"""
Name:    fin_in
Purpose: Imports Re-Volt instance files (.fin)

Description:
Imports Instance files.

"""

import bpy
import bmesh
import mathutils
import importlib
from . import common
from . import rvstruct
from . import prm_out

# Check if 'bpy' is already in locals to determine if this is a reload scenario
if "bpy" in locals():
    importlib.reload(common)
    importlib.reload(rvstruct)

# Importing specific classes and functions
from .props.props_obj import RVObjectProperties
from .props.props_scene import RVSceneProperties
from .rvstruct import Instances, Instance, Vector, Color

# Add specific imports from common as needed
# Example: from .common import specific_function, SpecificClass


def export_file(filepath, scene):
    fin = Instances()

    # Gathers list of instance objects
    objs = [obj for obj in scene.objects if "is_instance" in obj and obj["is_instance"]]


    for obj in objs:
        props = obj.revolt
        instance = Instance()

        instance.name = obj.name.split(".prm")[0][:8].upper()
        instance.color = (
                int(props.fin_col[0] * 255)-128,
                int(props.fin_col[1] * 255)-128,
                int(props.fin_col[2] * 255)-128
        )
        print(instance.color)
        instance.env_color = rvstruct.Color(
            color= (
                int(props.fin_envcol[0] * 255),
                int(props.fin_envcol[1] * 255),
                int(props.fin_envcol[2] * 255),
            ), 
            alpha=True
        )
        instance.env_color.alpha = int((1-props.fin_envcol[3]) * 255)
        instance.priority = props.fin_priority

        instance.lod_bias = props.fin_lod_bias

        instance.position = Vector(data=to_revolt_coord(obj.location))

        instance.or_matrix = rvstruct.Matrix()
        instance.or_matrix.data = to_or_matrix(obj.matrix_world)

        instance.flag = FIN_SET_MODEL_RGB

        if props.fin_env:
            instance.flag |= FIN_ENV

        if props.fin_model_rgb:
            instance.flag |= FIN_SET_MODEL_RGB

        if props.fin_hide:
            instance.flag |= FIN_HIDE

        if props.fin_no_mirror:
            instance.flag |= FIN_NO_MIRROR

        if props.fin_no_lights:
            instance.flag |= FIN_NO_LIGHTS

        if props.fin_no_cam_coll:
            instance.flag |= FIN_NO_CAMERA_COLLISION

        if props.fin_no_obj_coll:
            instance.flag |= FIN_NO_OBJECT_COLLISION


        folder = os.sep.join(filepath.split(os.sep)[:-1])

        prm_fname = "{}.prm".format(instance.name).lower()


        # Searches for files that are longer than 8 chars
        if not prm_fname in os.listdir(folder):
            scene.objects.active = obj
            prev_apply_scale = scene.revolt.apply_scale
            prev_apply_rotation = scene.revolt.apply_rotation

            scene.revolt.apply_scale = False
            scene.revolt.apply_rotation = False
            prm_out.export_file(os.path.join(folder, prm_fname), scene)

            scene.revolt.apply_scale = prev_apply_scale
            scene.revolt.apply_rotation = prev_apply_rotation


        instance.name += "\x00"
        fin.instances.append(instance)

    fin.instance_count = len(fin.instances)

    with open(filepath, "wb") as fd:
        fin.write(fd)


