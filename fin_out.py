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

if "bpy" in locals():
    import imp
    imp.reload(common)
    imp.reload(rvstruct)


def export_file(filepath, scene):
    scene = bpy.context.scene
    fin = Instances()

    # Gathers list of instance objects
    objs = [obj for obj in scene.objects if obj.get("is_instance", False) and obj.type == 'MESH']

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

            # Use the base mesh name for the instance name
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
            prm_fname = "{}.prm".format(instance.name).lower()

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
        
def get_base_name_for_layers(obj):
    """Generates a base name for the object by removing numeric suffixes and delimiters."""
    name = obj.name
    # Regular expression to remove numeric suffixes like .001, _01, etc.
    base_name = re.sub(r'[\._-]\d+$', '', name)
    
    extension = ""
    specific_parts = ["body", "wheel", "axle", "spring"]

    if ".w" in name:
        extension = ".w"
    elif ".prm" in name or any(part in name for part in specific_parts):
        extension = ".prm"

    return f"{base_name}{extension}", ''