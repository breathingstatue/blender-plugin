"""
Name:    fob_in
Purpose: Imports Re-Volt level object files (.fob)

Description:
FOB files contain object entries with position, rotation, and varying extra data fields.
"""

import bmesh
import bpy
from math import radians
from mathutils import Matrix, Vector
from .common import to_blender_axis, to_blender_coord, SCALE, create_directional_fob_mesh_ui, apply_fob_range_scale
from .rvstruct import Objects
from .fob_subtypes import OBJECT_TYPE_NAMES

COLLECTION_NAME = "FOB_OBJECTS"

def ensure_collection(name):
    if name not in bpy.data.collections:
        collection = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(collection)
    return bpy.data.collections[name]

def _safe_fob_type_name(obj_id):
    name = OBJECT_TYPE_NAMES.get(int(obj_id), f"Unknown_{int(obj_id)}")
    return "_".join(name.replace("/", "_").split())


def format_fob_object_name(creation_index, obj_id):
    return f"FOB_{int(creation_index):03d}_{int(obj_id):03d}_{_safe_fob_type_name(obj_id)}"


def get_unique_name(base_name, existing):
    if base_name not in existing:
        return base_name
    index = 1
    while f"{base_name}_{index}" in existing:
        index += 1
    return f"{base_name}_{index}"

def import_file(filepath, scene):
    with open(filepath, 'rb') as file:
        objects_data = Objects()
        objects_data.read(file)

    collection = ensure_collection(COLLECTION_NAME)
    existing_names = {obj.name for obj in bpy.data.objects}

    for creation_index, obj in enumerate(reversed(objects_data.objects)):
        name = get_unique_name(format_fob_object_name(creation_index, obj.obj_id), existing_names)
        pos = to_blender_coord(obj.position)
        matrix = Matrix.Translation(Vector(pos))

        DEFAULT_ROT = (0.0, 0.0, 1.0, 0.0, 0.0, 1.0)

        if obj.rotation:
            forward = Vector(to_blender_axis(obj.rotation[0:3])).normalized()
            up = Vector(to_blender_axis(obj.rotation[3:6])).normalized()

            # Reject colinear or zero-length vectors
            if forward.length < 1e-6 or up.length < 1e-6 or abs(forward.dot(up)) > 0.999:
                rot_matrix = Matrix.Identity(3)
            else:
                right = up.cross(forward).normalized()
                up = forward.cross(right).normalized()
                rot_matrix = Matrix((right, forward, up)).transposed()

            matrix = rot_matrix.to_4x4()
            matrix.translation = Vector(pos)
        else:
            matrix = Matrix.Translation(Vector(pos))

        # Create directional mesh. Local Y is forward/depth and local Z is up.
        fob_obj = create_directional_fob_mesh_ui(name)

        # Set the object's final transform
        fob_obj.matrix_world = matrix

        # Assign custom properties
        fob_obj["is_fob_object"] = True
        fob_obj["fob_type"] = obj.obj_id
        fob_obj["fob_creation_index"] = creation_index
        for j in range(4):
            fob_obj[f"fob_subtype_{j+1}"] = obj.subinfos[j]
        apply_fob_range_scale(fob_obj)

        # Link to collection
        bpy.context.scene.collection.objects.link(fob_obj)
        collection.objects.link(fob_obj)
        bpy.context.scene.collection.objects.unlink(fob_obj)
        existing_names.add(name)
