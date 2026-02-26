"""
Name:    lit_in
Purpose: Imports Re-Volt light files (.lit) into Blender
"""

import bpy
import bmesh
from mathutils import Matrix as BlenderMatrix
from . import rvstruct
from .common import (
    to_blender_coord,
    to_trans_matrix,      # expects 3x3 rows: m[r][c]
    to_blender_scale,
    to_blender_axis,      # (x, y, z) -> (x, z, -y)
    dprint,
)

_S = BlenderMatrix(((1.0, 0.0,  0.0),
                    (0.0, 0.0, -1.0),
                    (0.0, 1.0,  0.0)))
_ST = _S.transposed()

COLLECTION_NAME = "LIGHTS"
SHADOW_REACH_FACTOR = 1.72


def ensure_collection(name):
    if name not in bpy.data.collections:
        collection = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(collection)
    return bpy.data.collections[name]


def _create_wire_cube(name="Light_Cube"):
    mesh = bpy.data.meshes.new(name + "_Mesh")
    obj = bpy.data.objects.new(name, mesh)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.delete(bm, geom=bm.faces[:], context='FACES_ONLY')
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    obj.display_type = 'WIRE'
    obj.show_in_front = True
    return obj


def _create_wire_cone(name="Light_Cone"):
    mesh = bpy.data.meshes.new(name + "_Mesh")
    obj = bpy.data.objects.new(name, mesh)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, segments=16, radius1=0.5, radius2=0.0, depth=1.5)
    bmesh.ops.delete(bm, geom=bm.faces[:], context='FACES_ONLY')
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    obj.display_type = 'WIRE'
    obj.show_in_front = True
    return obj


def _create_empty(name="Light_Empty"):
    obj = bpy.data.objects.new(name, None)
    obj.empty_display_type = 'SPHERE'
    obj.empty_display_size = 0.2
    return obj


def _decode_world_mode(flicker_mode):
    base = flicker_mode & 0x0F
    if base == 5:
        return "WORLD_ONLY"
    if base == 6:
        return "OBJECTS_ONLY"
    return "WORLD_OBJECTS"


def _decode_flicker(flicker_mode):
    return bool(flicker_mode & 0x10)


_LT_DECODE = {
    0: "OMNI",
    1: "OMNI_NORMAL",
    2: "SPOT",
    3: "SPOT_NORMAL",
    4: "SQUARE_SHADOW",
}
def _decode_light_type(light_type_byte):
    return _LT_DECODE.get(int(light_type_byte), "OMNI")


def _as_rv_rows(m):
    if isinstance(m, (list, tuple)):
        if len(m) == 3 and isinstance(m[0], (list, tuple)):
            r0, r1, r2 = m
            return (
                (float(r0[0]), float(r0[1]), float(r0[2])),
                (float(r1[0]), float(r1[1]), float(r1[2])),
                (float(r2[0]), float(r2[1]), float(r2[2])),
            )
        if len(m) == 9:
            return (
                (float(m[0]), float(m[1]), float(m[2])),
                (float(m[3]), float(m[4]), float(m[5])),
                (float(m[6]), float(m[7]), float(m[8])),
            )
    raise TypeError("Unsupported RV matrix layout; expected 3x3 rows or flat 9 floats")

def _rv_rows_to_blender_R3(rv_rows):
    # Take RV basis columns
    c0 = (rv_rows[0][0], rv_rows[1][0], rv_rows[2][0])
    c1 = (rv_rows[0][1], rv_rows[1][1], rv_rows[2][1])
    c2 = (rv_rows[0][2], rv_rows[1][2], rv_rows[2][2])
    # Map each to Blender axes
    b0 = to_blender_axis(c0)
    b1 = to_blender_axis(c1)
    b2 = to_blender_axis(c2)
    # Reassemble as Blender rows
    return (
        (float(b0[0]), float(b1[0]), float(b2[0])),
        (float(b0[1]), float(b1[1]), float(b2[1])),
        (float(b0[2]), float(b1[2]), float(b2[2])),
    )


def import_file(filepath, scene):
    with open(filepath, "rb") as file:
        lights = rvstruct.Lights(file)

    collection = ensure_collection(COLLECTION_NAME)
    dprint(f"[LIT] Importing {len(lights.lights)} lights from {filepath}")

    for index, light in enumerate(lights.lights):
        name = f"Light_{index}"

        decoded_kind = _decode_light_type(light.light_type)
        dprint(
            f"[LIT] Light #{index}: raw_type=0x{light.light_type:02X} decoded={decoded_kind} "
            f"flicker_mode=0x{light.flicker_mode:02X} flicker_speed={light.flicker_speed} "
            f"cone={light.cone_angle} reach={light.reach}"
        )

        # Create Blender object by stored type (no heuristics)
        if decoded_kind == "SQUARE_SHADOW":
            obj = _create_wire_cube(name)
        elif decoded_kind in {"SPOT", "SPOT_NORMAL"}:
            obj = _create_wire_cone(name)
        else:
            obj = _create_empty(name)

        # Basic props
        obj["is_light"] = True
        obj.is_light = True
        obj.light_type = decoded_kind
        obj["light_type"] = decoded_kind
        obj.light_world_mode = _decode_world_mode(light.flicker_mode)
        obj.light_flicker = _decode_flicker(light.flicker_mode)
        obj.light_flicker_speed = max(0, min(255, int(light.flicker_speed)))
        obj.light_cone = max(1, min(180, int(round(light.cone_angle))))
        obj.light_reach = float(light.reach)

        # Payload visualization
        if decoded_kind == "SQUARE_SHADOW":
            sx, sy, sz = map(float, light.size)
            obj.light_size = (sx, sy, sz)  # keep RV order (used by export)

            # Normalize preview scale so half-extents match exactly
            # Measure the base cube's local half-extents along its axes
            try:
                hx = max(abs(v.co.x) for v in obj.data.vertices) or 1.0
                hy = max(abs(v.co.y) for v in obj.data.vertices) or 1.0
                hz = max(abs(v.co.z) for v in obj.data.vertices) or 1.0
            except Exception:
                hx = hy = hz = 1.0  # safe fallback

            # Correct axis order is X=sx, Y=sy, Z=sz
            obj.scale = (
                to_blender_scale(sx) / hx,
                to_blender_scale(sy) / hy,
                to_blender_scale(sz) / hz,
            )

            obj.light_rgb = [255, 255, 255]
        else:
            obj.light_size = (0.0, 0.0, 0.0)
            obj.light_rgb = [
                max(0, min(255, int(round(light.rgb[0] * 255.0)))),
                max(0, min(255, int(round(light.rgb[1] * 255.0)))),
                max(0, min(255, int(round(light.rgb[2] * 255.0)))),
            ]

        # Rotation (exact inverse of export)
        rv_rows = _as_rv_rows(light.matrix.data)
        M_rv = BlenderMatrix(rv_rows)
        R_bl = _ST @ M_rv
        obj.rotation_mode = 'QUATERNION'
        obj.rotation_quaternion = R_bl.to_quaternion()

        # Translation
        obj.location = to_blender_coord(light.position.data)

        # Link
        scene.collection.objects.link(obj)
        if collection and obj.name not in collection.objects:
            collection.objects.link(obj)
            try:
                scene.collection.objects.unlink(obj)
            except Exception:
                pass

        dprint(f"[LIT] Imported light {name} -> {obj.light_type}")

    return True
