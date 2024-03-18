"""
Name:    taz_in
Purpose: Imports Re-Volt level track zone files (.taz)

Description:
Zone files contain numbered boxes to identify tracks space.

""" 

import bpy
import bmesh
import os
from mathutils import Matrix as BlenderMatrix
from .common import to_blender_coord, to_blender_axis, SCALE
from .rvstruct import TrackZones, Zone, Vector

# Add specific imports from common as needed
# Example: from .common import specific_function, SpecificClass

def import_file(filepath, scene):
    """
    Imports a .taz file and links it to the scene as a Blender object.
    """
    with open(filepath, 'rb') as file:
        tzones = TrackZones(file)

    for zone in tzones.zones:
        pos = to_blender_coord(zone.pos)
        size = zone.size.scale(SCALE)

        # Extract the 3x3 matrix data
        rv_matrix_data = zone.matrix.data  # This is a list of tuples

        # Convert the 3x3 matrix to a 4x4 matrix for Blender
        blender_matrix_data = [list(row) + [0] for row in rv_matrix_data]  # Convert each tuple to list and append 0
        blender_matrix_data.append([0, 0, 0, 1])  # Add the 4th row for 4x4 matrix

        matrix_blender = BlenderMatrix(blender_matrix_data)
        matrix_blender.transpose()

        rot = matrix_blender.to_euler("XZY")
        rot = to_blender_axis(rot)

        create_zone(zone.id, pos, (size[0], size[2], size[1]), rot)
        

def create_zone(zid=None, location=(0, 0, 0), size=(1, 1, 1), rotation=(0, 0, 0)):
    if 'TRACK_ZONES' not in bpy.data.collections:
        new_col = bpy.data.collections.new('TRACK_ZONES')
        bpy.context.scene.collection.children.link(new_col)

    track_zones_collection = bpy.data.collections['TRACK_ZONES']

    mesh = bpy.data.meshes.new(name=f"Z{zid}_Mesh")
    ob = bpy.data.objects.new(f"Z{zid if zid is not None else len(track_zones_collection.objects)}", mesh)
    track_zones_collection.objects.link(ob)

    # Set the vertices and edges, explicitly using data keyword
    verts = [
        Vector(data=(-1, -1, -1)), Vector(data=(-1, -1, 1)),
        Vector(data=(-1, 1, -1)), Vector(data=(-1, 1, 1)),
        Vector(data=(1, -1, -1)), Vector(data=(1, -1, 1)),
        Vector(data=(1, 1, -1)), Vector(data=(1, 1, 1))
    ]
    edges = [(0, 1), (1, 3), (3, 2), (2, 0), (4, 5), (5, 7), (7, 6), (6, 4), (0, 4), (1, 5), (3, 7), (2, 6)]

    # Adjust vertex positions based on size
    adjusted_verts = []
    for v in verts:
        adjusted_verts.append((size[0] * v.data[0] / 2, size[2] * v.data[1] / 2, size[1] * v.data[2] / 2))

    mesh.from_pydata(adjusted_verts, edges, [])
    mesh.update()

    ob.location = location
    ob.rotation_euler = rotation
    ob.display_type = 'WIRE'
    ob.show_in_front = True
    ob.show_name = True
    ob["is_track_zone"] = True

    return ob
