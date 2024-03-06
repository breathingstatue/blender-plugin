"""
Name:    hul_out
Purpose: Exports hull collision files.

Description:

"""

import bpy
import bmesh
import mathutils
import importlib
from . import common
from . import rvstruct
from . import prm_in

# Check if 'bpy' is already in locals to determine if this is a reload scenario
if "bpy" in locals():
    importlib.reload(common)
    importlib.reload(rvstruct)

# Importing specific classes and functions
from .common import apply_trs, to_revolt_axis, to_revolt_coord, to_revolt_scale, rvbbox_from_verts
from .rvstruct import Hull, ConvexHull, BoundingBox, Edge, Sphere, Plane, Interior
from mathutils import Color, Vector


def get_plane(x, y, z):
    vector1 = [x[1] - x[0], y[1] - y[0], z[1] - z[0]]
    vector2 = [x[2] - x[0], y[2] - y[0], z[2] - z[0]]

    normal = vector1.cross(vector2)

    distance = - (normal[0] * x[0] + normal[1] * y[0] + normal[2] * z[0])


def export_hull(filepath, scene):
    hull = rvstruct.Hull()

    # Export Convex Hulls
    chull_objs = [obj for obj in scene.objects if obj.name.startswith("is_hull_convex")]
    hull.chull_count = len(chull_objs)

    for obj in chull_objs:
        chull = rvstruct.ConvexHull()
        bm = bmesh.new()
        bm.from_mesh(obj.data)

        apply_trs(obj, bm, transform=False)

        for face in bm.faces:
            plane = create_plane_from_face(face)
            chull.faces.append(plane)
            chull.face_count += 1

        process_edges_and_vertices(chull, bm)
        define_bounding_box(chull, bm)

        bm.free()        
        hull.chulls.append(chull)

    # Export Sphere Hulls
    hull.interior = process_sphere_hulls(scene)

    # Write to file
    with open(filepath, "wb") as f:
        hull.write(f)
        
def create_plane_from_face(face):
    plane = rvstruct.Plane()
    normal = rvstruct.Vector(data=to_revolt_axis(face.normal))
    vec = rvstruct.Vector(data=to_revolt_coord(face.verts[0].co))
    distance = -normal.dot(vec)

    plane.normal = normal
    plane.distance = distance
    return plane

def process_sphere_hulls(scene):
    interior = rvstruct.Interior()
    # Filter to include only mesh objects marked as sphere hulls
    sphere_objs = [obj for obj in scene.objects if obj.name.startswith("is_hull_sphere")]
    interior.sphere_count = len(sphere_objs)

    for obj in sphere_objs:
        sphere = rvstruct.Sphere()
        sphere.center = rvstruct.Vector(data=to_revolt_coord(obj.location))
        sphere.radius = to_revolt_scale(sum(obj.scale) / 3)
        interior.spheres.append(sphere)

    return interior

def process_edges_and_vertices(chull, bm):
    ind = 0
    for edge in bm.edges:
        rvedge = rvstruct.Edge()
        for vert in edge.verts:
            rvvert = rvstruct.Vector(data=to_revolt_coord(vert.co))
            existing_vertex = next((v for v in chull.vertices if v.data == rvvert.data), None)
            if existing_vertex:
                rvedge.vertices.append(chull.vertices.index(existing_vertex))
            else:
                chull.vertices.append(rvvert)
                rvedge.vertices.append(ind)
                ind += 1
        chull.edges.append(rvedge)
    chull.vertex_count = len(chull.vertices)
    chull.edge_count = len(chull.edges)

def define_bounding_box(chull, bm):
    bbox = rvstruct.BoundingBox(data=rvbbox_from_verts(bm.verts))
    chull.bbox_offset = rvstruct.Vector(data=(
        (bbox.xlo + bbox.xhi) / 2,
        (bbox.ylo + bbox.yhi) / 2,
        (bbox.zlo + bbox.zhi) / 2
    ))
    bbox.xlo -= chull.bbox_offset[0]
    bbox.xhi -= chull.bbox_offset[0]
    bbox.ylo -= chull.bbox_offset[1]
    bbox.yhi -= chull.bbox_offset[1]
    bbox.zlo -= chull.bbox_offset[2]
    bbox.zhi -= chull.bbox_offset[2]

    chull.bbox = bbox

def export_file(filepath, scene):
    return export_hull(filepath, scene)
