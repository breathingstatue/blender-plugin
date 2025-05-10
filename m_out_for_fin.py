"""
Name:    m_out_for_fin
Purpose: Exports Re-Volt model mesh for instace file.

Description:
Exports Model for Instace.
"""

import os
import bpy
import bmesh
from mathutils import Color, Vector, Matrix
from . import common, rvstruct, img_in, layers
from .common import (
    dprint, get_all_lod, triangulate_ngons, queue_error, FACE_PROP_MASK,
    FACE_QUAD, texture_to_int, FACE_ENV, to_revolt_coord, to_revolt_axis,
    rvbbox_from_bm, center_from_rvbbox, radius_from_bmesh,
    MAX_MODEL_SLOTS
)
from .layers import *
from .rvstruct import Model

def export_file(filepath, scene):
    basename = os.path.basename(filepath).split('.')[0]
    obj = bpy.context.view_layer.objects.active
    print(f"Exporting M for {obj.name}...")

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
        # Dynamically get the object that owns this mesh
        for candidate in bpy.data.objects:
            if candidate.type == 'MESH' and candidate.data == me:
                obj = candidate
                break
        else:
            print(f"[WARNING] No object found for mesh: {me.name}")
            continue

        export_mesh(me, obj, scene, filepath, model, basename)

    animations = eval(scene.texture_animations)
    for animdict in animations:
        anim = rvstruct.TexAnimation()
        anim.from_dict(animdict)
        model.animations.append(anim)
    model.animation_count = scene.ta_max_slots

    with open(filepath, "wb") as file:
        model.write(file)

def get_texture_from_material(face, obj, prefix=None):
    """
    Attempts to get the image texture assigned to a face's material.
    """
    # Only allow fallback if the face has a valid material
    if obj.material_slots and face.material_index < len(obj.material_slots):
        mat = obj.material_slots[face.material_index].material
        if mat and mat.node_tree:
            for node in mat.node_tree.nodes:
                if node.type == 'TEX_IMAGE' and node.image:
                    if not prefix or prefix in node.image.name.lower():
                        return node.image
                    else:
                        print(f"[DEBUG] Ignored: {node.image.name} (wrong prefix '{prefix}')")
    # Do NOT fallback to other materials arbitrarily
    return None

def export_mesh(me, obj, scene, filepath, model, basename):
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
    type_layer = bm.faces.layers.int.get("Type")

    model.polygon_count += len(bm.faces)
    model.vertex_count += len(bm.verts)

    for i in range(MAX_MODEL_SLOTS):
        if scene.get(f"m_model_name_{i}", "").lower() == basename:
            mode = scene.get(f"m_texture_mode_{i}", "VERTEX_COLOR")
            path = scene.get(f"m_texture_path_{i}", "")
            if mode == "TEXTURE_NAME" and os.path.isfile(path):
                prefix = os.path.splitext(os.path.basename(path))[0].lower()
            elif mode == "LEVEL_TEXTURES" and os.path.isdir(path):
                prefix = os.path.basename(path).lower()

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
            poly.vertex_indices.append(face.verts[i].index if i < len(face.verts) else 0)

        for i in vert_order:
            if i < len(face.verts):
                color = face.loops[i][vc_layer]
                alpha = face.loops[i][va_layer]
                col = rvstruct.Color(
                    color=(int(color[0] * 255), int(color[1] * 255), int(color[2] * 255)),
                    alpha=255 - int(((alpha[0] + alpha[1] + alpha[2]) * 255) / 3)
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