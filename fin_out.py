"""
Name:    fin_in
Purpose: Imports Re-Volt instance files (.fin)

Description:
Imports Instance files.

"""

import bpy
import bmesh
import mathutils

from . import common
from . import rvstruct
from . import prm_out

from .rvstruct import Instances, Instance, Vector, Color
from .common import *

if "bpy" in locals():
    import imp
    imp.reload(common)
    imp.reload(rvstruct)


def export_file(filepath, context):
    scene = context.scene
    fin = Instances()

    # Gathers list of instance objects
    objs = [obj for obj in scene.objects if obj.get("is_instance", False)]

    for obj in objs:
        instance = Instance()

        instance.name = obj.name.split(".prm")[0][:8].upper()
    
        # Access custom properties with a fallback default
        fin_col = obj.get("fin_col", [0.5, 0.5, 0.5])
        instance.color = (
            int(fin_col[0] * 255) - 128,
            int(fin_col[1] * 255) - 128,
            int(fin_col[2] * 255) - 128,
        )
        print(instance.color)

        # Assuming fin_envcol is an RGBA value stored as a custom property
        fin_envcol = obj.get("fin_envcol", [0.5, 0.5, 0.5, 1.0])  # Default: mid-gray + opaque alpha
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
        instance.priority = obj.get("fin_priority", 0)
        instance.lod_bias = obj.get("fin_lod_bias", 0)
    
        # Position and orientation
        instance.position = Vector(data=to_revolt_coord(obj.location))
        instance.or_matrix = rvstruct.Matrix()
        instance.or_matrix.data = to_or_matrix(obj.matrix_world)
    
        # Flags
        instance.flag = obj.get("FIN_SET_MODEL_RGB", 0)
    
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


        # Searches for files that are longer than 8 chars
        if not prm_fname in os.listdir(folder):
            bpy.context.view_layer.objects.active = obj
            prev_apply_scale = scene.apply_scale
            prev_apply_rotation = scene.apply_rotation

            scene.apply_rotation = False
            scene.apply_scale = False
            prm_out.export_file(os.path.join(folder, prm_fname), scene, context)

            scene.apply_rotation = prev_apply_scale
            scene.apply_scale = prev_apply_rotation


        instance.name += "\x00"
        fin.instances.append(instance)

    fin.instance_count = len(fin.instances)

    with open(filepath, "wb") as fd:
        fin.write(fd)


