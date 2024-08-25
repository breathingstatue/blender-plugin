"""
Name:    fin_in
Purpose: Imports Re-Volt instance files (.fin)

Description:
Imports Instance files.

"""

import re
import os
import bpy
import bmesh
import mathutils

from . import common
from . import rvstruct
from . import prm_out

from .rvstruct import Instances, Instance, Vector, Color, Matrix
from .common import to_revolt_coord, FIN_SET_MODEL_RGB, to_or_matrix, FIN_ENV, FIN_HIDE, FIN_NO_MIRROR, FIN_NO_LIGHTS
from .common import FIN_NO_CAMERA_COLLISION, FIN_NO_OBJECT_COLLISION
from .tools import set_material_to_col_for_object, set_material_to_texture_for_object

if "bpy" in locals():
    import imp
    imp.reload(common)
    imp.reload(rvstruct)

def export_file(filepath, scene):
    scene = bpy.context.scene
    fin = rvstruct.Instances()

    # Ensure we're in object mode before any operations
    bpy.ops.object.mode_set(mode='OBJECT')

    # Select all mesh objects in the scene
    bpy.ops.object.select_all(action='SELECT')
    mesh_objects = [obj for obj in bpy.context.selected_objects if obj.type == 'MESH']
    
    if not mesh_objects:
        print("No mesh objects available for export.")
        return

    # Apply material settings using the imported utility functions
    for obj in mesh_objects:
        set_material_to_col_for_object(obj)
        set_material_to_texture_for_object(obj)

    # Perform the export process
    objs = [obj for obj in mesh_objects if obj.get("is_instance", False)]

    # Dictionary to keep track of objects by their base name
    objects_by_base_name = {}
    for obj in objs:
        base_name, _ = get_base_name_for_layers(obj)
        if base_name not in objects_by_base_name:
            objects_by_base_name[base_name] = []
        objects_by_base_name[base_name].append(obj)

    # Set to keep track of already exported PRM files
    exported_prms = set()

    for base_name, objects in objects_by_base_name.items():
        for obj in objects:
            instance = Instance()

            # Use the cleaned base name for the instance name
            instance.name = base_name[:8].upper()

            # Access custom properties with a fallback default
            fin_col = obj.get("fin_col", [0.5, 0.5, 0.5])
            instance.color = (
                int(fin_col[0] * 255) - 128,
                int(fin_col[1] * 255) - 128,
                int(fin_col[2] * 255) - 128,
            )
            print(f"Exporting instance with color: {instance.color}")

            fin_envcol = obj.get("fin_envcol", [0.5, 0.5, 0.5, 1.0])
            instance.env_color = rvstruct.Color(
                color=(
                    int(fin_envcol[0] * 255),
                    int(fin_envcol[1] * 255),
                    int(fin_envcol[2] * 255),
                ),
                alpha=True
            )
            instance.env_color.alpha = int((1 - fin_envcol[3]) * 255)

            # Access other custom properties similarly
            instance.priority = obj.get("fin_priority", 1)
            instance.lod_bias = obj.get("fin_lod_bias", 1024)

            # Position and orientation
            instance.position = Vector(data=to_revolt_coord(obj.location))
            instance.or_matrix = rvstruct.Matrix()
            instance.or_matrix.data = to_or_matrix(obj.matrix_world)

            # Flags
            instance.flag = 0

            if obj.get("fin_env", False):
                instance.flag |= FIN_ENV

            if obj.get("fin_model_rgb", False):
                instance.flag |= FIN_SET_MODEL_RGB

            if obj.get("fin_hide", False):
                instance.flag |= FIN_HIDE

            if obj.get("fin_no_mirror", False):
                instance.flag |= FIN_NO_MIRROR

            if obj.get("fin_no_lights", False):
                instance.flag |= FIN_NO_LIGHTS

            if obj.get("fin_no_cam_coll", False):
                instance.flag |= FIN_NO_CAMERA_COLLISION

            if obj.get("fin_no_obj_coll", False):
                instance.flag |= FIN_NO_OBJECT_COLLISION

            folder = os.sep.join(filepath.split(os.sep)[:-1])

            # Ensure the base name ends with .prm but avoid adding .prm twice
            if not base_name.endswith(".prm"):
                prm_fname = f"{base_name}.prm"
            else:
                prm_fname = base_name

            # Ensure the objects with the same base name are exported as a single .prm file
            if prm_fname not in exported_prms:
                bpy.context.view_layer.objects.active = obj
                prev_apply_scale = scene.apply_scale
                prev_apply_rotation = scene.apply_rotation

                scene.apply_rotation = False
                scene.apply_scale = False
                prm_out.export_file(os.path.join(folder, prm_fname), scene)

                scene.apply_rotation = prev_apply_rotation
                scene.apply_scale = prev_apply_scale

                exported_prms.add(prm_fname)

            instance.name += "\x00"
            fin.instances.append(instance)

    fin.instance_count = len(fin.instances)

    with open(filepath, "wb") as fd:
        fin.write(fd)

    print(f"Exported {len(fin.instances)} instances to {filepath}")

def set_material_to_col():
    """Sets the material to Vertex Colour (_Col) for all selected mesh objects."""
    mesh_objects = [obj for obj in bpy.context.selected_objects if obj.type == 'MESH']
    
    if not mesh_objects:
        print("No mesh objects selected for material assignment.")
        return

    for obj in mesh_objects:
        bpy.context.view_layer.objects.active = obj
        obj.data.material_choice = 'COL'

        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.object.assign_materials_auto()
        bpy.ops.object.mode_set(mode='OBJECT')

def set_material_to_texture():
    """Sets the material to Texture (UV_TEX) for all selected mesh objects."""
    mesh_objects = [obj for obj in bpy.context.selected_objects if obj.type == 'MESH']
    
    if not mesh_objects:
        print("No mesh objects selected for material assignment.")
        return

    for obj in mesh_objects:
        bpy.context.view_layer.objects.active = obj
        obj.data.material_choice = 'UV_TEX'

        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.object.assign_materials_auto()
        bpy.ops.object.mode_set(mode='OBJECT')
        
def get_base_name_for_layers(obj):
    """Generates a clean base name for the object by removing unnecessary suffixes and handling extensions."""
    name = obj.name.lower()

    # Remove any numeric suffixes like .001, _01, etc.
    base_name = re.sub(r'[\._-]\d+$', '', name)

    # If the name ends with .prm, remove it temporarily for further processing
    if base_name.endswith('.prm'):
        base_name = base_name[:-4]  # Remove the .prm extension

    # Now, remove any additional dots or segments after the base name
    base_name = base_name.split('.')[0]

    # Reattach the .prm extension only if it's not already there
    return base_name, ''

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