"""
Name:    rim_out
Purpose: Exports Re-Volt mirror plane files (.rim)

Description:
Mirror planes are used to determine reflective surfaces.
"""

import bpy
import bmesh
import importlib
from mathutils import Vector

from . import common
from . import rvstruct
from .common import apply_trs, to_revolt_axis, to_revolt_coord, rvbbox_from_verts

# --- Proper modern reload ---
if "common" in locals():
    importlib.reload(common)
    importlib.reload(rvstruct)


def _is_mirror_obj(obj: bpy.types.Object) -> bool:
    # Works whether you use a registered BoolProperty or only custom props
    if obj is None:
        return False
    if getattr(obj, "is_mirror_plane", False):
        return True
    return bool(obj.get("is_mirror_plane", False))


def _face_center(face: bmesh.types.BMFace) -> Vector:
    c = Vector((0.0, 0.0, 0.0))
    n = 0
    for loop in face.loops:
        c += loop.vert.co
        n += 1
    return c / max(n, 1)

def _loops_list(face):
    return [l for l in face.loops]

def _reverse_loops(loops):
    loops = list(loops)
    loops.reverse()
    return loops

def _face_center_from_loops(loops):
    c = Vector((0.0, 0.0, 0.0))
    for l in loops:
        c += l.vert.co
    return c / max(len(loops), 1)


def export_file(filepath: str, scene: bpy.types.Scene):
    objs = [obj for obj in scene.objects if _is_mirror_obj(obj)]

    rim = rvstruct.RIM()

    for obj in objs:
        if obj.type != "MESH" or obj.data is None:
            continue

        bm = bmesh.new()
        bm.from_mesh(obj.data)

        # Apply translation/rotation/scale into the bmesh.
        # IMPORTANT: this destroys obj's local axes in the bmesh space,
        # so we capture the object's +Z direction in world space BEFORE applying.
        obj_up_world = (obj.matrix_world.to_3x3() @ Vector((0.0, 0.0, 1.0))).normalized()

        apply_trs(obj, bm, transform=True)

        # Ensure normals match the transformed geometry
        bm.normal_update()
        bm.faces.ensure_lookup_table()

        for face in bm.faces:
            if len(face.verts) < 3:
                continue

            mirror_plane = rvstruct.MirrorPlane()

            # Enforce: mirroring side = side whose normal faces the object's +Z axis (in world space)
            loops = list(face.loops)
            if not loops:
                continue

            face_n = face.normal.normalized()

            # If this face points opposite to object +Z, flip the winding and normal
            if face_n.dot(obj_up_world) < 0.0:
                loops.reverse()
                face_n = -face_n

            # Export normal using the enforced direction
            normal = rvstruct.Vector(data=to_revolt_axis(face_n))
            normal.normalize()

            # Use face center for stable distance (especially far mirrors)
            center = sum((l.vert.co for l in loops), Vector()) / len(loops)
            center_rv = rvstruct.Vector(data=to_revolt_coord(center))

            # Plane equation: n·x = distance
            distance = normal.dot(center_rv)

            mirror_plane.plane.normal = normal
            mirror_plane.plane.distance = distance

            # Bounding box from loop verts (stable)
            loop_verts = [l.vert for l in loops]
            mirror_plane.bounding_box = rvstruct.BoundingBox(
                data=rvbbox_from_verts(loop_verts)
            )

            # Export vertices in loop order (stable winding)
            mirror_plane.vertices = [
                rvstruct.Vector(data=to_revolt_coord(l.vert.co))
                for l in loops
            ]

            rim.mirror_planes.append(mirror_plane)
            rim.num_mirror_planes += 1

        bm.free()

    print("Mirror planes:", rim.num_mirror_planes)

    with open(filepath, "wb") as f:
        rim.write(f)