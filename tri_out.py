"""
Name:    tri_out
Purpose: Exports Re-Volt level trigger files (.tri)

Description:
Triggers contain trigger type, flag low and flag high.

"""

import bpy
import mathutils
from .common import to_revolt_coord, to_revolt_scale, to_or_matrix
from .rvstruct import Triggers

def export_file(filepath, scene):
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
    
    # IMPORTANT: Triggers.write() already writes the count.
    with open(filepath, "wb") as file:
        triggers.write(file)

def transforms_to_revolt(location, rotation_euler=(0,0,0), scale=(1,1,1)):
    """Converts Blender object transforms to Re-Volt .tri fields."""
    # Convert location from Blender coordinates to Re-Volt coordinates
    location_revolt = to_revolt_coord(location)

    # Imported .tri triggers map Re-Volt size XYZ to Blender scale XZY.
    scale_revolt = [
        to_revolt_scale(scale[0]) / 2,
        to_revolt_scale(scale[2]) / 2,
        to_revolt_scale(scale[1]) / 2,
    ]

    if hasattr(rotation_euler, "to_matrix"):
        rotation_matrix = rotation_euler.to_matrix()
    else:
        rotation_matrix = mathutils.Euler(rotation_euler, 'XYZ').to_matrix()
    rotation_matrix_revolt = to_or_matrix(rotation_matrix)

    return location_revolt, rotation_matrix_revolt, scale_revolt
