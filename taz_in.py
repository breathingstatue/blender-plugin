"""
Name:    taz_in
Purpose: Imports Re-Volt level track zone files (.taz)

Description:
Zone files contain numbered boxes to identify tracks space.

""" 

import bpy
import bmesh
import os
from mathutils import Vector, Matrix
from .common import to_blender_coord, to_blender_axis, SCALE
from .rvstruct import TrackZones

# Add specific imports from common as needed
# Example: from .common import specific_function, SpecificClass

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
    """
    Adds a zone representative with vertices and edges at the positions of a cube's corners to the scene.
    """
    if 'TRACK_ZONES' not in bpy.data.collections:
        new_col = bpy.data.collections.new('TRACK_ZONES')
        bpy.context.scene.collection.children.link(new_col)

    track_zones_collection = bpy.data.collections['TRACK_ZONES']

    # Create a new mesh and an object
    mesh = bpy.data.meshes.new(name=f"Z{zid}_Mesh")
    ob = bpy.data.objects.new(f"Z{zid if zid is not None else len(track_zones_collection.objects)}", mesh)

    # Properly link the object to the TRACK_ZONES collection
    track_zones_collection.objects.link(ob)

    # Now set the vertices and edges
    verts = [Vector((-1, -1, -1)), Vector((-1, -1, 1)), Vector((-1, 1, -1)), Vector((-1, 1, 1)),
             Vector((1, -1, -1)), Vector((1, -1, 1)), Vector((1, 1, -1)), Vector((1, 1, 1))]
    edges = [(0, 1), (1, 3), (3, 2), (2, 0), (4, 5), (5, 7), (7, 6), (6, 4), (0, 4), (1, 5), (3, 7), (2, 6)]
    verts = [Vector((size[0] * v[0] / 2, size[1] * v[1] / 2, size[2] * v[2] / 2)) for v in verts]
    mesh.from_pydata(verts, edges, [])

    # Update the mesh
    mesh.update()

    # Set the object's location and rotation
    ob.location = location
    ob.rotation_euler = rotation

    # Set object properties
    ob.display_type = 'WIRE'
    ob.show_in_front = True
    ob.show_name = True
    ob["is_track_zone"] = True

    return ob
