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
)
from .rvstruct import Instances, Vector

if "bpy" in locals():
    importlib.reload(common)
    importlib.reload(rvstruct)

# ---------------------------------------------------------------------------
# Main FIN import
# ---------------------------------------------------------------------------

def import_file(filepath, scene, texture_base_name=None):
    print(f"Opening file: {filepath}")
    with open(filepath, 'rb') as file:
        filename = os.path.basename(filepath)
        level_name = os.path.splitext(filename)[0]
        texture_base_name = texture_base_name or level_name
        fin = Instances(file)
        print(f"Imported FIN file with {len(fin.instances)} instances.")

    mesh_cache = {}
    name_counter = {}

    for idx, instance in enumerate(fin.instances):
        print(f"Importing instance {idx + 1}/{len(fin.instances)}: {instance.name}")
        import_instance(filepath, scene, instance, texture_base_name, mesh_cache, name_counter)

    print("Assigning UV texture materials...")
    assign_uvtex_materials(scene)
    print("Import complete.")

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

            # Remove temporary source object (keep only mesh data)
            if temp_obj.name in bpy.context.scene.collection.objects:
                bpy.context.scene.collection.objects.unlink(temp_obj)
            bpy.data.objects.remove(temp_obj)
    else:
        print(f"[WARN] No model found for '{raw_name}'")
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

    # ----------------------------------------------------------------------
    # Transform & position
    # ----------------------------------------------------------------------

    instance_obj.matrix_world = to_trans_matrix(instance.or_matrix)
    instance_obj.location = to_blender_coord(instance.position)

    # ----------------------------------------------------------------------
    # FIN-related data
    # ----------------------------------------------------------------------

    # RNA bool (registered in __init__.py)
    instance_obj.is_instance = True

    # Base name for textures: ID property
    instance_obj["fin_texture_base"] = texture_base_name

    # Model color: Re-Volt stores -128..127 → (128 + c) / 255
    instance_obj.fin_col = [(128 + c) / 255 for c in instance.color]

    # Env color (RGB + alpha inverted)
    envcol = (*instance.env_color.color, 255 - instance.env_color.alpha)
    instance_obj.fin_envcol = [c / 255 for c in envcol]

    # Priority
    instance_obj.fin_priority = getattr(instance, "priority", 1)

    # Flags
    flags = getattr(instance, "flags", 0)
    instance_obj["fin_flags"] = int(flags)

    # Decode flags into RNA properties
    instance_obj.fin_env = bool(flags & FIN_ENV)
    instance_obj.fin_hide = bool(flags & FIN_HIDE)
    instance_obj.fin_no_mirror = bool(flags & FIN_NO_MIRROR)
    instance_obj.fin_no_lights = bool(flags & FIN_NO_LIGHTS)
    instance_obj.fin_model_rgb = bool(flags & FIN_SET_MODEL_RGB)
    instance_obj.fin_no_obj_coll = bool(flags & FIN_NO_OBJECT_COLLISION)
    instance_obj.fin_no_cam_coll = bool(flags & FIN_NO_CAMERA_COLLISION)

    # Apply environment settings if applicable
    apply_environment_settings(instance_obj)

    # Ensure object mode for later ops
    if instance_obj.mode == 'EDIT':
        bpy.ops.object.mode_set(mode='OBJECT')

    # If mesh exists, set model color material & COL materials
    if instance_obj.data:
        model_color_material(instance_obj)
        print("Assigning vertex color materials...")
        assign_col_materials(scene)

    print(f"Finished importing {unique_name}")
    return instance_obj

# ---------------------------------------------------------------------------
# Environment color handling
# ---------------------------------------------------------------------------

def apply_environment_settings(obj):
    """Applies environmental settings if applicable based on object properties."""
    # fin_envcol is an RNA FloatVectorProperty with getter/setter,
    # but keep obj.get fallback for backwards safety.
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

    # Retrieve or create Env material
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

    # Ensure Alpha node
    alpha_node = env_material.node_tree.nodes.get('Alpha')
    if not alpha_node:
        alpha_node = env_material.node_tree.nodes.new(type='ShaderNodeValue')
        alpha_node.name = 'Alpha'
        alpha_node.label = 'Alpha'

    # Connect Alpha to BSDF
    if not bsdf.inputs['Alpha'].is_linked:
        links.new(alpha_node.outputs['Value'], bsdf.inputs['Alpha'])

    # Update shader color and alpha
    bsdf.inputs['Base Color'].default_value = (*env_col[:3], 1.0)
    alpha_node.outputs['Value'].default_value = env_col[3]

def is_valid_color(color):
    """Check if the color values are within the valid range and meet specific criteria."""
    if not color or len(color) < 4:
        return False
    return all(0.0 <= c <= 1.0 for c in color[:3]) and 0.0 <= color[3] <= 1.0

def should_apply_env_settings(obj):
    # RNA props with fallback to ID-props
    fin_env = getattr(obj, "fin_env", obj.get("fin_env", False))
    apply_env = getattr(obj, "apply_env_settings", obj.get("apply_env_settings", True))
    return bool(fin_env) and bool(apply_env)

# ---------------------------------------------------------------------------
# RGB model color material
# ---------------------------------------------------------------------------

def model_color_material(obj):
    """Creates an RGB model color material and assigns it to the object or retrieves it if already created."""
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
    """Update the shader color based on the object's 'fin_col' property."""
    nodes = mat.node_tree.nodes
    color = getattr(obj, "fin_col", obj.get("fin_col", [0.5, 0.5, 0.5]))

    bsdf = nodes.get('Principled BSDF')
    if bsdf:
        bsdf.inputs['Base Color'].default_value[:3] = color[:3]

def setup_material_nodes(mat):
    """Sets up the shader nodes for the RGB modeling material."""
    nodes = mat.node_tree.nodes
    nodes.clear()
    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    output = nodes.new('ShaderNodeOutputMaterial')
    links = mat.node_tree.links
    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    print(f"Material '{mat.name}' set up with principled shader.")

def get_base_name_for_layers(obj):
    name_parts = obj.name.split('.')
    base_name = name_parts[0]
    suffix = ""

    if len(name_parts) > 1 and name_parts[-1].isdigit():
        suffix = f".{name_parts[-1]}"

    extension = ".prm"
    return f"{base_name}{extension}", suffix

# ---------------------------------------------------------------------------
# COL material assignment
# ---------------------------------------------------------------------------

def assign_col_materials(scene):
    mesh_objects = [obj for obj in scene.objects if obj.type == 'MESH' and obj.data]
    if not mesh_objects:
        return

    targets = [obj for obj in mesh_objects if "material_assigned_col" not in obj]
    if not targets:
        return

    bpy.ops.object.select_all(action='DESELECT')

    scene.material_choice = 'COL'

    for obj in targets:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = targets[0]

    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    bpy.ops.object.assign_materials_impexp()

    for obj in targets:
        obj["material_assigned_col"] = True

# ---------------------------------------------------------------------------
# UV texture material assignment
# ---------------------------------------------------------------------------

def assign_uvtex_materials(scene):
    """Assign .bmp-based UV materials to all mesh objects after import, in OBJECT mode."""

    def _clean_base(s: str) -> str:
        return ''.join(ch for ch in os.path.splitext(s)[0].lower() if ch.isalnum() or ch in ('_', '-'))

    def _int_to_texture_suffix(tex_num: int) -> str:
        # a, b, ..., z, aa, ab, ...
        suffix1 = chr(tex_num % 26 + 97)
        suffix2_num = tex_num // 26 - 1
        suffix2 = chr(suffix2_num % 26 + 97) if suffix2_num >= 0 else ''
        return suffix2 + suffix1

    def _collect_bmp_materials():
        out = {}
        for mat in bpy.data.materials:
            if not mat.use_nodes:
                continue
            for node in mat.node_tree.nodes:
                if node.type == 'TEX_IMAGE' and node.image and node.image.name.lower().endswith('.bmp'):
                    out[node.image.name] = mat
        return out

    def _is_instance(obj):
        return getattr(obj, "is_instance", obj.get("is_instance", False))

    def _get_fin_base(obj):
        if _is_instance(obj):
            val = getattr(obj, "fin_texture_base", obj.get("fin_texture_base", ""))
            if val:
                return str(val).strip().lower()
        return ""

    mesh_objects = [obj for obj in scene.objects if obj.type == 'MESH' and obj.data]
    if not mesh_objects:
        return

    bmp_materials = _collect_bmp_materials()

    scene_level_base = ""
    if "level_texture_base" in scene and scene["level_texture_base"]:
        scene_level_base = os.path.splitext(scene["level_texture_base"].strip().lower())[0]

    for obj in mesh_objects:
        if obj.get("material_assigned_uv"):
            continue

        me = obj.data
        bm = bmesh.new()
        bm.from_mesh(me)

        texnum_layer = bm.faces.layers.int.get("Texture Number")
        if not texnum_layer:
            bm.free()
            continue

        fin_base = _get_fin_base(obj)
        if _is_instance(obj) and fin_base:
            base = fin_base
        elif scene_level_base:
            base = scene_level_base
        else:
            base = _clean_base(obj.name)

        for face in bm.faces:
            tex_num = face[texnum_layer]
            if tex_num is None or tex_num < 0:
                continue

            suffix = _int_to_texture_suffix(tex_num)
            img_key = f"{base}{suffix}.bmp"

            mat = bmp_materials.get(img_key)
            if not mat:
                mat = bpy.data.materials.get(img_key) or bpy.data.materials.get(img_key[:-4])

            if not mat:
                continue

            if mat.name not in me.materials:
                me.materials.append(mat)

            face.material_index = me.materials.find(mat.name)

        bm.to_mesh(me)
        me.update()
        bm.free()

        obj["material_assigned_uv"] = True
