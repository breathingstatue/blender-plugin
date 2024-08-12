"""
Name:    tri_out
Purpose: Exports Re-Volt level trigger files (.tri)

Description:
Triggers contain trigger type, flag low and flag high.

"""

import os
import bpy
import math
import mathutils
from . import common
from . import rvstruct
from .common import to_revolt_coord, to_revolt_axis, to_revolt_scale, to_trans_matrix
from .rvstruct import Triggers, Trigger

def export_file(filepath, scene):
    obj = bpy.context.object
    scene = bpy.context.scene
    triggers = Triggers()
    triggers_collection = bpy.data.collections.get('TRIGGERS')

    if triggers_collection is None:
        print("No 'TRIGGERS' collection found.")
        return
    
    for obj in triggers_collection.objects:
        if "is_trigger" not in obj or not obj["is_trigger"]:
            continue
        
        # Retrieve the properties from the object
        trigger_type = obj.get("trigger_type", 0)
        flag_low = obj.get("flag_low", 0)
        flag_high = obj.get("flag_high", 0)
        
        # Convert object transforms to Re-Volt format
        location, rotation_matrix, scale = transforms_to_revolt(obj.location, obj.rotation_euler, obj.scale)
        
        # Append the trigger to the Triggers object
        triggers.append(id=obj.name, pos=location, rotation_matrix=rotation_matrix, size=scale, 
                        trigger_type=trigger_type, flag_low=flag_low, flag_high=flag_high)
    
    # Export all triggers to the TRI file
    with open(filepath, "wb") as file:
        triggers.write(file)

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
