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
import struct
from mathutils import Vector
from collections import deque
from . import (
    common,
    rvstruct,
    img_in,
    prm_out
)
from .common import *
from .prm_out import (
    export_mesh,
    get_texture_from_material
)

def update_split_size(self, context):
    value = self.split_size_faces  # Assuming this is correctly set somewhere
    self.actual_split_size = value * 2

def get_connected_faces(bm, start_face, max_faces, visited_faces):
    """Collect connected faces sharing the same material, starting from start_face."""
    material_index = start_face.material_index
    queue = deque([start_face])
    connected_faces = []

    while queue and len(connected_faces) < max_faces:
        face = queue.popleft()
        if face.index not in visited_faces:
            visited_faces.add(face.index)
            connected_faces.append(face.index)
            if face.material_index == material_index:
                for edge in face.edges:
                    for linked_face in edge.link_faces:
                        if linked_face.index not in visited_faces and linked_face.material_index == material_index:
                            queue.append(linked_face)
                            if len(connected_faces) >= max_faces:
                                break

    return connected_faces

def create_split_mesh(original_mesh, face_indices, original_obj_name, created_objects):
    new_mesh = bpy.data.meshes.new(name=f"{original_obj_name}_split_mesh")
    original_bm = bmesh.new()
    original_bm.from_mesh(original_mesh)
    original_bm.verts.ensure_lookup_table()
    original_bm.faces.ensure_lookup_table()

    split_bm = bmesh.new()

    vert_map = {}
    used_materials = set()

    # Identify all materials used by the subset of faces
    for face_index in face_indices:
        face = original_bm.faces[face_index]
        used_materials.add(face.material_index)

    # Map old material indices to new indices
    material_map = {old_idx: idx for idx, old_idx in enumerate(used_materials)}
    new_mesh.materials.clear()
    for old_idx in used_materials:
        new_mesh.materials.append(original_mesh.materials[old_idx])

    uv_layers = {layer.name: split_bm.loops.layers.uv.new(layer.name) for layer in original_bm.loops.layers.uv}
    vc_layers = {layer.name: split_bm.loops.layers.color.new(layer.name) for layer in original_bm.loops.layers.color} if original_bm.loops.layers.color else {}

    # Create new vertices and faces in split_bm
    for face_index in face_indices:
        face = original_bm.faces[face_index]
        new_verts = []
        for vert in face.verts:
            if vert.index not in vert_map:
                new_vert = split_bm.verts.new(vert.co)
                vert_map[vert.index] = new_vert
            new_verts.append(vert_map[vert.index])

        new_face = split_bm.faces.new(new_verts)
        new_face.material_index = material_map[face.material_index]  # Remap material index

        # Copy UV and vertex color data
        for l, loop in enumerate(face.loops):
            new_loop = new_face.loops[l]
            for layer_name, layer in uv_layers.items():
                new_loop[layer].uv = loop[original_bm.loops.layers.uv[layer_name]].uv
            for color_name, color_layer in vc_layers.items():
                new_loop[color_layer] = loop[original_bm.loops.layers.color[color_name]]

    split_bm.to_mesh(new_mesh)
    new_obj = bpy.data.objects.new(name=f"{original_obj_name}_split_{len(created_objects)}", object_data=new_mesh)
    bpy.context.collection.objects.link(new_obj)
    created_objects.append(new_obj)  # Add to the created objects list
    split_bm.free()
    print(f"Created and linked new mesh with {len(face_indices)} faces.")
    return new_mesh

def split_mesh(obj, split_size, created_objects):
    print(f"Checking if object {obj.name} should be split.")
    if '_split_' in obj.name:
        print(f"Skipping already split object: {obj.name}")
        return []

    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.faces.ensure_lookup_table()
    
    split_meshes = []
    visited_faces = set()

    for face in bm.faces:
        if face.index not in visited_faces:
            face_indices = get_connected_faces(bm, face, split_size, visited_faces)
            if face_indices:
                new_mesh = create_split_mesh(mesh, face_indices, obj.name, created_objects)
                new_obj_name = f"{obj.name}_split_{len(split_meshes)}"
                new_obj = bpy.data.objects.new(name=new_obj_name, object_data=new_mesh)
                bpy.context.collection.objects.link(new_obj)
                created_objects.append(new_obj)  # Add to the created objects list
                split_meshes.append(new_obj)

    bm.free()
    return split_meshes

def split_meshes(scene_objects, split_size, created_objects):
    split_meshes_list = []
    process_queue = deque(scene_objects)  # Use a queue to manage objects to be processed

    while process_queue:
        obj = process_queue.popleft()
        if obj.type == 'MESH' and not obj.hide_render:
            if '_split_' not in obj.name:  # Check if the object is not already a split object
                split_objs = split_mesh(obj, split_size, created_objects)
                split_meshes_list.extend(split_objs)
                print(f"Split {obj.name} into {len(split_objs)} parts.")
                for split_obj in split_objs:
                    process_queue.append(split_obj)  # Add new splits to the queue if needed
            else:
                print(f"Skipping already split object: {obj.name}")

    return split_meshes_list

def cleanup_split_objects(objects_list):
    for obj in objects_list:
        try:
            bpy.data.objects.remove(obj, do_unlink=True)
            print(f"Removed object {obj.name} successfully.")
        except ReferenceError:
            pass  # Ignore if object is already removed
        except Exception as e:
            print(f"Failed to remove object {obj.name}: {str(e)}")

def export_split_world(filepath, context, split_size):
    scene = context.scene
    world = rvstruct.World()
    split_meshes_list = []  # Initialize at the beginning of the function
    created_objects = []  # List to track created objects

    if not world:
        print("Failed to instantiate world object.")
        return

    try:
        split_meshes_list = split_meshes(scene.objects, split_size, created_objects)
        for split_obj in split_meshes_list:
            converted_mesh = export_mesh(split_obj.data, split_obj, scene, filepath, world=world)
            if converted_mesh:
                world.meshes.append(converted_mesh)

        world.mesh_count = len(world.meshes)
        world.generate_bigcubes()

        with open(filepath, "wb") as file:
            world.write(file)
        print("Export successful!")
    except Exception as e:
        print(f"Failed to export due to an error: {e}")
    finally:
        cleanup_split_objects(created_objects)
        print("Cleanup completed, all temporary objects removed.")

def export_standard_world(filepath, context):
    scene = context.scene
    world = rvstruct.World()
    objs = [obj for obj in scene.objects if obj_conditions(obj)]
    try:
        for obj in objs:
            me = obj.data
            print(f"Exporting mesh for {obj.name}")
            mesh = export_mesh(me, obj, scene, filepath, world=world)
            if mesh:
                world.meshes.append(mesh)

        world.mesh_count = len(world.meshes)
        world.generate_bigcubes()

        with open(filepath, "wb") as file:
            world.write(file)
        print("Export successful!")
    except Exception as e:
        print(f"Failed to export due to an error: {e}")

def obj_conditions(obj):
    return (obj.data and
            obj.type == "MESH" and
            not any(obj.get(attr) for attr in ["is_instance", "is_cube", "is_bcube", "is_bbox", "is_mirror_plane", "is_hull_sphere", "is_hull_convex", "is_track_zone"]))

def export_file(filepath, scene, context):
    if getattr(context.scene, 'export_worldcut', False):
        split_size = getattr(context.scene, 'actual_split_size', 100)  # Use the actual_split_size for calculations.
        print(f"Exporting World as split meshes with {split_size} faces per segment.")
        export_split_world(filepath, context, split_size)
    else:
        print("Exporting World.")
        export_standard_world(filepath, context)
