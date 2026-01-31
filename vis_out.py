"""
Name:    vis_out
Purpose: Exports Re-Volt level Visiboxes (.vis)

Description:
Visibox file contains IDs of either Camera or Cubes (Visiboxes).
"""

import struct
from mathutils import Vector
from .common import SCALE  # <-- add this


def export_file(filepath, scene):
    visiboxes = [
        obj for obj in scene.objects
        if obj.get("is_visibox", False)
    ]

    with open(filepath, "wb") as f:
        f.write(struct.pack("<I", len(visiboxes)))

        for obj in visiboxes:
            typ = int(obj.get("visibox_type", "1"))
            id_ = int(obj.get("visibox_id", 0))

            if not obj.data or not hasattr(obj.data, "vertices"):
                continue  # skip if not a mesh

            # Get bounding box corners in local space
            bbox_local = [Vector(corner) for corner in obj.bound_box]

            # Transform corners to world space
            bbox_world = [obj.matrix_world @ corner for corner in bbox_local]

            # Blender world AABB
            min_corner = Vector((
                min(v.x for v in bbox_world),
                min(v.y for v in bbox_world),
                min(v.z for v in bbox_world),
            ))
            max_corner = Vector((
                max(v.x for v in bbox_world),
                max(v.y for v in bbox_world),
                max(v.z for v in bbox_world),
            ))

            # Convert Blender world AABB -> Re-Volt bbox pairs
            # RV: x = Blender x
            # RV: y = -Blender z   (NOTE: negation swaps min/max!)
            # RV: z = Blender y
            xlo = min_corner.x / SCALE
            xhi = max_corner.x / SCALE

            ylo = -max_corner.z / SCALE  # <-- swapped
            yhi = -min_corner.z / SCALE  # <-- swapped

            zlo = min_corner.y / SCALE
            zhi = max_corner.y / SCALE

            coords = [xlo, xhi, ylo, yhi, zlo, zhi]

            # Write data
            f.write(struct.pack("<BBH", typ, id_, 0x5667))
            f.write(struct.pack("<6f", *coords))
