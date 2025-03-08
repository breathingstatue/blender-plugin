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
from . import common
from . import prm_in_for_fin
from . import rvstruct
from .common import to_trans_matrix, to_blender_coord, FIN_SET_MODEL_RGB, FIN_ENV, FIN_HIDE, FIN_NO_MIRROR, FIN_NO_LIGHTS
from .common import FIN_NO_OBJECT_COLLISION, FIN_NO_CAMERA_COLLISION
from .rvstruct import Instances, Vector
from mathutils import Color

# Check if 'bpy' is already in locals to determine if this is a reload scenario
if "bpy" in locals():
    importlib.reload(common)
    importlib.reload(rvstruct)

def import_file(filepath, scene):
    print(f"Opening file: {filepath}")  # Debug point 1
    with open(filepath, 'rb') as file:
        filename = os.path.basename(filepath)
        fin = Instances(file)
        print(f"Imported FIN file with {len(fin.instances)} instances.")  # Debug point 2

    for idx, instance in enumerate(fin.instances):
        print(f"Importing instance {idx+1}/{len(fin.instances)}: {instance.name}")  # Debug point 3
        import_instance(filepath, scene, instance)

    print("Running material assignment...")  # Debug point 4
    assign_material_to_all(scene)
    print("Import complete.")  # Debug point 5

def import_instance(filepath, scene, instance):
    print(f"Importing instance: {instance.name}")  # Debug point 1
    folder = os.sep.join(filepath.split(os.sep)[:-1])
    instance_name = clean_instance_name(instance.name)

    expected_prm_fname = instance_name if instance_name.endswith(".prm") else f"{instance_name}.prm"
    print(f"Expected PRM file: {expected_prm_fname}")  # Debug point 2

    prm_fname = None
    for f in os.listdir(folder):
        if f == expected_prm_fname:
            prm_fname = f
            break

    if not prm_fname:
        for f in os.listdir(folder):
            if f.startswith(instance_name) and f.endswith(".prm"):
                prm_fname = f
                break

    print(f"Matching PRM found: {prm_fname}")  # Debug point 3

    if prm_fname in [ob.name for ob in scene.objects]:
        print(f"PRM {prm_fname} already in scene. Duplicating...")  # Debug point 4
        data = scene.objects[prm_fname].data
        instance_obj = bpy.data.objects.new(name=prm_fname, object_data=data)
        # Check if the object is already in the scene collection
        if instance_obj.name not in bpy.context.scene.collection.objects:
            bpy.context.scene.collection.objects.link(instance_obj)
        else:
            print(f"Object '{instance_obj.name}' is already in the scene collection.")
    elif prm_fname:
        prm_path = os.path.join(folder, prm_fname)
        print(f"Importing PRM from path: {prm_path}")  # Debug point 5
        instance_obj = prm_in_for_fin.import_file(prm_path, scene)
    else:
        print(f"No PRM found for {instance_name}. Creating empty object.")  # Debug point 6
        instance_obj = bpy.data.objects.new(instance_name, None)
        # Check if the object is already in the scene collection
        if instance_obj.name not in bpy.context.scene.collection.objects:
            bpy.context.scene.collection.objects.link(instance_obj)
        else:
            print(f"Object '{instance_obj.name}' is already in the scene collection.")
        instance_obj.empty_display_type = "SPHERE"

    print(f"Applying transformations to {instance_name}")  # Debug point 7
    instance_obj.matrix_world = to_trans_matrix(instance.or_matrix)
    instance_obj.location = to_blender_coord(instance.position)

    instance_obj["is_instance"] = True
    instance_obj["fin_col"] = [(128 + c) / 255 for c in instance.color]
    envcol = (*instance.env_color.color, 255 - instance.env_color.alpha)
    instance_obj["fin_envcol"] = [c / 255 for c in envcol]
    instance_obj["fin_priority"] = instance.priority

    apply_environment_settings(instance_obj)
    model_color_material(instance_obj)

    # Ensure the object is in object mode before proceeding
    if instance_obj.mode == 'EDIT':
        bpy.ops.object.mode_set(mode='OBJECT')

    print(f"Finished importing {instance_name}")  # Debug point 8
    return instance_obj

def apply_environment_settings(obj):
    """Applies environmental settings if applicable based on object properties."""
    env_col = obj.get("fin_envcol", [1.0, 1.0, 1.0, 1.0])

    if not should_apply_env_settings(obj) or not is_valid_color(env_col):
        return

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    env_layer = bm.loops.layers.color.get("Env") or bm.loops.layers.color.new("Env")
    env_alpha_layer = bm.faces.layers.float.get("EnvAlpha") or bm.faces.layers.float.new("EnvAlpha")

    full_color = (*env_col[:3], env_col[3])

    for face in bm.faces:
        for loop in face.loops:
            loop[env_layer] = full_color  # Assign RGBA to the Env layer
        face[env_alpha_layer] = env_col[3]

    bm.to_mesh(obj.data)
    obj.data.update()
    bm.free()

    # Retrieve or create the material with environmental settings
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

    # Ensure there is a separate alpha node if not already present
    alpha_node = env_material.node_tree.nodes.get('Alpha')
    if not alpha_node:
        alpha_node = env_material.node_tree.nodes.new(type='ShaderNodeValue')
        alpha_node.name = 'Alpha'
        alpha_node.label = 'Alpha'

    # Link the alpha node to the BSDF shader
    if not bsdf.inputs['Alpha'].is_linked:
        links.new(alpha_node.outputs['Value'], bsdf.inputs['Alpha'])

    # Update the BSDF shader's base color and alpha
    bsdf.inputs['Base Color'].default_value = (*env_col[:3], 1)
    alpha_node.outputs['Value'].default_value = env_col[3]

def is_valid_color(color):
    """Check if the color values are within the valid range and meet specific criteria."""
    if not color:
        return False
    # Ensure colors are within the range 0 to 1
    return all(0 <= c <= 1 for c in color[:3]) and 0 <= color[3] <= 1

def should_apply_env_settings(obj):
    """Determines if environmental settings should be applied to a given object."""
    return obj.get("fin_env", False) and obj.get("apply_env_settings", True)

def model_color_material(obj):
    """Creates a model color material and assigns it to the object or retrieves it if already created."""
    base_name, _ = get_base_name_for_layers(obj)
    material_name = f"{base_name}_RGBModelColor"

    mat = bpy.data.materials.get(material_name)
    if not mat:
        mat = bpy.data.materials.new(name=material_name)
        mat.use_nodes = True
        setup_material_nodes(mat)

    if mat.name not in obj.data.materials:
        obj.data.materials.append(mat)

    # Ensure the color is applied directly to the shader
    update_shader_color(obj, mat)

    return mat

def update_shader_color(obj, mat):
    """Update the shader color based on the object's 'fin_col' property."""
    nodes = mat.node_tree.nodes
    color = obj.get("fin_col", [0.5, 0.5, 0.5])

    bsdf = nodes.get('Principled BSDF')
    if bsdf:
        bsdf.inputs['Base Color'].default_value[:3] = color[:3]

def setup_material_nodes(mat):
    """Sets up the shader nodes for the RGB model material."""
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

    # Check if the last part of the name is a number (suffix like .001, .002)
    if len(name_parts) > 1 and name_parts[-1].isdigit():
        suffix = f".{name_parts[-1]}"

    extension = ".prm"

    return f"{base_name}{extension}", suffix

def clean_instance_name(name):
    """
    Cleans the instance name by removing unnecessary suffixes after a dot,
    while preserving the .prm extension.
    """
    # Lowercase the name to ensure consistency
    name = name.lower()

    # If the name ends with '.prm', strip it temporarily to clean up the base name
    if name.endswith(".prm"):
        base_name = name[:-4]  # Strip off the '.prm' part
    else:
        base_name = name

    # Find the first dot in the base name and strip anything after it
    if '.' in base_name:
        base_name = base_name.split('.')[0]

    # Reattach the .prm extension if it was originally there
    return f"{base_name}.prm" if name.endswith(".prm") else base_name

def assign_material_to_all(scene):
    mesh_objects = [obj for obj in scene.objects if obj.type == 'MESH' and obj.data]
    if not mesh_objects:
        print("No valid mesh objects for material assignment.")
        return

    # Deselect all objects first
    bpy.ops.object.select_all(action='DESELECT')

    # Select all mesh objects at once for faster batch processing
    for obj in mesh_objects:
        if "material_assigned" not in obj:
            obj.select_set(True)
            obj.data.material_choice = 'COL'  # Set vertex color first

    # Ensure all objects are in object mode before proceeding
    bpy.ops.object.mode_set(mode='OBJECT')

    # Assign COL materials
    bpy.ops.object.assign_materials_fin()

    # Deselect all objects first
    bpy.ops.object.select_all(action='DESELECT')

    # Select all mesh objects at once for faster batch processing
    for obj in mesh_objects:
        obj.select_set(True)
        obj.data.material_choice = 'UV_TEX'

    # Ensure all objects are in object mode before proceeding
    bpy.ops.object.mode_set(mode='OBJECT')

    # Assign UV_TEX materials
    bpy.ops.object.assign_materials_fin()

    # Mark objects as assigned to prevent reprocessing
    for obj in mesh_objects:
        obj["material_assigned"] = True

    print("Batch material assignment complete.")
