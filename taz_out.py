"""
Name:    taz_out
Purpose: Exports Re-Volt level track zone files (.taz)

Description:
Zone files contain numbered boxes to identify tracks space.

"""

import bpy
import mathutils
from .common import to_revolt_coord, to_revolt_scale, to_or_matrix
from .rvstruct import TrackZones

def export_file(filepath, scene):
    zones = TrackZones()
    track_zones_collection = bpy.data.collections.get('TRACK_ZONES')

    if track_zones_collection is None:
        print("No 'TRACK_ZONES' collection found.")
        return

    for obj in track_zones_collection.objects:
        if not getattr(obj, "is_track_zone", False) and not obj.get("is_track_zone"):
            continue

        zid = obj.get("track_zone_id")
        if zid is None:
            print(f"Skipping object {obj.name}: No 'track_zone_id' custom property found")
            continue

        # Convert object transforms to Re-Volt format
        location, rotation_matrix, size = transforms_to_revolt(obj.location, obj.rotation_euler, obj.scale)

        zones.append(int(zid), location, rotation_matrix, size)

    # IMPORTANT: TrackZones.write() already writes the count.
    with open(filepath, "wb") as file:
        zones.write(file)

def transforms_to_revolt(location, rotation_euler=(0,0,0), scale=(1,1,1)):
    """Converts Blender object transforms to Re-Volt .taz fields."""
    # Convert location from Blender coordinates to Re-Volt coordinates
    location_revolt = to_revolt_coord(location)

    # Imported .taz zones map Re-Volt size XYZ to Blender scale XZY.
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
