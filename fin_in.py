"""
Name:    fin_in
Purpose: Imports Re-Volt instance files (.fin)

Description:
Imports Instance files.
"""

import os
import bpy
import bmesh
import mathutils
import importlib
from mathutils import Color

from . import common
from . import prm_in_for_fin
from . import rvstruct
from .common import (
    to_trans_matrix,
    to_blender_coord,
    FIN_SET_MODEL_RGB,
    FIN_ENV,
    FIN_HIDE,
    FIN_NO_MIRROR,
    FIN_NO_LIGHTS,
    FIN_NO_OBJECT_COLLISION,
    FIN_NO_CAMERA_COLLISION,
    MAX_MODEL_SLOTS,
    clean_model_base_name,
    dprint,
)
from .rvstruct import Instances, Vector

if "bpy" in locals():
    importlib.reload(common)
    importlib.reload(rvstruct)

# ---------------------------------------------------------------------------
# Main FIN import
# ---------------------------------------------------------------------------

def import_file(filepath, scene, texture_base_name=None):
    dprint(f"Opening FIN file: {filepath}")
    with open(filepath, 'rb') as file:
        filename = os.path.basename(filepath)
        level_name = os.path.splitext(filename)[0]
        texture_base_name = texture_base_name or level_name
        fin = Instances(file)
        dprint(f"Imported FIN file with {len(fin.instances)} instances.")

    mesh_cache = {}
    name_counter = {}

    for idx, instance in enumerate(fin.instances):
        dprint(f"Importing instance {idx + 1}/{len(fin.instances)}: {instance.name}")
        import_instance(filepath, scene, instance, texture_base_name, mesh_cache, name_counter)

    assign_texvc_materials(scene)
    dprint("FIN import complete.")

# ---------------------------------------------------------------------------
# Single instance import
# ---------------------------------------------------------------------------

def import_instance(filepath, scene, instance, texture_base_name, mesh_cache, name_counter):
    folder = os.path.dirname(filepath)
    raw_name = instance.name.rstrip("\x00").lower()

    matched_filename = None
    for f in os.listdir(folder):
        f_lower = f.lower()
        name_no_ext, ext = os.path.splitext(f_lower)
        if name_no_ext.startswith(raw_name) and ext == ".prm":
            matched_filename = f
            break

    if matched_filename:
        base_name = os.path.splitext(matched_filename)[0]

        if base_name in mesh_cache:
            mesh_data = mesh_cache[base_name]
        else:
            path = os.path.join(folder, matched_filename)
            temp_obj = prm_in_for_fin.import_file(path, scene, texture_base_name=texture_base_name)

            mesh_data = temp_obj.data
            mesh_cache[base_name] = mesh_data

            if temp_obj.name in bpy.context.scene.collection.objects:
                bpy.context.scene.collection.objects.unlink(temp_obj)
            bpy.data.objects.remove(temp_obj)
    else:
        common.queue_error("FIN import", f"No model found for '{raw_name}'")
        instance_obj = bpy.data.objects.new(raw_name, None)
        bpy.context.scene.collection.objects.link(instance_obj)
        instance_obj.empty_display_type = "SPHERE"
        return instance_obj

    base_obj_name = os.path.splitext(matched_filename)[0] if matched_filename else base_name
    name_count = name_counter.get(base_obj_name, 0)
    name_suffix = f".{str(name_count).zfill(3)}" if name_count > 0 else ""
    unique_name = base_obj_name + name_suffix
    name_counter[base_obj_name] = name_count + 1

    instance_obj = bpy.data.objects.new(unique_name, mesh_data)
    bpy.context.scene.collection.objects.link(instance_obj)

    instance_obj.matrix_world = to_trans_matrix(instance.or_matrix)
    instance_obj.location = to_blender_coord(instance.position)

    instance_obj.is_instance = True
    instance_obj["fin_texture_base"] = texture_base_name
    instance_obj.fin_col = [(128 + c) / 255 for c in instance.color]

    envcol = (*instance.env_color.color, 255 - instance.env_color.alpha)
    instance_obj.fin_envcol = [c / 255 for c in envcol]

    instance_obj.fin_priority = getattr(instance, "priority", 1)

    flags = getattr(instance, "flags", 0)
    instance_obj["fin_flags"] = int(flags)

    instance_obj.fin_env = bool(flags & FIN_ENV)
    instance_obj.fin_hide = bool(flags & FIN_HIDE)
    instance_obj.fin_no_mirror = bool(flags & FIN_NO_MIRROR)
    instance_obj.fin_no_lights = bool(flags & FIN_NO_LIGHTS)
    instance_obj.fin_model_rgb = bool(flags & FIN_SET_MODEL_RGB)
    instance_obj.fin_no_obj_coll = bool(flags & FIN_NO_OBJECT_COLLISION)
    instance_obj.fin_no_cam_coll = bool(flags & FIN_NO_CAMERA_COLLISION)

    apply_environment_settings(instance_obj)

    if instance_obj.mode == 'EDIT':
        bpy.ops.object.mode_set(mode='OBJECT')

    if instance_obj.data:
        model_color_material(instance_obj)

    dprint(f"Imported instance '{unique_name}'")
    return instance_obj

# ---------------------------------------------------------------------------
# Environment color handling
# ---------------------------------------------------------------------------

def apply_environment_settings(obj):
    env_col = getattr(obj, "fin_envcol", obj.get("fin_envcol", [1.0, 1.0, 1.0, 1.0]))

    if not should_apply_env_settings(obj) or not is_valid_color(env_col):
        return

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    env_layer = bm.loops.layers.color.get("Env") or bm.loops.layers.color.new("Env")
    env_alpha_layer = bm.faces.layers.float.get("EnvAlpha") or bm.faces.layers.float.new("EnvAlpha")

    full_color = (*env_col[:3], env_col[3])

    for face in bm.faces:
        for loop in face.loops:
            loop[env_layer] = full_color
        face[env_alpha_layer] = env_col[3]

    bm.to_mesh(obj.data)
    obj.data.update()
    bm.free()

    env_material_name = f"{obj.name.split('.')[0]}_Env"
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

    alpha_node = env_material.node_tree.nodes.get('Alpha')
    if not alpha_node:
        alpha_node = env_material.node_tree.nodes.new(type='ShaderNodeValue')
        alpha_node.name = 'Alpha'
        alpha_node.label = 'Alpha'

    if not bsdf.inputs['Alpha'].is_linked:
        links.new(alpha_node.outputs['Value'], bsdf.inputs['Alpha'])

    bsdf.inputs['Base Color'].default_value = (*env_col[:3], 1.0)
    alpha_node.outputs['Value'].default_value = env_col[3]

def is_valid_color(color):
    if not color or len(color) < 4:
        return False
    return all(0.0 <= c <= 1.0 for c in color[:3]) and 0.0 <= color[3] <= 1.0

def should_apply_env_settings(obj):
    fin_env = getattr(obj, "fin_env", obj.get("fin_env", False))
    apply_env = getattr(obj, "apply_env_settings", obj.get("apply_env_settings", True))
    return bool(fin_env) and bool(apply_env)

# ---------------------------------------------------------------------------
# RGB model color material
# ---------------------------------------------------------------------------

def model_color_material(obj):
    base_name, _ = get_base_name_for_layers(obj)
    material_name = f"{base_name}_RGBModelColor"

    mat = bpy.data.materials.get(material_name)
    if not mat:
        mat = bpy.data.materials.new(name=material_name)
        mat.use_nodes = True
        setup_material_nodes(mat)

    if mat.name not in obj.data.materials:
        obj.data.materials.append(mat)

    update_shader_color(obj, mat)
    return mat

def update_shader_color(obj, mat):
    nodes = mat.node_tree.nodes
    color = getattr(obj, "fin_col", obj.get("fin_col", [0.5, 0.5, 0.5]))

    bsdf = nodes.get('Principled BSDF')
    if bsdf:
        bsdf.inputs['Base Color'].default_value[:3] = color[:3]

def setup_material_nodes(mat):
    nodes = mat.node_tree.nodes
    nodes.clear()
    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    output = nodes.new('ShaderNodeOutputMaterial')
    links = mat.node_tree.links
    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    dprint(f"Material '{mat.name}' set up with principled shader.")

def get_base_name_for_layers(obj):
    name_parts = obj.name.split('.')
    base_name = name_parts[0]
    suffix = ""

    if len(name_parts) > 1 and name_parts[-1].isdigit():
        suffix = f".{name_parts[-1]}"

    extension = ".prm"
    return f"{base_name}{extension}", suffix

def assign_texvc_materials(scene):
    mesh_objects = [obj for obj in scene.objects if obj.type == 'MESH' and obj.data]
    if not mesh_objects:
        return

    bpy.ops.object.select_all(action='DESELECT')

    scene.material_choice = 'TEX_VC'

    for obj in mesh_objects:
        obj.select_set(True)

    bpy.context.view_layer.objects.active = mesh_objects[0]

    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    bpy.ops.object.assign_materials_auto()
