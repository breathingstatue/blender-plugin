"""
Name:    taz_out
Purpose: Exports Re-Volt level track zone files (.taz)

Description:
Zone files contain numbered boxes to identify tracks space.

"""


import os
import bpy
import mathutils
from . import common
from . import rvstruct
from .common import to_revolt_coord, to_revolt_axis
from .rvstruct import TrackZones


def export_file(filepath, scene):
    zones = TrackZones()
    track_zones_collection = bpy.data.collections.get('TRACK_ZONES')

    if track_zones_collection is None:
        print("No 'TRACK_ZONES' collection found.")
        return
    
    for obj in track_zones_collection.objects:
        if "is_track_zone" not in obj or not obj["is_track_zone"]:
            continue
        
        zid = int(obj.name.split(".", 1)[0][1:])
        location, rotation_matrix_data, size = transforms_to_revolt(
            obj.location, obj.rotation_euler, obj.scale, obj.dimensions)
        
        zones.append(zid, location, rotation_matrix_data, size)
    
    with open(filepath, "wb") as file:
        zones.write(file)

def transforms_to_revolt(location, rotation_euler=(0, 0, 0), scale=(1, 1, 1), dimensions=(1, 1, 1)):
    """
    This function takes blender's order transformation parameters values and converts
    them into values ready to export
    """
    location = to_revolt_coord(location)
    rotation_euler = to_revolt_axis(rotation_euler)
    scale = to_revolt_coord(scale)

    # Correctly apply the scale to the object's dimensions
    # The size for each dimension is calculated by multiplying the dimension by its corresponding scale factor.
    size = [dimensions[i] * abs(scale[i]) for i in range(3)]

    rotation_matrix = mathutils.Euler(rotation_euler, 'XZY').to_matrix()
    rotation_matrix_3x3 = [list(row)[:3] for row in rotation_matrix][:3]

    return location, rotation_matrix_3x3, size
