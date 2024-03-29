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
        
        # Get a name of object and zone id from it
        zid = int(obj.name.split(".", 1)[0][1:])
        zones.append(zid, *transforms_to_revolt(obj.location, obj.rotation_euler, obj.scale))
    
    # Exports all zones to the TAZ file
    with open(filepath, "wb") as file:
        zones.write(file)

def transforms_to_revolt(location, rotation_euler = (0,0,0), scale = (1,1,1)):
    """
    This function takes blender's order transformation parameters values and converts
    them into values ready to export
    """
    location = to_revolt_coord(location)
    rotation_euler = to_revolt_axis(rotation_euler)
    rotation_matrix = mathutils.Euler(rotation_euler, 'XZY').to_matrix()
    rotation_matrix.transpose()

    # Ensuring the rotation matrix is in the correct format
    rotation_matrix_correct_format = [list(row)[:3] for row in rotation_matrix]

    scale = to_revolt_coord(scale)
    scale = [abs(val) for val in scale]
    
    return location, rotation_matrix_correct_format, scale
