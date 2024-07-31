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
from . import rvstruct
from . import prm_in

# Check if 'bpy' is already in locals to determine if this is a reload scenario
if "bpy" in locals():
    importlib.reload(common)
    importlib.reload(rvstruct)

# Importing specific classes and functions
from .common import to_trans_matrix, to_blender_coord, FIN_SET_MODEL_RGB, FIN_ENV, FIN_HIDE, FIN_NO_MIRROR, FIN_NO_LIGHTS
from .common import FIN_NO_OBJECT_COLLISION, FIN_NO_CAMERA_COLLISION
from .rvstruct import Instances, Vector
from mathutils import Color

# You can add specific imports from common as needed
# Example: from .common import function_name, ClassName


def import_file(filepath, scene):

    with open(filepath, 'rb') as file:
        filename = os.path.basename(filepath)
        fin = Instances(file)
        print("Imported FIN file.")

    for instance in fin.instances:
        import_instance(filepath, scene, instance)


def import_instance(filepath, scene, instance):
    folder = os.sep.join(filepath.split(os.sep)[:-1])

    prm_fname = "{}.prm".format(instance.name).lower()

    # Searches for files that are longer than 8 chars
    if not prm_fname in os.listdir(folder):
        for f in os.listdir(folder):
            if f.startswith(instance.name.lower()) and ".prm" in f:
                prm_fname = f
                break

    if prm_fname in [ob.name for ob in scene.objects]:
        print("Found already existing instance: {}".format(prm_fname))
        data = scene.objects[prm_fname].data

        # Creates a duplicate object and links it to the scene
        instance_obj = bpy.data.objects.new(name=prm_fname, object_data=data)
        if instance_obj is not None:
            scene.collection.objects.link(instance_obj)

    elif prm_fname in os.listdir(folder):
        print("Found prm in dir.")
        prm_path = os.path.join(folder, prm_fname)
        # Creates the object and links it to the scene
        instance_obj = prm_in.import_file(prm_path, bpy.context.scene)

    else:
        print("Could not find instance {} at {}".format(prm_fname, folder))
        # Creates an empty object instead
        instance_obj = bpy.data.objects.new("prm_fname", None)
        if instance_obj is not None:
            scene.collection.objects.link(instance_obj)
        instance_obj.empty_draw_type = "SPHERE"

    instance_obj.matrix_world = to_trans_matrix(instance.or_matrix)
    instance_obj.location = to_blender_coord(instance.position)

    instance_obj.is_instance = True
    instance_obj.fin_col = [(128 + c) / 255 for c in instance.color]
    envcol = (*instance.env_color.color, 255 - instance.env_color.alpha)
    instance_obj.fin_envcol = [c / 255 for c in envcol]
    instance_obj.fin_priority = instance.priority

    flag = instance.flag
    instance_obj.fin_model_rgb = bool(flag & FIN_SET_MODEL_RGB)
    instance_obj.fin_env = bool(flag & FIN_ENV)
    instance_obj.fin_hide = bool(flag & FIN_HIDE)
    instance_obj.fin_no_mirror = bool(flag & FIN_NO_MIRROR)
    instance_obj.fin_no_lights = bool(flag & FIN_NO_LIGHTS)
    instance_obj.fin_no_cam_coll = bool(flag & FIN_NO_OBJECT_COLLISION)
    instance_obj.fin_no_obj_coll = bool(flag & FIN_NO_CAMERA_COLLISION)


