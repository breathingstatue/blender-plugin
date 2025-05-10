"""
Name:    fob_out
Purpose: Exports Re-Volt level object files (.fob)

Description:
FOB objects contain object ID, flags, position, rotation matrix, and optional extra data.
"""

import bpy
import struct
from mathutils import Matrix, Vector
from .common import to_revolt_axis, to_revolt_coord
from .rvstruct import Objects, Object

def export_file(filepath, scene):
    objs = [obj for obj in bpy.context.scene.objects if obj.get("is_fob_object")]
    objs.sort(key=lambda o: int(o.get("fob_creation_index", 0)), reverse=True)

    objects_data = Objects()
    for obj in objs:
        obj_id = int(obj.get("fob_type", 0))
        subinfos = [int(obj.get(f"fob_subtype_{i+1}", 0)) for i in range(4)]
        pos = to_revolt_coord(obj.location)

        matrix = obj.matrix_world.to_3x3().normalized()
        forward = to_revolt_axis((matrix @ Vector((0, 1, 0))).normalized())  # Y
        up      = to_revolt_axis((matrix @ Vector((0, 0, 1))).normalized())  # Z

        rotation_6 = tuple([round(v, 6) for v in (*forward, *up)])
        if rotation_6 == (0.0, 0.0, 1.0, 0.0, 0.0, 1.0):
            rotation_6 = None

        objects_data.objects.append(Object(obj_id, subinfos, pos, rotation_6))

    with open(filepath, 'wb') as file:
        file.write(len(objects_data.objects).to_bytes(4, 'little'))
        for obj in objects_data.objects:
            file.write(obj.write())
