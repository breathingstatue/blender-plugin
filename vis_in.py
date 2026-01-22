"""
Name:    vis_in
Purpose: Imports Re-Volt level Visiboxes (.vis)

Description:
Visibox file contains IDs of either Camera or Cubes (Visiboxes).
"""

import bpy
import bmesh
import math
from mathutils import Vector, Euler
from . import common
from .common import to_blender_coord
from .rvstruct import Visiboxes


def import_file(filepath, scene):
    print(f"Importing vis file: {filepath}")
    with open(filepath, 'rb') as file:
        visidata = Visiboxes(file)
    visibox_list = visidata.visiboxes

    existing_names = {obj.name for obj in bpy.data.objects}
    print(f"Number of visiboxes: {len(visibox_list)}")

    for visibox in visibox_list:
        typ = visibox.type
        id_ = visibox.id

        # Re-Volt order: min_x, max_x, min_y, max_y, min_z, max_z
        x_min, x_max = visibox.coords[0], visibox.coords[1]
        y_min, y_max = visibox.coords[2], visibox.coords[3]
        z_min, z_max = visibox.coords[4], visibox.coords[5]

        # Compute center and size in Re-Volt coordinates
        center_rv = (
            (x_min + x_max) / 2,
            (y_min + y_max) / 2,
            (z_min + z_max) / 2,
        )
        size_rv = (
            abs(x_max - x_min),
            abs(y_max - y_min),
            abs(z_max - z_min),
        )

        # Convert to Blender coordinates
        center = Vector(to_blender_coord(center_rv))
        size = Vector(size_rv) * 0.01  # assuming SCALE = 100

        obj = create_visibox(
            id_=id_,
            typ=typ,
            location=center,
            size=size,
            existing_names=existing_names
        )


def create_visibox(id_=0, typ=1, location=(0, 0, 0), size=(1, 1, 1), existing_names=None):
    collection_name = "VISIBOXES"

    if collection_name not in bpy.data.collections:
        new_collection = bpy.data.collections.new(collection_name)
        bpy.context.scene.collection.children.link(new_collection)
    else:
        new_collection = bpy.data.collections[collection_name]

    if existing_names is None:
        existing_names = {obj.name for obj in bpy.data.objects}

    base_name = f"Visibox_{id_}"
    mesh_name = get_unique_name(f"{base_name}_Mesh", existing_names)
    obj_name = get_unique_name(base_name, existing_names)

    # Create mesh and object
    mesh = bpy.data.meshes.new(name=mesh_name)
    obj = bpy.data.objects.new(name=obj_name, object_data=mesh)

    # Link object to collections
    bpy.context.scene.collection.objects.link(obj)
    new_collection.objects.link(obj)
    bpy.context.scene.collection.objects.unlink(obj)

    # Build geometry as axis-aligned wireframe cube
    bm = bmesh.new()
    half = Vector(size) / 2

    corners = [
        Vector((-half.x, -half.y, -half.z)),
        Vector(( half.x, -half.y, -half.z)),
        Vector(( half.x,  half.y, -half.z)),
        Vector((-half.x,  half.y, -half.z)),
        Vector((-half.x, -half.y,  half.z)),
        Vector(( half.x, -half.y,  half.z)),
        Vector(( half.x,  half.y,  half.z)),
        Vector((-half.x,  half.y,  half.z)),
    ]

    verts = [bm.verts.new(corner) for corner in corners]
    bm.verts.ensure_lookup_table()
    for v1, v2 in [
        (0, 1), (1, 2), (2, 3), (3, 0),
        (4, 5), (5, 6), (6, 7), (7, 4),
        (0, 4), (1, 5), (2, 6), (3, 7),
    ]:
        bm.edges.new((verts[v1], verts[v2]))
    bm.to_mesh(mesh)
    bm.free()

    # Set object properties
    obj.location = Vector(location)
    obj.rotation_mode = 'XYZ'
    obj.rotation_euler = Euler((math.radians(-90), 0, 0), 'XYZ')
    obj.display_type = 'WIRE'
    obj.show_in_front = True
    obj.scale = Vector((1, 1, 1))

    # --- Visibox markers (set BOTH ID-props and RNA props) ---
    obj["is_visibox"] = True
    obj["visibox_id"] = int(id_)
    obj["visibox_type"] = str(typ)

    # These are your registered bpy.props on bpy.types.Object:
    obj.is_visibox = True
    obj.visibox_id = int(id_)
    obj.visibox_type = str(typ)

    return obj


def get_unique_name(base_name, existing_names):
    if base_name not in existing_names:
        return base_name

    suffix_index = ord('a')
    while f"{base_name}{chr(suffix_index)}" in existing_names:
        suffix_index += 1
        if suffix_index > ord('z'):
            raise ValueError("Too many objects with the same base name.")
    return f"{base_name}{chr(suffix_index)}"
