"""
Name:    w_out
Purpose: Exports Re-Volt level world files (.w)

Description:
World files contain meshes, optimization data, and texture animations.
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
import struct
from mathutils import Vector
from . import (
	common,
	rvstruct,
	img_in,
	prm_out
)
from .common import *
from .prm_out import export_mesh

def get_context_override():
    for window in bpy.context.window_manager.windows:
        screen = window.screen
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                for region in area.regions:
                    if region.type == 'WINDOW':
                        # Only include necessary context components
                        override = {
                            'window': window,
                            'screen': screen,
                            'area': area,
                            'region': region,
                            'scene': bpy.context.scene,
                            'view_layer': bpy.context.view_layer
                        }
                        return override
    return None

def create_cubes_from_objects(objects):
    cubes = []
    for obj in objects:
        if obj.type == 'MESH':
            # Transform mesh vertices to world coordinates
            world_vertices = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]

            # Calculate the min and max extents in each direction
            min_coords = Vector((min(v.x for v in world_vertices), min(v.y for v in world_vertices), min(v.z for v in world_vertices)))
            max_coords = Vector((max(v.x for v in world_vertices), max(v.y for v in world_vertices), max(v.z for v in world_vertices)))

            # Calculate the center and dimensions
            dimensions = max_coords - min_coords
            center = (min_coords + max_coords) / 2

            # Use the largest dimension to ensure the cube covers everything
            cube_edge_length = max(dimensions.x, dimensions.y, dimensions.z)

            print(f"Object: {obj.name}, Center: {center}, Cube Edge Length: {cube_edge_length}")

            cubes.append((obj.name, center, cube_edge_length))
    return cubes

def batch_create_cubes(cubes_data):
    created_cubes = []
    context_override = get_context_override()
    
    if not context_override:
        print("Could not get context override")
        return []
    
    for name, center, cube_edge_length in cubes_data:
        # Create the cube at the calculated center with the specified size
        bpy.ops.mesh.primitive_cube_add(size=cube_edge_length, location=center, align='WORLD')
        cube = bpy.context.active_object
        if cube:
            cube.name = name + '_cube'
            created_cubes.append(cube)
            print(f"Cube created for {name}, Center: {center}, Edge Length: {cube_edge_length}")

    # Apply transformations to ensure the cubes are correctly scaled
    bpy.ops.object.select_all(action='DESELECT')
    for cube in created_cubes:
        cube.select_set(True)
    bpy.context.view_layer.objects.active = created_cubes[0] if created_cubes else None
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    return created_cubes

def delete_cubes(cubes):
    bpy.ops.object.select_all(action='DESELECT')
    for cube in cubes:
        cube.select_set(True)
    bpy.ops.object.delete()

def export_world_as_cubes(filepath, context):
    scene = context.scene
    world = rvstruct.World()

    # Create cubes from mesh objects
    mesh_objects = [obj for obj in scene.objects if obj.type == 'MESH']
    cubes_data = create_cubes_from_objects(mesh_objects)
    cubes = batch_create_cubes(cubes_data)

    # Export each cube
    for cube in cubes:
        print(f"Exporting cube for {cube.name}")
        mesh = export_mesh(cube.data, cube, scene, filepath, world=world)
        if mesh:
            world.meshes.append(mesh)
        else:
            queue_error("exporting World as Cubes", "A cube could not be exported.")

    world.mesh_count = len(world.meshes)
    world.generate_bigcubes()

    with open(filepath, "wb") as file:
        world.write(file)

    # Delete the cubes after exporting
    delete_cubes(cubes)

def export_standard_world(filepath, context):
    # Creates an empty world object to put the scene into
    scene = context.scene
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
        print(f"Exporting mesh for {obj.name}")
        mesh = export_mesh(me, obj, scene, filepath, world=world)
        if mesh:
            world.meshes.append(mesh)
        else:
            queue_error("exporting World", "A mesh could not be exported.")

    world.mesh_count = len(world.meshes)
    # Generates one big cube (sphere) around the scene
    world.generate_bigcubes()

    # Exports the texture animation
    #animations = eval(scene.texture_animations)
    #for animdict in animations:
    #    anim = rvstruct.TexAnimation()
    #    anim.from_dict(animdict)
    #    world.animations.append(anim)
    #world.animation_count = scene.ta_max_slots

    # Writes the world to a file
    with open(filepath, "wb") as file:
        world.write(file)

def export_file(filepath, scene, context):
    if getattr(context.scene, 'export_as_cubes', False):
        print("Exporting World as cubes.")
        export_world_as_cubes(filepath, context)
    else:
        print("Exporting World.")
        export_standard_world(filepath, context)