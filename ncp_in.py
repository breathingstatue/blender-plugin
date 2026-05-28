"""
Name:    ncp_in
Purpose: Imports Re-Volt collision files (.ncp)

Description:
Imports collision files.
"""

import os
import bpy
import bmesh
import importlib
from mathutils import Color

from . import common
from . import rvstruct
from .rvstruct import NCP, Vector as RVVector, Polyhedron, Plane
from .common import *

# Reload imports if 'bpy' is already in locals (Blender add-on reload)
if "bpy" in locals():
    importlib.reload(common)
    importlib.reload(rvstruct)


def intersect(d1, n1, d2, n2, d3, n3):
    """ Intersection of three planes
    "If three planes are each specified by a point x and a unit normal vec n":
    http://mathworld.wolfram.com/Plane-PlaneIntersection.html """
    det = n1.scalar(n2.cross(n3))

    # If det is too small, there is no intersection
    if abs(det) < 1e-100:
        return None

    # Returns intersection point
    return (d1 * n2.cross(n3) +
            d2 * n3.cross(n1) +
            d3 * n1.cross(n2)
            ) / det


def import_file(filepath, scene):
    with open(filepath, 'rb') as file:
        filename = os.path.basename(filepath)
        ncp = NCP(file)
        print("Imported NCP file.")

    me = bpy.data.meshes.new(name=filename)
    bm = bmesh.new()
    materials_dict = {}

    material_layer = bm.faces.layers.int.new("Material")
    type_layer = bm.faces.layers.int.new("NCPType")

    for poly in ncp.polyhedra:
        ds = [-to_blender_scale(p.distance) for p in poly.planes]
        ns = [RVVector(data=to_blender_axis(p.normal)) for p in poly.planes]
        verts = []

        if poly.type & NCP_QUAD:
            verts.extend([
                intersect(ds[0], ns[0], ds[1], ns[1], ds[2], ns[2]),
                intersect(ds[0], ns[0], ds[2], ns[2], ds[3], ns[3]),
                intersect(ds[0], ns[0], ds[3], ns[3], ds[4], ns[4]),
                intersect(ds[0], ns[0], ds[4], ns[4], ds[1], ns[1])
            ])
            face_indices = (0, 3, 2, 1)
        else:
            verts.extend([
                intersect(ds[0], ns[0], ds[1], ns[1], ds[2], ns[2]),
                intersect(ds[0], ns[0], ds[2], ns[2], ds[3], ns[3]),
                intersect(ds[0], ns[0], ds[3], ns[3], ds[1], ns[1])
            ])
            face_indices = (0, 2, 1)

        if any(v is None for v in verts):
            print('Skipping polyhedron (no intersection).')
            continue

        bmverts = [bm.verts.new(v) for v in verts if v]

        try:
            new_face = bm.faces.new([bmverts[i] for i in face_indices])
        except ValueError:
            continue

        new_face[material_layer] = poly.material
        new_face[type_layer] = poly.type

        material_info = next(
            (item for item in MATERIALS if item[0] == str(poly.material)),
            None
        )
        if material_info:
            material_name = material_info[1]
        else:
            material_name = f"Material_{poly.material}"

        mat = materials_dict.get(material_name)
        if mat is None:
            mat = bpy.data.materials.get(material_name)
            if mat is None:
                mat = bpy.data.materials.new(name=material_name)
            mat.use_nodes = True
            bsdf = mat.node_tree.nodes.get('Principled BSDF')
            if bsdf:
                if 0 <= poly.material < len(COLORS):
                    base_color = COLORS[poly.material]
                else:
                    base_color = (1.0, 1.0, 1.0)
                bsdf.inputs['Base Color'].default_value = (*base_color, 1.0)
            materials_dict[material_name] = mat

        mat = materials_dict[material_name]
        if me.materials.find(mat.name) == -1:
            me.materials.append(mat)

        mat_index = me.materials.find(mat.name)
        if mat_index == -1:
            print(f"Warning: Failed to assign material '{mat.name}' to face.")
        else:
            new_face.material_index = mat_index

    bm.to_mesh(me)
    bm.free()

    ob = bpy.data.objects.new(name=filename, object_data=me)
    ob["source_path"] = filepath
    ob["is_ncp_collision"] = True
    # Check if the object is already in the scene collection
    if ob.name not in bpy.context.scene.collection.objects:
        bpy.context.scene.collection.objects.link(ob)
    else:
        print(f"Object '{ob.name}' is already in the scene collection.")

    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    return ob
