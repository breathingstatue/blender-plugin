"""
Name:    w_out
Purpose: Exports Re-Volt level world files (.w)

Description:
World files contain meshes, optimization data and texture animations.

"""

import os
import bpy
import bmesh
import importlib
from mathutils import Color, Vector
from . import common
from . import rvstruct
from . import img_in
from . import prm_out

# Check if 'bpy' is already in locals to determine if this is a reload scenario
if "bpy" in locals():
    importlib.reload(common)
    importlib.reload(rvstruct)
    importlib.reload(img_in)
    importlib.reload(prm_out)
    
# Importing specific functions and classes
from .prm_out import export_mesh

# Add specific imports from common as needed
# Example: from .common import specific_function, SpecificClass

def export_file(filepath, scene):
    props = scene.revolt
    # Creates an empty world object to put the scene into
    world = rvstruct.World()

    objs = []
    # Goes through all objects and adds the exportable ones to the list
    for obj in scene.objects:
        conditions = (
            obj.data and
            obj.type == "MESH" and
            not obj.revolt.is_instance and
            not obj.revolt.is_cube and
            not obj.revolt.is_bcube and
            not obj.revolt.is_bbox and
            not obj.revolt.is_mirror_plane and
            not obj.revolt.is_hull_sphere and
            not obj.revolt.is_hull_convex and
            not obj.revolt.is_track_zone
        )
        if conditions:
            objs.append(obj)

    # Goes through all objects from the scene and exports them to PRM/Mesh
    for obj in objs:
        me = obj.data
        print("Exporting mesh for {}".format(obj.name))
        mesh = export_mesh(me, obj, scene, filepath, world=world)
        if mesh:
            world.meshes.append(mesh)
        else:
            queue_error(
                "exporting World",
                "A mesh could not be exported."
            )

    world.mesh_count = len(world.meshes)
    # Generates one big cube (sphere) around the scene
    world.generate_bigcubes()

    # Exports the texture animation
    animations = eval(props.texture_animations)
    for animdict in animations:
        anim = rvstruct.TexAnimation()
        anim.from_dict(animdict)
        world.animations.append(anim)
    world.animation_count = props.ta_max_slots

    # Writes the world to a file
    with open(filepath, "wb") as file:
        world.write(file)
