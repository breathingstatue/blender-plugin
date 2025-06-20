"""
Name:    m_out
Purpose: Exports Re-Volt model files (.m)

Description:
Exports Models.
"""

import os
import bpy
import bmesh
from mathutils import Color, Vector, Matrix
from . import common, rvstruct, img_in, layers
from .common import (
    dprint, get_all_lod, triangulate_ngons, queue_error, FACE_PROP_MASK,
    FACE_QUAD, texture_to_int, FACE_ENV, to_revolt_coord, to_revolt_axis,
    rvbbox_from_bm, center_from_rvbbox, radius_from_bmesh, MAX_MODEL_SLOTS
)
from .layers import *
from .rvstruct import Model

def export_file(filepath, scene):
    obj = bpy.context.view_layer.objects.active
    print(f"Exporting M for {obj.name}...")

    bpy.ops.object.mode_set(mode='OBJECT')

    mesh_objects = [o for o in scene.objects if o.type == 'MESH']

    set_material_to_col(mesh_objects)
    bpy.context.view_layer.update()
    set_material_to_texture(mesh_objects)

    meshes = []
    if "|q" in obj.data.name:
        dprint("LODs present.")
        meshes = get_all_lod(obj.data.name.split('|')[0])
        print([m.name for m in meshes])
    else:
        dprint("No LOD present.")
        meshes.append(obj.data)

    model = Model()

    for me in meshes:
        if not isinstance(me, bpy.types.Mesh):
            print(f"Skipping non-mesh object: {me}")
            continue

        print(f"Exporting mesh {meshes.index(me)} of {len(meshes)}")
        export_mesh(me, obj, scene, filepath, model)

    animations = eval(scene.texture_animations)
    for animdict in animations:
        anim = rvstruct.TexAnimation()
        anim.from_dict(animdict)
        model.animations.append(anim)
    model.animation_count = scene.ta_max_slots

    with open(filepath, "wb") as file:
        model.write(file)

def get_texture_from_material(face, obj):
    if not obj.material_slots:
        print(f"[DEBUG] Object '{obj.name}' has no material slots.")
        return None

    if face.material_index >= len(obj.material_slots):
        print(f"[DEBUG] Face {face.index} references invalid material index {face.material_index}.")
        return None

    mat = obj.material_slots[face.material_index].material
    if not mat:
        print(f"[DEBUG] No material assigned to slot {face.material_index}.")
        return None

    print(f"[DEBUG] Face {face.index} uses material '{mat.name}'.")

    # First: Try node-based method
    if mat.use_nodes:
        for node in mat.node_tree.nodes:
            print(f"[DEBUG] Checking node '{node.name}' of type '{node.type}'...")
            if node.type == 'TEX_IMAGE':
                if node.image:
                    print(f"[DEBUG] Found TEX_IMAGE node with image '{node.image.name}' (filepath: '{node.image.filepath}')")
                    return node.image
                else:
                    print(f"[DEBUG] TEX_IMAGE node has no image assigned.")

    print(f"[DEBUG] No TEX_IMAGE node with image found in material '{mat.name}'")
    return None

def export_mesh(me, obj, scene, filepath, model):
    bm = bmesh.new()
    bm.from_mesh(me)

    if scene.apply_scale:
        bmesh.ops.scale(bm, vec=obj.scale, verts=bm.verts)
    if scene.apply_rotation:
        bmesh.ops.rotate(bm, cent=obj.location, matrix=obj.rotation_euler.to_matrix(), space=obj.matrix_basis, verts=bm.verts)

    if scene.triangulate_ngons:
        num_ngons = triangulate_ngons(bm)
        if num_ngons > 0:
            print(f"Triangulated {num_ngons} n-gons")

    uv_layer = bm.loops.layers.uv.get("UVMap") or bm.loops.layers.uv.new("UVMap")
    vc_layer = bm.loops.layers.color.get("Col") or bm.loops.layers.color.new("Col")
    env_layer = bm.loops.layers.color.get("Env") or bm.loops.layers.color.new("Env")
    env_alpha_layer = bm.faces.layers.float.get("EnvAlpha") or bm.faces.layers.float.new("EnvAlpha")
    va_layer = bm.loops.layers.color.get("Alpha") or bm.loops.layers.color.new("Alpha")
    texnum_layer = bm.faces.layers.int.get("Texture Number") or bm.faces.layers.int.new("Texture Number")
    type_layer = bm.faces.layers.int.get("Type") or bm.faces.layers.int.new("Type")

    model.polygon_count += len(bm.faces)
    model.vertex_count += len(bm.verts)

    # Determine texture prefix based on model-specific settings
    model_name = obj.name.lower().split('.')[0]

    for i in range(MAX_MODEL_SLOTS):
        if scene.get(f"m_model_name_{i}", "").lower() == model_name:
            mode = scene.get(f"m_texture_mode_{i}", "VERTEX_COLOR")
            path = scene.get(f"m_texture_path_{i}", "")
            if mode == "TEXTURE_NAME" and os.path.isfile(path):
                prefix = os.path.splitext(os.path.basename(path))[0].lower()
            elif mode == "LEVEL_TEXTURES" and os.path.isdir(path):
                prefix = os.path.basename(path).lower()  # Optional: just use folder name

    for face in bm.faces:
        poly = rvstruct.Polygon()
        is_quad = len(face.verts) == 4
        poly.type = face[type_layer] & FACE_PROP_MASK
        if is_quad:
            poly.type |= FACE_QUAD

        if scene.use_tex_num and texnum_layer:
            poly.texture = face[texnum_layer]
            print(f"[OK] Face {face.index}: Using Texture Number layer → {poly.texture}")
        else:
            image = get_texture_from_material(face, obj)
            if image:
                image_name = image.name
                image_base = os.path.splitext(image_name)[0].lower()

                if image_base == "fxpage1" or image_base == prefix:
                    poly.texture = 0
                    print(f"[INFO] Face {face.index}: '{image_base}' matched base '{prefix}' → index 0")
                else:
                    poly.texture = texture_to_int(image_name, prefix=prefix)
                    print(f"[INFO] Face {face.index}: '{image_name}' with prefix '{prefix}' → index {poly.texture}")
            else:
                poly.texture = -1  # Ensure it's marked untextured
                print(f"[INFO] Face {face.index}: No texture assigned → index -1")

        vert_order = [2, 1, 0, 3] if not is_quad else [3, 2, 1, 0]

        for i in vert_order:
            idx = face.verts[i].index if i < len(face.verts) else 0
            poly.vertex_indices.append(idx)

        for i in vert_order:
            if i < len(face.verts):
                color = face.loops[i][vc_layer]
                alpha = face.loops[i][va_layer]
                col = rvstruct.Color(
                    color=(int(color[0]*255), int(color[1]*255), int(color[2]*255)),
                    alpha=255 - int(((alpha[0]+alpha[1]+alpha[2])*255)/3)
                )
            else:
                col = rvstruct.Color(color=(255, 255, 255), alpha=255)
            poly.colors.append(col)

        # Assign UVs (only if the face has a valid texture)
        if poly.texture != -1:
            for i in vert_order:
                if i < len(face.verts) and uv_layer:
                    uv = face.loops[i][uv_layer].uv
                    poly.uv.append(rvstruct.UV(uv=(uv[0], 1.0 - uv[1])))
                else:
                    poly.uv.append(rvstruct.UV(uv=(0.0, 0.0)))
        else:
            # Untextured face: zero out UVs to avoid invalid export values
            poly.uv = [rvstruct.UV(uv=(0.0, 0.0)) for _ in range(len(vert_order))]

        model.polygons.append(poly)

    for vertex in bm.verts:
        coord = to_revolt_coord(vertex.co)
        normal = to_revolt_axis(vertex.normal)
        rvvert = rvstruct.Vertex()
        rvvert.position = rvstruct.Vector(data=coord)
        rvvert.normal = rvstruct.Vector(data=normal)
        model.vertices.append(rvvert)

    bm.free()

def set_material_to_col(mesh_objects):
    if not mesh_objects:
        print("No mesh objects selected for material assignment.")
        return

    for obj in mesh_objects:
        obj.data.material_choice = 'COL'
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.object.assign_materials_impexp()
        bpy.ops.object.mode_set(mode='OBJECT')

def set_material_to_texture(mesh_objects):
    if not mesh_objects:
        print("No mesh objects selected for material assignment.")
        return

    for obj in mesh_objects:
        obj.data.material_choice = 'UV_TEX'
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.object.assign_materials_impexp()
        bpy.ops.object.mode_set(mode='OBJECT')