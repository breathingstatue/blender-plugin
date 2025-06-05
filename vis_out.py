"""
Name:    vis_out
Purpose: Exports Re-Volt level Visiboxes (.vis)

Description:
Visibox file contains IDs of either Camera or Cubes (Visiboxes).
"""

import struct
from mathutils import Vector
from .common import to_revolt_coord


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

            # Compute axis-aligned min and max directly
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

            # Convert to Re-Volt coordinate system (x, z, -y)
            min_rv = to_revolt_coord(min_corner)
            max_rv = to_revolt_coord(max_corner)

            coords = [
                min_rv[0], max_rv[0],  # x
                min_rv[1], max_rv[1],  # y
                min_rv[2], max_rv[2],  # z
            ]

            # Write data
            f.write(struct.pack("<BBH", typ, id_, 0))
            f.write(struct.pack("<6f", *coords))
