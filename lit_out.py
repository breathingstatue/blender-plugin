"""
Name:    lit_out
Purpose: Exports Re-Volt light files (.lit) from Blender
"""

import bpy
from . import rvstruct
from .common import (
    to_revolt_coord,
    dprint,
    SCALE,
    to_revolt_axis,  # (x, y, z) -> (x, -z, y)
)

SHADOW_REACH_FACTOR = 1.72

_LT_ENCODE = {
    "OMNI": 0,
    "OMNI_NORMAL": 1,
    "SPOT": 2,
    "SPOT_NORMAL": 3,
    "SQUARE_SHADOW": 4,
}

def _encode_light_type(kind: str) -> int:
    return _LT_ENCODE.get(str(kind), 0)

def _encode_world_mode(mode, flicker):
    if mode == "WORLD_ONLY":
        base = 5
    elif mode == "OBJECTS_ONLY":
        base = 6
    else:
        base = 7
    return (base | 0x10) if flicker else base

def from_blender_scale(num: float) -> float:
    return float(num) / float(SCALE)

def _blender_R_to_rv_R3_rows(R_bl_3x3):
    """
    Convert Blender 3x3 rotation to RV 3x3 by applying to_revolt_axis
    to each column (basis vector). Return row-major 3x3 (tuple of rows).
    """
    # Blender columns (basis vectors)
    c0 = (R_bl_3x3[0][0], R_bl_3x3[1][0], R_bl_3x3[2][0])
    c1 = (R_bl_3x3[0][1], R_bl_3x3[1][1], R_bl_3x3[2][1])
    c2 = (R_bl_3x3[0][2], R_bl_3x3[1][2], R_bl_3x3[2][2])

    # Map to RV axes
    r0 = to_revolt_axis(c0)  # column 0 in RV space
    r1 = to_revolt_axis(c1)  # column 1 in RV space
    r2 = to_revolt_axis(c2)  # column 2 in RV space

    # Build RV rows from the mapped columns
    return (
        (float(r0[0]), float(r1[0]), float(r2[0])),
        (float(r0[1]), float(r1[1]), float(r2[1])),
        (float(r0[2]), float(r1[2]), float(r2[2])),
    )


def export_file(filepath, scene):
    lights = rvstruct.Lights()
    light_objs = [o for o in scene.objects if getattr(o, "is_light", False) or o.get("is_light")]

    for obj in light_objs:
        light = rvstruct.Light()

        # Position
        light.position = rvstruct.Vector(data=to_revolt_coord(obj.location))

        # Rotation-only 3x3 from world rotation (scale-independent)
        R_bl = obj.matrix_world.to_quaternion().to_matrix()
        light.matrix = rvstruct.Matrix()
        light.matrix.data = _blender_R_to_rv_R3_rows(R_bl)

        # Cone (degrees; writer stores raw = deg*2)
        cone = int(getattr(obj, "light_cone", obj.get("light_cone", 90)))
        light.cone_angle = max(1, min(180, cone))

        # Fixed fields
        light.pad0 = 0
        light.type_const = 0x42

        # World/flicker
        world_mode = getattr(obj, "light_world_mode", obj.get("light_world_mode", "WORLD_OBJECTS"))
        flicker = bool(getattr(obj, "light_flicker", obj.get("light_flicker", False)))
        light.flicker_mode = _encode_world_mode(world_mode, flicker)

        # Type (use stored human-readable string)
        kind = getattr(obj, "light_type", obj.get("light_type", "OMNI"))
        light.light_type = _encode_light_type(kind)

        # Payload and reach
        if kind == "SQUARE_SHADOW":
            size_prop = getattr(obj, "light_size", obj.get("light_size", None))
            if size_prop:
                sx, sy, sz = map(float, size_prop)  # RV order
            else:
                s = obj.scale
                sx = from_blender_scale(float(s.x))  # Blender X -> RV X
                sy = from_blender_scale(float(s.z))  # Blender Z -> RV Y
                sz = from_blender_scale(float(s.y))  # Blender Y -> RV Z
            light.size = (sx, sy, sz)
            light.rgb = (1.0, 1.0, 1.0)  # unused for squares
            light.reach = float(max(sx, sy, sz) * SHADOW_REACH_FACTOR)
        else:
            rgb = getattr(obj, "light_rgb", obj.get("light_rgb", (255, 255, 255)))
            light.rgb = (
                max(0.0, min(1.0, float(rgb[0]) / 255.0)),
                max(0.0, min(1.0, float(rgb[1]) / 255.0)),
                max(0.0, min(1.0, float(rgb[2]) / 255.0)),
            )
            reach = getattr(obj, "light_reach", obj.get("light_reach", 0.0))
            light.reach = float(reach)

        # Flicker speed (0–255; low byte used)
        spd = int(getattr(obj, "light_flicker_speed", obj.get("light_flicker_speed", 1)))
        light.flicker_speed = max(0, min(255, spd))

        lights.lights.append(light)

    lights.light_count = len(lights.lights)
    dprint(f"[LIT] Exporting {lights.light_count} lights to {filepath}")
    with open(filepath, "wb") as fd:
        lights.write(fd)
    return True
