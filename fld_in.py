"""
Name:    fld_in
Purpose: Imports Re-Volt force field files (.fld)
"""

import bpy
import bmesh
import math
from mathutils import Matrix as BlenderMatrix, Vector as BlenderVector

from . import rvstruct
from .common import SCALE, dprint, to_blender_coord, to_blender_axis


COLLECTION_NAME = "FORCE_FIELDS"

FIELD_TYPE_FROM_ID = {
    0: "LINEAR",
    1: "ORIENTATION_UP",
    2: "VELOCITY",
    3: "SPHERICAL",
    4: "WIND",
    5: "ANGULAR",
    6: "ANGULAR_VELOCITY",
    7: "ORIENTATION_FWD",
}


def ensure_collection(name=COLLECTION_NAME):
    collection = bpy.data.collections.get(name)
    if not collection:
        collection = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(collection)
    return collection


def _unique_name(base_name, existing):
    if base_name not in existing:
        return base_name
    index = 1
    while f"{base_name}_{index}" in existing:
        index += 1
    return f"{base_name}_{index}"


def _rv_rows_to_blender_matrix(rv_rows):
    c0 = (rv_rows[0][0], rv_rows[1][0], rv_rows[2][0])
    c1 = (rv_rows[0][1], rv_rows[1][1], rv_rows[2][1])
    c2 = (rv_rows[0][2], rv_rows[1][2], rv_rows[2][2])

    b0 = to_blender_axis(c0)
    b1 = to_blender_axis(c1)
    b2 = to_blender_axis(c2)
    return BlenderMatrix((
        (float(b0[0]), float(b1[0]), float(b2[0])),
        (float(b0[1]), float(b1[1]), float(b2[1])),
        (float(b0[2]), float(b1[2]), float(b2[2])),
    ))


def _create_wire_box(name):
    mesh = bpy.data.meshes.new(name + "_Mesh")
    obj = bpy.data.objects.new(name, mesh)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=2.0)
    bmesh.ops.delete(bm, geom=bm.faces[:], context='FACES_ONLY')
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    return obj


def _create_wire_sphere(name):
    mesh = bpy.data.meshes.new(name + "_Mesh")
    obj = bpy.data.objects.new(name, mesh)
    segments = 13
    verts = []
    edges = []

    def add_ring(axis):
        start = len(verts)
        for i in range(segments):
            angle = 2.0 * math.pi * i / segments
            c = math.cos(angle)
            s = math.sin(angle)
            if axis == "Z":
                verts.append((c, s, 0.0))
            elif axis == "Y":
                verts.append((c, 0.0, s))
            else:
                verts.append((0.0, c, s))
        for i in range(segments):
            edges.append((start + i, start + ((i + 1) % segments)))

    add_ring("Z")
    add_ring("Y")
    add_ring("X")
    mesh.from_pydata(verts, edges, [])
    mesh.update()
    return obj


def _decode_type(raw_type):
    type_id = int(raw_type) & 0xFF
    return FIELD_TYPE_FROM_ID.get(type_id, "LINEAR")


def _decode_shape(raw_type):
    return "SPHERE" if (int(raw_type) & 0x00010000) else "BOX"


def _decode_apply(raw_type):
    return "FORCE" if ((int(raw_type) >> 28) & 0x0F) == 1 else "ACCELERATE"


def _decode_direction(option):
    return "RADIAL" if (int(option) & 0x00100000) else "LINEAR"


def _decode_distribution(option):
    return "GRADIENT" if ((int(option) >> 24) & 0x0F) == 1 else "UNIFORM"


def _set_field_props(obj, field, index):
    raw_type = int(field.raw_type)
    obj["is_force_field"] = True
    obj["force_field_index"] = int(index)
    obj["force_field_raw_type"] = raw_type

    obj.is_force_field = True
    obj.force_field_type = _decode_type(raw_type)
    obj.force_field_shape = _decode_shape(raw_type)
    obj.force_field_apply = _decode_apply(raw_type)
    obj.force_field_direction_mode = _decode_direction(raw_type)
    obj.force_field_distribution = _decode_distribution(raw_type)
    obj.force_field_magnitude = float(field.magnitude)
    obj.force_field_damping = float(field.damping)
    obj.force_field_mag_start = float(field.mag_start)
    obj.force_field_mag_end = float(field.mag_end)
    obj.force_field_radius_start = float(field.radius_start)
    obj.force_field_radius_end = float(field.radius_end)
    obj.force_field_direction = tuple(float(v) for v in field.direction)
    obj.force_field_option = raw_type


def import_file(filepath, scene):
    with open(filepath, "rb") as file:
        fields = rvstruct.ForceFields(file)

    collection = ensure_collection()
    existing = {obj.name for obj in bpy.data.objects}
    dprint(f"[FLD] Importing {len(fields.force_fields)} force fields from {filepath}")

    for index, field in enumerate(fields.force_fields):
        field_type = _decode_type(field.raw_type)
        shape = _decode_shape(field.raw_type)
        name = _unique_name(f"ForceField_{index}_{field_type}", existing)
        existing.add(name)

        obj = _create_wire_sphere(name) if shape == "SPHERE" else _create_wire_box(name)
        obj.display_type = 'WIRE'
        obj.show_in_front = True
        obj.location = to_blender_coord(field.position.data)
        obj.rotation_mode = 'QUATERNION'
        obj.rotation_quaternion = _rv_rows_to_blender_matrix(field.matrix.data).to_quaternion()
        obj.scale = tuple(max(0.001, abs(float(v)) * SCALE) for v in field.size)

        _set_field_props(obj, field, index)

        scene.collection.objects.link(obj)
        collection.objects.link(obj)
        try:
            scene.collection.objects.unlink(obj)
        except Exception:
            pass

    return True
