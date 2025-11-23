"""
Name:    m_in_for_fin
Purpose: Imports Re-Volt model files (.m) for Instances (.fin)

Description:
Imports Models for Instance files.
"""

import os
import bpy
import bmesh
import importlib
from mathutils import Vector
from . import common
from . import layers
from .layers import set_face_env
from . import rvstruct
from . import img_in
from . import w_in
from .rvstruct import Model
from .common import to_blender_coord, to_blender_axis, FACE_QUAD, reverse_quad, FACE_ENV, dprint, int_to_texture
from .common import MAX_MODEL_SLOTS, get_model_texture_path

# Reload imports if 'bpy' is already in locals
if "bpy" in locals():
    importlib.reload(common)
    importlib.reload(rvstruct)
    importlib.reload(img_in)

def import_file(filepath, scene, model_name=None, texture_base_name=None):
    meshes = []
    obj = None

    with open(filepath, 'rb') as file:
        filename = os.path.basename(filepath)
        base_name = os.path.splitext(os.path.basename(filepath))[0].lower()
        if not model_name:
            model_name = base_name
        file.seek(0, os.SEEK_END)
        file_end = file.tell()
        file.seek(0, os.SEEK_SET)

        while file.tell() < file_end:
            meshes.append(Model(file))

    dprint(f"Imported {filename} ({len(meshes)} meshes)")

    if not meshes:
        print("No meshes found in the file.")
        return None

    for index, model in enumerate(meshes):
        me = import_m_mesh(model, filename, filepath, scene, model_name)
        
        if len(meshes) > 1:
            # Fake user if there are multiple LoDs so they're kept when saving
            me.use_fake_user = True

            # Append a quality suffix to meshes
            bname, number = me.name.rsplit(".", 1)
            me.name = "{}|q{}".format(bname, meshes.index(model))
            
        if index == 0:
            dprint(f"Creating Blender object for {filename}...")
            obj = bpy.data.objects.new(filename, me)

            # Fix: ensure object is linked to a visible collection
            if obj.name not in bpy.context.view_layer.objects:
                bpy.context.collection.objects.link(obj)

            obj["is_model"] = True

            bpy.context.view_layer.objects.active = obj
            assign_uv_tex_material(obj, base_name=texture_base_name, model_name=model_name)

    if obj:  # Only proceed if an object was successfully created
        texture_animations = [animation.as_dict() for animation in model.animations]
        scene.texture_animations = str(texture_animations)
        scene.ta_max_slots = model.animation_count
    
    return obj

def import_m_mesh(model, filename, filepath, scene, model_name, envlist=None):
    me = bpy.data.meshes.new(name=filename)
    bm = bmesh.new()
    add_rvmesh_to_bmesh(model, bm, me, filepath, scene, model_name, envlist)
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    materials = create_materials_for_attributes(me, bm, filename)

    return me

def add_rvmesh_to_bmesh(model, bm, me, filepath, scene, model_name, envlist=None):
    uv_layer = bm.loops.layers.uv.new("UVMap")
    vc_layer = bm.loops.layers.color.new("Col")
    env_layer = bm.loops.layers.color.new("Env")
    env_alpha_layer = bm.faces.layers.float.new("EnvAlpha")
    va_layer = bm.loops.layers.color.new("Alpha")
    texnum_layer = bm.faces.layers.int.new("Texture Number")
    type_layer = bm.faces.layers.int.new("Type")
    created_faces = []

    for vert in model.vertices:
        position = to_blender_coord(vert.position.data)
        bm.verts.new(Vector((position[0], position[1], position[2])))

    bm.verts.ensure_lookup_table()

    for poly in model.polygons:
        is_quad = poly.type & FACE_QUAD
        num_loops = 4 if is_quad else 3
        indices = [poly.vertex_indices[i] for i in reversed(range(num_loops))]
        verts = [bm.verts[idx] for idx in indices]
        uvs = reverse_quad(poly.uv, tri=not is_quad)
        colors = reverse_quad(poly.colors, tri=not is_quad)

        try:
            face = bm.faces.new(verts)
            created_faces.append(face)
        except ValueError as e:
            continue

        if poly.texture >= 0:
            texture_path = get_model_texture_path(filepath, poly.texture, scene, model_name)
            if texture_path and os.path.isfile(texture_path):
                material_name = os.path.basename(texture_path)
                material = bpy.data.materials.get(material_name)
                if not material:
                    image = bpy.data.images.load(texture_path, check_existing=True)
                    material = bpy.data.materials.new(name=material_name)
                    material.use_nodes = True
                    bsdf = material.node_tree.nodes.get('Principled BSDF')
                    tex_image = material.node_tree.nodes.new('ShaderNodeTexImage')
                    tex_image.image = image
                    material.node_tree.links.new(bsdf.inputs['Base Color'], tex_image.outputs['Color'])
                if material_name not in me.materials:
                    me.materials.append(material)
                face.material_index = me.materials.find(material_name)

        face[type_layer] = poly.type
        face[texnum_layer] = poly.texture
        
        for l in range(num_loops):
            alpha = 1-(float(colors[l].alpha) / 255)
            color = [float(c) / 255 for c in colors[l].color]

            face.loops[l][uv_layer].uv = (uvs[l].u, 1 - uvs[l].v)

            face.loops[l][vc_layer][0] = color[0]
            face.loops[l][vc_layer][1] = color[1]
            face.loops[l][vc_layer][2] = color[2]

            face.loops[l][va_layer][0] = alpha
            face.loops[l][va_layer][1] = alpha
            face.loops[l][va_layer][2] = alpha

        face.smooth = True

def create_materials_for_attributes(me, bm, obj_name):
    materials = {}
    for attr_name in ['Col', 'Alpha', 'Env']:
        mat_name = f"{obj_name}_{attr_name}"
        material = bpy.data.materials.get(mat_name)
        if not material:
            material = bpy.data.materials.new(name=mat_name)
            material.use_nodes = True
            nodes = material.node_tree.nodes
            links = material.node_tree.links

            material_output = nodes.get('Material Output') or nodes.new(type='ShaderNodeOutputMaterial')
            attr_node = nodes.new(type='ShaderNodeAttribute')
            attr_node.attribute_name = attr_name
            attr_node.attribute_type = 'GEOMETRY'

            if attr_name == 'Col':
                principled_bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
                links.new(attr_node.outputs['Color'], principled_bsdf.inputs['Base Color'])
                links.new(principled_bsdf.outputs['BSDF'], material_output.inputs['Surface'])

            elif attr_name == 'Alpha':
                principled_bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
                links.new(attr_node.outputs['Color'], principled_bsdf.inputs['Base Color'])
                links.new(principled_bsdf.outputs['BSDF'], material_output.inputs['Surface'])

            elif attr_name == 'Env':
                principled_bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
                links.new(attr_node.outputs['Color'], principled_bsdf.inputs['Base Color'])
                links.new(principled_bsdf.outputs['BSDF'], material_output.inputs['Surface'])

        materials[attr_name] = material

    return materials
                    
def assign_uv_tex_material(obj, base_name=None, model_name=None):
    bm = bmesh.new()
    bm.from_mesh(obj.data)

    scene = bpy.context.scene
    uv_layer = bm.loops.layers.uv.verify()
    texnum_layer = bm.faces.layers.int.get("Texture Number") or bm.faces.layers.int.new("Texture Number")
    bmp_materials = get_bmp_materials()

    # Determine source_mode and base texture name per model
    source_mode = 'VERTEX_COLOR'
    base_name_for_texture = ""
    texture_path = ""

    if model_name:
        for i in range(MAX_MODEL_SLOTS):
            if common.get_scene_value(scene, f"m_model_name_{i}", "") == model_name:
                source_mode = common.get_scene_value(scene, f"m_texture_mode_{i}", "VERTEX_COLOR")
                texture_path = common.get_scene_value(scene, f"m_texture_path_{i}", "")
                if source_mode == "TEXTURE_NAME":
                    base_name_for_texture = os.path.splitext(os.path.basename(texture_path))[0].lower()
                elif source_mode == "LEVEL_TEXTURES":
                    base_name_for_texture = os.path.basename(texture_path.rstrip("/\\")).lower()

    for face in bm.faces:
        # Determine material_key depending on mode
        material_key = None

        if source_mode == 'TEXTURE_NAME':
            material_key = f"{base_name_for_texture}.bmp"

        elif source_mode == 'LEVEL_TEXTURES':
            if not texnum_layer or face[texnum_layer] < 0:
                print(f"[DEBUG] Skipping face — LEVEL_TEXTURES mode but tex_num is invalid: {face[texnum_layer]}")
                continue
            tex_num = face[texnum_layer]
            material_key = int_to_texture(tex_num, name=base_name_for_texture)

        else:
            # VERTEX_COLOR — skip assigning material entirely
            continue

        if material_key is None:
            continue

        print(f"[DEBUG] Trying to assign material: {material_key}")

        if material_key in bmp_materials:
            material = bmp_materials[material_key]
            if material.name not in obj.data.materials:
                obj.data.materials.append(material)
            face.material_index = obj.data.materials.find(material.name)
        else:
            print(f"[WARN] Material not found for key: {material_key}")

    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
                
def get_bmp_materials():
    bmp_materials = {}
    for mat in bpy.data.materials:
        if mat.use_nodes:
            for node in mat.node_tree.nodes:
                if node.type == 'TEX_IMAGE' and node.image and node.image.filepath.lower().endswith('.bmp'):
                    bmp_materials[node.image.name] = mat
    return bmp_materials

def apply_env_data(mesh_data, world, polygons, envlist, obj_name):
    """
    Apply environment settings to a mesh in Blender by setting vertex colors and adjusting the Principled BSDF node's base color and alpha.
    """
    global w_in

    bm = bmesh.new()
    bm.from_mesh(mesh_data)

    # Ensure environment layers are added or retrieved correctly
    env_layer = bm.loops.layers.color.get("Env") or bm.loops.layers.color.new("Env")
    env_alpha_layer = bm.faces.layers.float.get("EnvAlpha") or bm.faces.layers.float.new("EnvAlpha")

    # Retrieve or create the material with environmental settings
    env_material_name = f"{obj_name}_Env"
    env_material = bpy.data.materials.get(env_material_name)
    if not env_material:
        env_material = bpy.data.materials.new(name=env_material_name)
        env_material.use_nodes = True
        nodes = env_material.node_tree.nodes
        links = env_material.node_tree.links
        bsdf = nodes.new('ShaderNodeBsdfPrincipled')
        mat_output = nodes.new('ShaderNodeOutputMaterial')
        links.new(bsdf.outputs['BSDF'], mat_output.inputs['Surface'])
    else:
        nodes = env_material.node_tree.nodes
        links = env_material.node_tree.links
        bsdf = env_material.node_tree.nodes.get('Principled BSDF')
        if not bsdf:
            bsdf = env_material.node_tree.nodes.new('ShaderNodeBsdfPrincipled')

    # Validate the number of faces and polygons
    if len(bm.faces) == len(polygons):
        for face_index, (face, poly) in enumerate(zip(bm.faces, polygons)):
            if poly.type & FACE_ENV:
                env_index = w_in.envidx % len(envlist)
                env_col = envlist[env_index]
                scaled_color = tuple(c / 255.0 for c in env_col.color)
                scaled_alpha = env_col.alpha / 255.0

                full_color = (*scaled_color, scaled_alpha)  # Ensure we have RGBA values

                for loop in face.loops:
                    loop[env_layer] = full_color  # Assign RGBA to the Env layer
                face[env_alpha_layer] = scaled_alpha

                if bsdf:
                    bsdf.inputs['Base Color'].default_value = (*scaled_color, 1)
                    bsdf.inputs['Alpha'].default_value = scaled_alpha

                face.smooth = True
                w_in.envidx += 1  # Increment the global index after processing each face

    bm.to_mesh(mesh_data)
    mesh_data.update()
    bm.free()