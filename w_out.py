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
from . import common, rvstruct, img_in, prm_out
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
    
    # Call this function in your export process before processing animations
    ensure_default_animation_entry(bpy.context.scene)

    # Exports the texture animation
    animations = json.loads(scene.texture_animations)
    for animdict in animations:
        anim = rvstruct.TexAnimation()
        anim.from_dict(animdict)
        world.animations.append(anim)
    world.animation_count = scene.ta_max_slots

    # Writes the world to a file
    with open(filepath, "wb") as file:
        world.write(file)
        
def ensure_default_animation_entry(scene):
    # Check if there are existing animations; if not, create a default entry
    if not scene.texture_animations.strip():
        # Define a default animation entry structure
        default_animation_entry = {
            "slot": 0,
            "frame_start": 0,
            "frame_end": 0,
            "frame_count": 0,
            "frames": [],
            "texture": "",
            "delay": 0,
        }

        # Initialize texture_animations with the default animation entry
        scene.texture_animations = json.dumps([default_animation_entry])
    else:
        # Load existing animations and check if there's a need to append a new default entry
        animations = json.loads(scene.texture_animations)
        
        # Determine the next available slot if you need to add a new entry
        # This example just appends a new default entry without specific conditions
        # Modify this logic based on how you want to handle multiple entries
        next_slot = len(animations)
        new_animation_entry = {
            "slot": next_slot,
            "frame_start": 0,
            "frame_end": 0,
            "frame_count": 0,
            "frames": [],
            "texture": "",
            "delay": 0,
        }
        animations.append(new_animation_entry)

        # Save the updated animations back to the scene
        scene.texture_animations = json.dumps(animations)
