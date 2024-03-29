"""
Name:    taz_in
Purpose: Imports Re-Volt level track zone files (.taz)

Description:
Zone files contain numbered boxes to identify tracks space.

""" 
import bpy
import os
from . import common
from . import rvstruct

from .rvstruct import TrackZones
from .common import *

def import_file(filepath, scene):
    """
    Imports a .taz file and links it to the scene as a Blender object.
    """
    with open(filepath, 'rb') as file:
        filename = os.path.basename(filepath)
        tzones = TrackZones(file)
    
    zones = tzones.zones
    
    # Create an cubes representing each zone
    for zone in zones:
        # Position and size
        pos =  to_blender_coord(zone.pos)
        size = zone.size.scale(SCALE)
        # Rotation
        matrix = Matrix(zone.matrix.data)
        matrix.transpose()
        rot = matrix.to_euler("XZY")
        rot = to_blender_axis(rot)
        # Add to scene
        create_zone(zone.id, pos, (size[0],size[2],size[1]), rot)
        

def create_zone(zid=None, location=(0, 0, 0), size=(1, 1, 1), rotation=(0, 0, 0)):
    track_zones_collection_name = 'TRACK_ZONES'

    # Ensure the collection exists
    if track_zones_collection_name not in bpy.data.collections:
        new_collection = bpy.data.collections.new(track_zones_collection_name)
        bpy.context.scene.collection.children.link(new_collection)
    else:
        new_collection = bpy.data.collections[track_zones_collection_name]

    # Create a new mesh and object
    mesh = bpy.data.meshes.new(name=f"Z{zid}_Mesh")
    ob = bpy.data.objects.new(name=f"Z{zid}", object_data=mesh)

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

    # Now you need to create the mesh data. This is an example of creating a simple cube.
    # If you have specific vertices and faces data, you should use them here.
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)  # This size=1.0 is a placeholder; actual size is set by ob.scale
    bm.to_mesh(mesh)
    bm.free()
