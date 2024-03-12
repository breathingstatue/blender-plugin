"""
Name:    taz_out
Purpose: Exports Re-Volt level track zone files (.taz)

Description:
Zone files contain numbered boxes to identify tracks space.

"""

import os
import bmesh
import bpy
import mathutils
from .common import to_revolt_coord, to_revolt_axis

from .rvstruct import TrackZones

# Add specific imports from common as needed
# Example: from .common import specific_function, SpecificClass

def export_file(filepath, scene):
    # Collect all zones
    zones = TrackZones()
    
    # Access the 'TRACK_ZONES' collection, assuming it exists
    track_zones_collection = bpy.data.collections.get('TRACK_ZONES')
    
    if track_zones_collection is None:
        print("No 'TRACK_ZONES' collection found.")
        return
    
    # Find all boxes marked as track zones and add them
    for obj in track_zones_collection.objects:
        # Check for the custom property instead of is_track_zone
        if "is_track_zone" not in obj or not obj["is_track_zone"]:
            continue
        
        # Assuming the object's name is structured as expected to extract the ID
        zid = int(obj.name.split(".", 1)[0][1:])
        zones.append(zid, *transforms_to_revolt(obj.location, obj.rotation_euler, obj.scale))
    
    # Exports all zones to the TAZ file
    with open(filepath, "wb") as file:
        zones.write(file)

def transforms_to_revolt(location, rotation_euler = (0,0,0), scale = (1,1,1)):
    """
    This function takes Blender's order transformation parameters values and converts
    them into values ready to export
    """
    location =          to_revolt_coord(location)
    rotation_euler =    to_revolt_axis(rotation_euler)
    rotation_matrix =   mathutils.Euler(rotation_euler, 'XZY').to_matrix()
    rotation_matrix.transpose()

    # Make scale absolute values
    scale = to_revolt_coord(scale)
    scale = [abs(val) for val in scale]
    
    return location, rotation_matrix, scale
