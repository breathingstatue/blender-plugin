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
from .prm_out import export_mesh, get_texture_from_material

def create_split_mesh(original_mesh, face_indices, original_obj_name, created_objects):
    new_mesh = bpy.data.meshes.new(name=f"{original_obj_name}_split_mesh")
    original_bm = bmesh.new()
    original_bm.from_mesh(original_mesh)
    original_bm.verts.ensure_lookup_table()
    original_bm.faces.ensure_lookup_table()

    split_bm = bmesh.new()

    vert_map = {}
    used_materials = set()

    for face_index in face_indices:
        face = original_bm.faces[face_index]
        if face.material_index < len(original_mesh.materials):
            used_materials.add(face.material_index)

    material_map = {old_idx: idx for idx, old_idx in enumerate(used_materials)}
    new_mesh.materials.clear()
    for old_idx in used_materials:
        if old_idx < len(original_mesh.materials):
            new_mesh.materials.append(original_mesh.materials[old_idx])

    uv_layers = {layer.name: split_bm.loops.layers.uv.new(layer.name) for layer in original_bm.loops.layers.uv}
    vc_layers = {layer.name: split_bm.loops.layers.color.new(layer.name) for layer in original_bm.loops.layers.color} if original_bm.loops.layers.color else {}

    env_layer = split_bm.loops.layers.color.new("Env") if original_bm.loops.layers.color.get("Env") else None
    env_alpha_layer = split_bm.faces.layers.float.new("EnvAlpha") if original_bm.faces.layers.float.get("EnvAlpha") else None
    va_layer = split_bm.loops.layers.color.new("Alpha") if original_bm.loops.layers.color.get("Alpha") else None
    texnum_layer = split_bm.faces.layers.int.new("Texture Number") if original_bm.faces.layers.int.get("Texture Number") else None
    type_layer = split_bm.faces.layers.int.new("Type") if original_bm.faces.layers.int.get("Type") else None

    # Custom properties layers
    custom_props_layers = {}
    custom_props = ["FACE_DOUBLE", "FACE_TRANSLUCENT", "FACE_MIRROR", "FACE_TRANSL_TYPE", "FACE_TEXANIM", "FACE_NOENV", "FACE_ENV", "FACE_CLOTH", "FACE_SKIP"]
    for prop in custom_props:
        if prop in original_bm.faces.layers.int:
            custom_props_layers[prop] = split_bm.faces.layers.int.new(prop)

    for face_index in face_indices:
        face = original_bm.faces[face_index]
        new_verts = []
        for vert in face.verts:
            if vert.index not in vert_map:
                new_vert = split_bm.verts.new(vert.co)
                vert_map[vert.index] = new_vert
            new_verts.append(vert_map[vert.index])

        try:
            new_face = split_bm.faces.new(new_verts)
        except ValueError:
            print(f"Skipping invalid face creation for vertices: {[v.index for v in new_verts]}")
            continue

        # Ensure the material index is valid before assigning it
        if face.material_index in material_map:
            new_face.material_index = material_map[face.material_index]
        else:
            new_face.material_index = 0  # Fallback to the first material if out of bounds

        for l, loop in enumerate(face.loops):
            new_loop = new_face.loops[l]
            for layer_name, layer in uv_layers.items():
                new_loop[layer].uv = loop[original_bm.loops.layers.uv[layer_name]].uv
            for color_name, color_layer in vc_layers.items():
                new_loop[color_layer] = loop[original_bm.loops.layers.color[color_name]]

        if env_layer:
            for l, loop in enumerate(face.loops):
                new_loop[env_layer] = loop[original_bm.loops.layers.color["Env"]]
        if env_alpha_layer:
            new_face[env_alpha_layer] = face[original_bm.faces.layers.float["EnvAlpha"]]
        if va_layer:
            for l, loop in enumerate(face.loops):
                new_loop[va_layer] = loop[original_bm.loops.layers.color["Alpha"]]
        if texnum_layer:
            new_face[texnum_layer] = face[original_bm.faces.layers.int["Texture Number"]]
        if type_layer:
            new_face[type_layer] = face[original_bm.faces.layers.int["Type"]]

        for prop, layer in custom_props_layers.items():
            if layer:
                new_face[layer] = face[original_bm.faces.layers.int[prop]]

    split_bm.to_mesh(new_mesh)
    new_mesh.update()  # Ensure normals are updated
    new_mesh.validate()  # Validate the mesh

    new_obj = bpy.data.objects.new(name=f"{original_obj_name}_split_{len(created_objects)}", object_data=new_mesh)
    bpy.context.collection.objects.link(new_obj)
    created_objects.append(new_obj)

    for prop in original_mesh.keys():
        new_obj[prop] = original_mesh[prop]

    for prop in ["is_instance", "is_cube", "is_bcube", "is_bbox", "is_mirror_plane", "is_hull_sphere", "is_hull_convex", "is_track_zone"]:
        if hasattr(original_mesh, prop):
            setattr(new_obj, prop, getattr(original_mesh, prop))

    split_bm.free()
    print(f"Created and linked new mesh with {len(face_indices)} faces.")
    return new_obj

def calculate_bounding_box(mesh):
    min_x = min_y = min_z = float('inf')
    max_x = max_y = max_z = float('-inf')

    for vert in mesh.vertices:
        min_x = min(min_x, vert.co.x)
        max_x = max(max_x, vert.co.x)
        min_y = min(min_y, vert.co.y)
        max_y = max(max_y, vert.co.y)
        min_z = min(min_z, vert.co.z)
        max_z = max(max_z, vert.co.z)

    return (min_x, max_x), (min_y, max_y), (min_z, max_z)

def simple_split_mesh_by_grid(obj, split_size_faces):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()

    # Calculate the bounding box
    (min_x, max_x), (min_y, max_y), (min_z, max_z) = calculate_bounding_box(obj.data)

    # Determine grid size based on the desired number of faces
    num_faces = len(bm.faces)
    num_splits = max(1, num_faces // split_size_faces)
    grid_size = int(num_splits ** (1/3)) + 1  # Ensure we have enough splits

    # Calculate grid cell dimensions
    cell_width = (max_x - min_x) / grid_size if max_x != min_x else 1.0
    cell_height = (max_y - min_y) / grid_size if max_y != min_y else 1.0
    cell_depth = (max_z - min_z) / grid_size if max_z != min_z else 1.0

    # Create face batches
    face_batches = []
    cell_faces = {}

    for face in bm.faces:
        # Determine the grid cell for the face
        centroid = face.calc_center_median()
        cell_x = int((centroid.x - min_x) / cell_width)
        cell_y = int((centroid.y - min_y) / cell_height)
        cell_z = int((centroid.z - min_z) / cell_depth)
        cell_key = (cell_x, cell_y, cell_z)

        if cell_key not in cell_faces:
            cell_faces[cell_key] = []
        cell_faces[cell_key].append(face.index)

        # Split batches if they exceed the split size
        if len(cell_faces[cell_key]) >= split_size_faces:
            face_batches.append(cell_faces[cell_key])
            cell_faces[cell_key] = []

    # Add remaining faces
    for faces in cell_faces.values():
        if faces:
            face_batches.append(faces)

    bm.free()
    return face_batches

def export_split_world(filepath, scene, split_size_faces):
    world = rvstruct.World()
    created_objects = []
    split_meshes_list = []
    scene = bpy.context.scene

    for obj in scene.objects:
        if obj.type == 'MESH' and not obj.hide_render and '_split_' not in obj.name:
            face_batches = simple_split_mesh_by_grid(obj, split_size_faces)
            for batch in face_batches:
                new_obj = create_split_mesh(obj.data, batch, f"{obj.name}_split", created_objects)
                if new_obj:
                    split_meshes_list.append(new_obj)

    if not split_meshes_list:
        print("No valid meshes to export.")
        return

    for split_obj in split_meshes_list:
        if split_obj and split_obj.data:
            converted_mesh = export_mesh(split_obj.data, split_obj, scene, filepath, world=world)
            if converted_mesh:
                world.meshes.append(converted_mesh)

    world.mesh_count = len(world.meshes)
    world.generate_bigcubes()
    
    # Exports the texture animation
    animations = eval(scene.texture_animations)
    for animdict in animations:
        anim = rvstruct.TexAnimation()
        anim.from_dict(animdict)
        world.animations.append(anim)
    world.animation_count = scene.ta_max_slots

    with open(filepath, "wb") as file:
        world.write(file)

    for obj in created_objects:
        bpy.data.objects.remove(obj, do_unlink=True)

def export_standard_world(filepath, scene):
    scene = bpy.context.scene
    world = rvstruct.World()
    meshes = [export_mesh(obj.data, obj, scene, filepath, world=world) for obj in scene.objects if obj_conditions(obj)]
    world.meshes.extend(meshes)
    world.mesh_count = len(world.meshes)
    world.generate_bigcubes()
    
    # Exports the texture animation
    animations = eval(scene.texture_animations)
    for animdict in animations:
        anim = rvstruct.TexAnimation()
        anim.from_dict(animdict)
        world.animations.append(anim)
    world.animation_count = scene.ta_max_slots

    with open(filepath, "wb") as file:
        world.write(file)

def obj_conditions(obj):
    return obj.type == "MESH" and obj.data and not any(obj.get(attr) for attr in ["is_instance", "is_cube", "is_bcube", "is_bbox", "is_mirror_plane", "is_hull_sphere", "is_hull_convex", "is_track_zone"])

def export_file(filepath, scene):
    split_size_faces = getattr(scene, 'split_size_faces', 100) * 2
    
    # Ensure we're in object mode before any operations
    bpy.ops.object.mode_set(mode='OBJECT')

    # Get all mesh objects in the scene
    mesh_objects = [obj for obj in scene.objects if obj.type == 'MESH']

    # Run batch material assignment for both COL and UV_TEX
    fast_batch_assign_materials(mesh_objects, 'COL')
    fast_batch_assign_materials(mesh_objects, 'UV_TEX')

    # Proceed with export if everything is okay
    if getattr(scene, 'export_worldcut', False):
        export_split_world(filepath, scene, split_size_faces)
    else:
        export_standard_world(filepath, scene)

    # Debug print to confirm export completion
    print(f"Export completed to {filepath}")
    
def fast_batch_assign_materials(mesh_objects, material_choice):
    """
    Optimized batch processing of material assignment.
    Processes all selected objects in a single batch operation.
    """
    if not mesh_objects:
        print("No mesh objects selected for material assignment.")
        return

    # Set all objects to the desired material choice
    for obj in mesh_objects:
        obj.data.material_choice = material_choice

    # Switch to edit mode for all objects at once
    bpy.ops.object.select_all(action='DESELECT')
    for obj in mesh_objects:
        obj.select_set(True)
    
    # Switch to edit mode for all selected objects
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')

    # Apply material assignment for all selected objects
    bpy.ops.object.assign_materials_auto()

    # Switch back to object mode after processing
    bpy.ops.object.mode_set(mode='OBJECT')

    print(f"Assigned materials ({material_choice}) to all mesh objects.")

def set_material_to_col(mesh_objects):
    """Legacy function for backward compatibility (Uses batch processing now)."""
    fast_batch_assign_materials(mesh_objects, 'COL')

def set_material_to_texture(mesh_objects):
    """Legacy function for backward compatibility (Uses batch processing now)."""
    fast_batch_assign_materials(mesh_objects, 'UV_TEX')