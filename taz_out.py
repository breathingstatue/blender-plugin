"""
Name:    taz_out
Purpose: Exports Re-Volt level track zone files (.taz)

Description:
Zone files contain numbered boxes to identify tracks space.

"""

import os
import bpy
import math
import mathutils
from . import common
from . import rvstruct
from .common import to_revolt_coord, to_revolt_axis, to_revolt_scale, to_trans_matrix
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
        
        # Get the ID from the custom property
        zid = obj.get("track_zone_id")
        if zid is None:
            print(f"Skipping object {obj.name}: No 'track_zone_id' custom property found")
            continue
        
        # Convert object transforms to Re-Volt format
        location, rotation_matrix, scale = transforms_to_revolt(obj.location, obj.rotation_euler, obj.scale)
        # Append the zone to the TrackZones object
        zones.append(zid, location, rotation_matrix, scale)
    
    # Export all zones to the TAZ file
    with open(filepath, "wb") as file:
        zones.write(file)

def transforms_to_revolt(location, rotation_euler=(0,0,0), scale=(1,1,1)):
    """
    Converts Blender's transformation parameters to Re-Volt format, accounting for specific discrepancies.
    """
    # Convert location from Blender coordinates to Re-Volt coordinates
    location_revolt = to_revolt_coord(location)
    
    # Convert scale to Re-Volt format
    scale_revolt = to_revolt_scale(scale)
    
    # Since Re-Volt expects the scale to be halved, adjust accordingly
    scale_revolt = [val / 2 for val in scale_revolt]
    
    # Convert rotation from Blender Euler angles to Re-Volt format
    # Apply the XZY order and correct the 90-degree offset on the X-axis
    rotation_euler_revolt = (rotation_euler[0] - math.radians(90), -rotation_euler[2], rotation_euler[1])
    
    # Create a rotation matrix from Re-Volt's Euler angles (XZY order)
    rotation_matrix = mathutils.Euler(rotation_euler_revolt, 'XZY').to_matrix()
    
    # Convert the rotation matrix to a 4x4 matrix
    rotation_matrix_4x4 = rotation_matrix.to_4x4()
    
    # Convert rotation matrix to a 3x3 matrix for Re-Volt
    rotation_matrix_correct_format = [list(row)[:3] for row in rotation_matrix_4x4]
    
    return location_revolt, rotation_matrix_correct_format, scale_revolt