"""
Name:    w_out
Purpose: Exports Re-Volt level world files (.w)

Description:
World files contain meshes, optimization data and texture animations.

"""

if "bpy" in locals():
    import imp
    imp.reload(common)
    imp.reload(rvstruct)
    imp.reload(img_in)
    imp.reload(prm_out)

import os
import bpy
import bmesh
import json
from mathutils import Color, Vector
from . import (
    common,
    rvstruct,
    img_in,
    prm_out
)
from .common import *
from .prm_out import export_mesh


def export_file(filepath, scene):
    # Creates an empty world object to put the scene into
    world = rvstruct.World()

    objs = []
    # Goes through all objects and adds the exportable ones to the list
    for obj in scene.objects:
        conditions = (
            obj.data and
            obj.type == "MESH" and
            not obj.get("is_instance") and
            not obj.get("is_cube") and
            not obj.get("is_bcube") and
            not obj.get("is_bbox") and
            not obj.get("is_mirror_plane") and
            not obj.get("is_hull_sphere") and
            not obj.get("is_hull_convex") and
            not obj.get("is_track_zone")
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
    animations = json.loads(scene.texture_animations)
    print("Exporting texture animations...")
    for animdict in animations:
        anim = rvstruct.TexAnimation()
        anim.from_dict(animdict)
        if not all(frame is not None for frame in anim.frames):
            print("Warning: Found a None frame in texture animation.")
        world.animations.append(anim)
    world.animation_count = scene.ta_max_slots
    scene.texture_animations = json.dumps(animations)

    # Writes the world to a file
    with open(filepath, "wb") as file:
        world.write(file)
