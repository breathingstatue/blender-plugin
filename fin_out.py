"""
Name:    fin_out
Purpose: Exports Re-Volt instance files (.fin)

Description:
Exports Instance files.

"""

import re
import os
import bpy
from . import common
from . import rvstruct
from . import prm_out_for_fin

from .rvstruct import Instances, Instance, Vector, Matrix, Color
from .common import to_revolt_coord, to_or_matrix, FIN_SET_MODEL_RGB, FIN_ENV, FIN_HIDE, FIN_NO_MIRROR, FIN_NO_LIGHTS
from .common import FIN_NO_CAMERA_COLLISION, FIN_NO_OBJECT_COLLISION


if "bpy" in locals():
    import imp
    imp.reload(common)
    imp.reload(rvstruct)
    imp.reload(prm_out_for_fin)


def export_file(filepath, scene):
    print("Starting export...")  
    scene = bpy.context.scene
    fin = rvstruct.Instances()

    bpy.ops.object.mode_set(mode='OBJECT')
    print("Switched to Object Mode")  

    # Collect all mesh objects for export
    bpy.ops.object.select_all(action='SELECT')
    mesh_objects = [obj for obj in bpy.context.selected_objects if obj.type == 'MESH']
    
    if not mesh_objects:
        print("No mesh objects available for export.")
        return

    print(f"Found {len(mesh_objects)} mesh objects")  

    # Batch process materials: First COL, then UV_TEX
    assign_material_to_meshes(mesh_objects, 'COL')
    assign_material_to_meshes(mesh_objects, 'UV_TEX')

    # Group objects by PRM base name
    objects_by_base_name = {}
    for obj in mesh_objects:
        if obj.get("is_instance", False):
            base_name, _ = get_base_name_for_layers(obj)
            if base_name not in objects_by_base_name:
                objects_by_base_name[base_name] = []
            objects_by_base_name[base_name].append(obj)

    exported_prms = set()

    # Batch PRM export
    for base_name, objects in objects_by_base_name.items():
        if base_name in exported_prms:
            continue  # Skip already exported PRMs

        print(f"Batch exporting PRM for {base_name}.prm with {len(objects)} objects")  

        # Select all objects sharing the same base name
        bpy.ops.object.select_all(action='DESELECT')
        for obj in objects:
            obj.select_set(True)

        bpy.context.view_layer.objects.active = objects[0]  # Set one active for export

        folder = os.path.dirname(filepath)
        prm_fname = f"{base_name}.prm"

        # Perform batch PRM export using prm_out_for_fin
        prm_out_for_fin.export_file(os.path.join(folder, prm_fname), scene)

        exported_prms.add(base_name)  # Mark as exported

        # Add instances to FIN
        for obj in objects:
            instance = Instance()
            instance.name = base_name[:8].upper()

            fin_col = obj.get("fin_col", [0.5, 0.5, 0.5])
            instance.color = (
                int(fin_col[0] * 255) - 128,
                int(fin_col[1] * 255) - 128,
                int(fin_col[2] * 255) - 128,
            )
            print(f"Instance {instance.name} with color {instance.color}")  

            fin_envcol = obj.get("fin_envcol", [0.5, 0.5, 0.5, 1.0])
            instance.env_color = rvstruct.Color(
                color=(
                    int(fin_envcol[0] * 255),
                    int(fin_envcol[1] * 255),
                    int(fin_envcol[2] * 255),
                ),
                alpha=int((1 - fin_envcol[3]) * 255)
            )

            instance.position = Vector(data=to_revolt_coord(obj.location))
            instance.or_matrix = rvstruct.Matrix()
            instance.or_matrix.data = to_or_matrix(obj.matrix_world)

            # Assign instance flags
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

            instance.name += "\x00"
            fin.instances.append(instance)

    fin.instance_count = len(fin.instances)

    print("Writing to FIN file...")  
    with open(filepath, "wb") as fd:
        fin.write(fd)
    print(f"Export complete: {len(fin.instances)} instances exported to {filepath}")  


def assign_material_to_meshes(mesh_objects, material_choice):
    """Assign materials to mesh objects in bulk by switching to edit mode."""
    if not mesh_objects:
        print("No mesh objects for material assignment.")
        return

    bpy.ops.object.select_all(action='DESELECT')
    for obj in mesh_objects:
        obj.select_set(True)
        obj.data.material_choice = material_choice

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
