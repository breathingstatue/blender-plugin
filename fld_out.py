"""
Name:    fld_out
Purpose: Exports Re-Volt force field files (.fld)
"""

from mathutils import Vector

from . import rvstruct
from .common import SCALE, dprint, to_revolt_axis, to_revolt_coord


FIELD_TYPE_TO_ID = {
    "LINEAR": 0,
    "ORIENTATION_UP": 1,
    "VELOCITY": 2,
    "SPHERICAL": 3,
    "WIND": 4,
    "ANGULAR": 5,
    "ANGULAR_VELOCITY": 6,
    "ORIENTATION_FWD": 7,
}


def _blender_R_to_rv_R3_rows(R_bl_3x3):
    c0 = (R_bl_3x3[0][0], R_bl_3x3[1][0], R_bl_3x3[2][0])
    c1 = (R_bl_3x3[0][1], R_bl_3x3[1][1], R_bl_3x3[2][1])
    c2 = (R_bl_3x3[0][2], R_bl_3x3[1][2], R_bl_3x3[2][2])

    r0 = to_revolt_axis(c0)
    r1 = to_revolt_axis(c1)
    r2 = to_revolt_axis(c2)

    return (
        (float(r0[0]), float(r1[0]), float(r2[0])),
        (float(r0[1]), float(r1[1]), float(r2[1])),
        (float(r0[2]), float(r1[2]), float(r2[2])),
    )


def _encode_raw_type(obj):
    kind = getattr(obj, "force_field_type", obj.get("force_field_type", "LINEAR"))
    type_id = FIELD_TYPE_TO_ID.get(str(kind), 0)
    old_raw = int(obj.get("force_field_raw_type", 0))
    shape = getattr(obj, "force_field_shape", obj.get("force_field_shape", "BOX"))
    apply = getattr(obj, "force_field_apply", obj.get("force_field_apply", "FORCE"))
    direction = getattr(obj, "force_field_direction_mode", obj.get("force_field_direction_mode", "LINEAR"))
    distribution = getattr(obj, "force_field_distribution", obj.get("force_field_distribution", "UNIFORM"))

    raw = old_raw & 0x00EEFF00
    raw |= type_id & 0xFF
    if shape == "SPHERE":
        raw |= 0x00010000
    if direction == "RADIAL":
        raw |= 0x00100000
    if distribution == "GRADIENT":
        raw |= 0x01000000
    if apply == "FORCE":
        raw |= 0x10000000
    return raw


def _field_size_from_object(obj):
    scale = Vector(obj.scale)
    return (
        abs(float(scale.x)) / SCALE,
        abs(float(scale.y)) / SCALE,
        abs(float(scale.z)) / SCALE,
    )


def export_file(filepath, scene):
    fields = rvstruct.ForceFields()
    field_objs = [
        obj for obj in scene.objects
        if getattr(obj, "is_force_field", False) or obj.get("is_force_field")
    ]
    field_objs.sort(key=lambda obj: int(obj.get("force_field_index", 0)))

    for obj in field_objs:
        field = rvstruct.ForceField()
        field.raw_type = _encode_raw_type(obj)
        field.position = rvstruct.Vector(data=to_revolt_coord(obj.location))

        R_bl = obj.matrix_world.to_quaternion().to_matrix()
        field.matrix = rvstruct.Matrix()
        field.matrix.data = _blender_R_to_rv_R3_rows(R_bl)

        field.size = rvstruct.Vector(data=_field_size_from_object(obj))
        direction = getattr(obj, "force_field_direction", obj.get("force_field_direction", (0.0, -1.0, 0.0)))
        field.direction = rvstruct.Vector(data=tuple(float(v) for v in direction[:3]))
        field.magnitude = float(getattr(obj, "force_field_magnitude", obj.get("force_field_magnitude", 0.0)))
        field.damping = float(getattr(obj, "force_field_damping", obj.get("force_field_damping", 0.0)))
        field.radius_start = float(getattr(obj, "force_field_radius_start", obj.get("force_field_radius_start", 256.0)))
        field.radius_end = float(getattr(obj, "force_field_radius_end", obj.get("force_field_radius_end", 512.0)))
        field.mag_start = float(getattr(obj, "force_field_mag_start", obj.get("force_field_mag_start", 0.0)))
        field.mag_end = float(getattr(obj, "force_field_mag_end", obj.get("force_field_mag_end", 0.0)))
        fields.force_fields.append(field)

    dprint(f"[FLD] Exporting {len(fields.force_fields)} force fields to {filepath}")
    with open(filepath, "wb") as fd:
        fields.write(fd)
    return True
