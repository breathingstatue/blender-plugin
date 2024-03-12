"""
Name:    fin_in
Purpose: Imports Re-Volt instance files (.fin)

Description:
Imports Instance files.

"""

if "bpy" in locals():
    import imp
    imp.reload(common)
    imp.reload(rvstruct)

import bpy
import bmesh
import mathutils

from . import common
from . import rvstruct
from . import prm_out

from .rvstruct import Instances, Instance, Vector, Color
from .common import *


def export_file(filepath, scene):
    fin = Instances()

    # Gathers list of instance objects
    objs = [obj for obj in scene.objects if obj.is_instance]


    for obj in objs:
        instance = Instance()

        instance.name = obj.name.split(".prm")[0][:8].upper()
        fin_col = getattr(obj, "fin_col", [0.5, 0.5, 0.5])  # Default to mid-gray if not set
        instance.color = (
            int(fin_col[0] * 255) - 128,
            int(fin_col[1] * 255) - 128,
            int(fin_col[2] * 255) - 128,
        )
        print(instance.color)
        instance.env_color = rvstruct.Color(
            color= (
                int(obj.fin_envcol[0] * 255),
                int(obj.fin_envcol[1] * 255),
                int(obj.fin_envcol[2] * 255),
            ), 
            alpha=True
        )
        instance.env_color.alpha = int((1-obj.fin_envcol[3]) * 255)
        instance.priority = obj.fin_priority

        instance.lod_bias = obj.fin_lod_bias

        instance.position = Vector(data=to_revolt_coord(obj.location))

        instance.or_matrix = rvstruct.Matrix()
        instance.or_matrix.data = to_or_matrix(obj.matrix_world)

        instance.flag = FIN_SET_MODEL_RGB

        if obj.fin_env:
            instance.flag |= FIN_ENV

        if obj.fin_model_rgb:
            instance.flag |= FIN_SET_MODEL_RGB

        if obj.fin_hide:
            instance.flag |= FIN_HIDE

        if obj.fin_no_mirror:
            instance.flag |= FIN_NO_MIRROR

        if obj.fin_no_lights:
            instance.flag |= FIN_NO_LIGHTS

        if obj.fin_no_cam_coll:
            instance.flag |= FIN_NO_CAMERA_COLLISION

        if obj.fin_no_obj_coll:
            instance.flag |= FIN_NO_OBJECT_COLLISION


        folder = os.sep.join(filepath.split(os.sep)[:-1])

        prm_fname = "{}.prm".format(instance.name).lower()


        # Searches for files that are longer than 8 chars
        if not prm_fname in os.listdir(folder):
            scene.objects.active = obj
            prev_apply_scale = scene.apply_scale
            prev_apply_rotation = scene.apply_rotation

            scene.apply_rotation = False
            scene.apply_scale = False
            prm_out.export_file(os.path.join(folder, prm_fname), scene)

            scene.apply_rotation = prev_apply_scale
            scene.apply_scale = prev_apply_rotation


        instance.name += "\x00"
        fin.instances.append(instance)

    fin.instance_count = len(fin.instances)

    with open(filepath, "wb") as fd:
        fin.write(fd)


