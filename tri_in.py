"""
Name:    tri_in
Purpose: Imports Re-Volt level trigger files (.tri)

Description:
Trigger files contain numbered type and flags to adjust the trigger.

"""

import bpy
import bmesh
import os
from mathutils import Matrix as BlenderMatrix
from . import common
from . import rvstruct
from .rvstruct import Triggers, Vector, Trigger, Matrix
from .common import to_blender_coord, to_blender_axis, to_blender_scale, to_trans_matrix, to_or_matrix, SCALE, TRIGGER_TYPES

# Define SCALE_ADJUSTMENT_FACTOR
SCALE_ADJUSTMENT_FACTOR = 2.0  # Adjust this to scale the triggers by a factor of 2

def to_blender_scale(num):
    return num * SCALE * SCALE_ADJUSTMENT_FACTOR

def get_unique_name(base_name, existing_names):
    """
    Generate a unique name for Blender objects based on base_name.
    If an object with the same name exists, append a numeric suffix starting from '1'.
    """
    if base_name not in existing_names:
        return base_name

    # Start with numeric suffixes
    suffix_index = 1
    while f"{base_name}_{suffix_index}" in existing_names:
        suffix_index += 1
    
    return f"{base_name}_{suffix_index}"

def rename_duplicate_triggers():
    """
    Renames trigger objects with duplicate names by appending numeric suffixes ('1', '2', etc.).
    """
    base_name_map = {}
    
    # Create a map of base names to their occurrences
    for obj in bpy.data.objects:
        if obj.get("is_trigger"):
            base_name = obj.name.split('.')[0]
            if base_name not in base_name_map:
                base_name_map[base_name] = []
            base_name_map[base_name].append(obj.name)
    
    # Rename objects with duplicate base names using numeric suffixes
    for base_name, names in base_name_map.items():
        if len(names) > 1:
            for i, name in enumerate(sorted(names)):
                if i == 0:
                    continue  # Keep the first object without suffix
                new_name = f"{base_name}_{i+1}"  # Numeric suffix starts from 2
                obj = bpy.data.objects[name]
                obj.name = new_name
                if obj.data:
                    mesh = bpy.data.meshes.get(obj.data.name)
                    if mesh:
                        mesh.name = f"{new_name}_Mesh"

def import_file(filepath, scene):
    """
    Imports a .tri file and links it to the scene as a Blender object.
    """
    print(f"Importing file: {filepath}")
    with open(filepath, 'rb') as file:
        filename = os.path.basename(filepath)
        print(f"Opened file: {filename}")
        triggers = Triggers(file)
        print("Triggers object created")
    
    triggers_list = triggers.triggers
    print(f"Number of triggers: {len(triggers_list)}")

    existing_names = {obj.name for obj in bpy.data.objects}

    # Create cubes representing each trigger
    for trigger in triggers_list:
        print(f"Processing trigger: {trigger}")
        # Position and size
        pos = to_blender_coord(trigger.pos) if trigger.pos else (0, 0, 0)
        print(f"Position: {pos}")
        size = (
            to_blender_scale(trigger.size[0]) if trigger.size else 1,
            to_blender_scale(trigger.size[1]) if trigger.size else 1,
            to_blender_scale(trigger.size[2]) if trigger.size else 1
        )
        print(f"Size: {size}")
        # Rotation
        try:
            matrix_data = trigger.matrix.data if trigger.matrix else [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]
            print(f"Matrix data: {matrix_data}")
            or_matrix = to_or_matrix(matrix_data)
            print(f"Orientation Matrix: {or_matrix}")
            trans_matrix = to_trans_matrix(or_matrix)
            print(f"Transformation Matrix: {trans_matrix}")
            blender_matrix = BlenderMatrix(trans_matrix)
            rot = blender_matrix.to_euler('XZY')
            rot = to_blender_axis(rot)
            print(f"Rotation: {rot}")
        except Exception as e:
            print(f"Error processing matrix for trigger: {e}")
            continue
        # Add to scene
        create_trigger(pos, (size[0], size[2], size[1]), rot, existing_names, trigger.trigger_type, trigger.flag_low, trigger.flag_high)
        print(f"Trigger created in Blender")

    # Rename duplicates after all triggers are created
    rename_duplicate_triggers()

def create_trigger(location=(0, 0, 0), size=(1, 1, 1), rotation=(0, 0, 0), existing_names=None, trigger_type=0, flag_low=0, flag_high=0):
    triggers_collection_name = 'TRIGGERS'

    # Ensure the collection exists
    if triggers_collection_name not in bpy.data.collections:
        new_collection = bpy.data.collections.new(triggers_collection_name)
        bpy.context.scene.collection.children.link(new_collection)
    else:
        new_collection = bpy.data.collections[triggers_collection_name]

    if existing_names is None:
        existing_names = {obj.name for obj in bpy.data.objects}

    # Get the name from the TRIGGER_TYPES dictionary
    trigger_name = TRIGGER_TYPES.get(trigger_type, "UnknownType")
    
    # Base name for object and mesh using the trigger name
    base_name = f"TRI_{trigger_name}"

    # Generate unique names for both mesh and object with numeric suffix
    unique_mesh_name = get_unique_name(f"{base_name}_Mesh", existing_names)
    unique_object_name = get_unique_name(base_name, existing_names)

    # Create a new mesh and object
    mesh = bpy.data.meshes.new(name=unique_mesh_name)
    ob = bpy.data.objects.new(name=unique_object_name, object_data=mesh)

    # Link object to the scene and then to the specific collection
    bpy.context.scene.collection.objects.link(ob)
    new_collection.objects.link(ob)
    bpy.context.scene.collection.objects.unlink(ob)

    # Set the object's location, rotation, and scale
    ob.location = location
    ob.scale = size
    ob.rotation_mode = 'XYZ'
    ob.rotation_euler = rotation

    # Additional properties
    ob.display_type = 'WIRE'
    ob.show_in_front = True
    ob["is_trigger"] = True

    # Assign the trigger_type as a custom property and make it editable
    ob["trigger_type"] = trigger_type
    ob["trigger_type_description"] = trigger_name

    # Assign flag_low directly to the object
    ob["flag_low"] = int(flag_low)

    # Handle flag_high only for relevant trigger types
    if trigger_type in {0, 2, 4, 9}:
        ob["flag_high"] = int(flag_high)
    else:
        ob["flag_high"] = 0  # or simply don't set it, depending on how your application handles it

    # Create the mesh data (example cube)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bm.to_mesh(mesh)
    bm.free()

    return ob