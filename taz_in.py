import bpy
import bmesh
import os
from mathutils import Matrix as BlenderMatrix
from . import common
from . import rvstruct
from .rvstruct import TrackZones, Vector, Zone, Matrix
from .common import to_blender_coord, to_blender_axis, to_blender_scale, to_trans_matrix, to_or_matrix, SCALE

# Define SCALE_ADJUSTMENT_FACTOR
SCALE_ADJUSTMENT_FACTOR = 2.0  # Adjust this to scale the track zones by a factor of 2

def to_blender_scale(num):
    return num * SCALE * SCALE_ADJUSTMENT_FACTOR

def get_unique_name(base_name, existing_names):
    """
    Generate a unique name for Blender objects based on base_name.
    If an object with the same name exists, append a suffix starting from 'a'.
    """
    if base_name not in existing_names:
        return base_name

    # Use suffixes starting from 'a'
    suffix_index = ord('a')
    while f"{base_name}{chr(suffix_index)}" in existing_names:
        suffix_index += 1
        if suffix_index > ord('z'):
            # Extend to handle more suffixes if necessary
            raise ValueError("Too many objects with the same base name.")
    
    return f"{base_name}{chr(suffix_index)}"

def rename_duplicate_zones():
    """
    Renames track zone objects with duplicate IDs by appending 'a', 'b', etc.
    """
    id_name_map = {}
    
    # Create a map of track zone IDs to their names
    for obj in bpy.data.objects:
        if obj.get("is_track_zone"):
            track_zone_id = obj.get("track_zone_id")
            if track_zone_id is not None:
                if track_zone_id not in id_name_map:
                    id_name_map[track_zone_id] = []
                id_name_map[track_zone_id].append(obj.name)
    
    # Rename objects with duplicate IDs
    for track_zone_id, names in id_name_map.items():
        if len(names) > 1:
            for i, name in enumerate(names):
                new_name = f"TZ{track_zone_id}{chr(ord('a') + i)}"
                # Rename the object
                obj = bpy.data.objects[name]
                obj.name = new_name
                # Rename the associated mesh
                if obj.data:
                    mesh = bpy.data.meshes[obj.data.name]
                    mesh.name = f"{new_name}_Mesh"

def import_file(filepath, scene):
    """
    Imports a .taz file and links it to the scene as a Blender object.
    """
    print(f"Importing file: {filepath}")
    with open(filepath, 'rb') as file:
        filename = os.path.basename(filepath)
        print(f"Opened file: {filename}")
        tzones = TrackZones(file)
        print("TrackZones object created")
    
    zones = tzones.zones
    print(f"Number of zones: {len(zones)}")

    existing_names = {obj.name for obj in bpy.data.objects}

    # Create cubes representing each zone
    for zone in zones:
        print(f"Processing zone: {zone.id}")
        # Position and size
        pos = to_blender_coord(zone.pos)
        print(f"Position: {pos}")
        size = (to_blender_scale(zone.size[0]), to_blender_scale(zone.size[1]), to_blender_scale(zone.size[2]))
        print(f"Size: {size}")
        # Rotation
        try:
            matrix_data = zone.matrix.data
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
            print(f"Error processing matrix for zone {zone.id}: {e}")
            continue
        # Add to scene
        create_zone(zone.id, pos, (size[0], size[2], size[1]), rot, existing_names)
        print(f"Zone {zone.id} created in Blender")

    # Rename duplicates after all zones are created
    rename_duplicate_zones()


def create_zone(zid=None, location=(0, 0, 0), size=(1, 1, 1), rotation=(0, 0, 0), existing_names=None):
    track_zones_collection_name = 'TRACK_ZONES'

    # Ensure the collection exists
    if track_zones_collection_name not in bpy.data.collections:
        new_collection = bpy.data.collections.new(track_zones_collection_name)
        bpy.context.scene.collection.children.link(new_collection)
    else:
        new_collection = bpy.data.collections[track_zones_collection_name]

    if existing_names is None:
        existing_names = {obj.name for obj in bpy.data.objects}

    # Base name for object and mesh
    base_name = f"TZ{zid}" if zid is not None else "TZ"

    # Generate unique names for both mesh and object
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
    ob["is_track_zone"] = True
    ob["track_zone_id"] = zid if zid is not None else 0

    # Create the mesh data. This is an example of creating a simple cube.
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bm.to_mesh(mesh)
    bm.free()

    return ob
