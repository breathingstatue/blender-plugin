"""
Name:    hul_out
Purpose: Exports hull collision files.

Description:
Exports Re-Volt .hul collision data (convex hulls + interior spheres).
Uses a "bake transforms once" pipeline to avoid invalid halfspace sets for Qhull.
"""

import bpy
import bmesh
import importlib
from . import common
from . import rvstruct
from . import prm_in

# Reload support
if "bpy" in locals():
    importlib.reload(common)
    importlib.reload(rvstruct)

from .common import apply_trs, to_revolt_axis, to_revolt_coord, to_revolt_scale, rvbbox_from_verts
from .rvstruct import Hull
from mathutils import Vector


# -------------------------------------------------------------------------
# Debug toggle
# -------------------------------------------------------------------------
RV_HUL_DEBUG = False
def _d(msg: str):
    if RV_HUL_DEBUG:
        print(msg)


def export_file(filepath, scene):
    return export_hull(filepath, scene)


def export_hull(filepath, scene):
    hull = Hull()

    # Only MESH objects can be hulls
    chull_objs = [
        obj for obj in scene.objects
        if obj.type == "MESH" and (getattr(obj, "is_hull_convex", False) or obj.get("is_hull_convex", False))
    ]
    hull.chull_count = len(chull_objs)

    _d(f"[HUL] convex selected: {[o.name for o in chull_objs]}")

    for obj in chull_objs:
        chull = rvstruct.ConvexHull()

        bm = bmesh.new()
        bm.from_mesh(obj.data)

        # IMPORTANT:
        # Bake full world TRS into bm ONCE.
        # This prevents double-transform issues and makes plane/bbox consistent.
        apply_trs(obj, bm, transform=True)

        # Ensure normals are consistent after transform.
        bm.normal_update()
        try:
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        except Exception:
            # Some Blender builds may not need/like it; normal_update still helps.
            pass

        # Bounding box from baked vertices (no obj.matrix_world here)
        define_bounding_box(chull, bm)

        # Planes from baked faces
        for face in bm.faces:
            plane = create_plane_from_face(face)
            chull.faces.append(plane)

        chull.face_count = len(chull.faces)

        # Optional edges/verts
        process_edges_and_vertices(chull, bm)

        hull.chulls.append(chull)

        _d(f"[HUL] {obj.name}: faces={chull.face_count} edges={chull.edge_count} verts={chull.vertex_count}")

        bm.free()

    # Spheres
    hull.interior = process_sphere_hulls(scene)

    # Write the hull data to a file
    try:
        with open(filepath, "wb") as f:
            _d(f"[HUL] writing: chull_count={hull.chull_count}, built={len(hull.chulls)}, spheres={getattr(hull.interior, 'sphere_count', 0)}")
            hull.write(f)
    except IOError as e:
        print(f"Failed to write hull data: {e}")


def create_plane_from_face(face):
    """
    Face plane in baked (world) space.
    Plane is defined as: normal . x + distance = 0
    distance = -normal . point_on_plane
    """
    plane = rvstruct.Plane()

    # Face normal & point are already in baked world space (Blender axes)
    world_normal = face.normal.normalized()
    world_point = face.verts[0].co

    normal = rvstruct.Vector(data=to_revolt_axis(world_normal))
    vec = rvstruct.Vector(data=to_revolt_coord(world_point))

    plane.normal = normal
    plane.distance = -normal.dot(vec)
    return plane


def define_bounding_box(chull, bm):
    bbox_data = rvbbox_from_verts(bm.verts)
    if bbox_data is None:
        # Empty mesh safety
        chull.bbox = rvstruct.BoundingBox(data=(0, 0, 0, 0, 0, 0))
        chull.bbox_offset = rvstruct.Vector(data=(0, 0, 0))
        return

    bbox = rvstruct.BoundingBox(data=bbox_data)

    # Center offset
    chull.bbox_offset = rvstruct.Vector(data=(
        (bbox.xlo + bbox.xhi) / 2,
        (bbox.ylo + bbox.yhi) / 2,
        (bbox.zlo + bbox.zhi) / 2
    ))

    # Make bbox relative to the offset (as Re-Volt expects)
    bbox.xlo -= chull.bbox_offset[0]
    bbox.xhi -= chull.bbox_offset[0]
    bbox.ylo -= chull.bbox_offset[1]
    bbox.yhi -= chull.bbox_offset[1]
    bbox.zlo -= chull.bbox_offset[2]
    bbox.zhi -= chull.bbox_offset[2]

    chull.bbox = bbox


def process_sphere_hulls(scene):
    interior = rvstruct.Interior()

    sphere_objs = [
        obj for obj in scene.objects
        if obj.type == "MESH" and (getattr(obj, "is_hull_sphere", False) or obj.get("is_hull_sphere", False))
    ]
    interior.sphere_count = len(sphere_objs)

    _d(f"[HUL] spheres selected: {[o.name for o in sphere_objs]}")

    for obj in sphere_objs:
        sphere = rvstruct.Sphere()

        # Use world-space center (handles parenting/constraints)
        world_center = obj.matrix_world.translation
        sphere.center = rvstruct.Vector(data=to_revolt_coord(world_center))

        # Local radius from geometry, then scale to world using max scale component
        r_local = calculate_radius_from_geometry(obj)
        s = obj.matrix_world.to_scale()
        r_world = r_local * max(s.x, s.y, s.z)

        sphere.radius = to_revolt_scale(r_world)

        interior.spheres.append(sphere)

    return interior


def calculate_radius_from_geometry(obj):
    """
    Local-space radius estimate from mesh bounds.
    """
    if not obj.data.vertices:
        return 0.0

    verts = [v.co for v in obj.data.vertices]
    min_x = min(v.x for v in verts)
    max_x = max(v.x for v in verts)
    min_y = min(v.y for v in verts)
    max_y = max(v.y for v in verts)
    min_z = min(v.z for v in verts)
    max_z = max(v.z for v in verts)

    diameter_x = max_x - min_x
    diameter_y = max_y - min_y
    diameter_z = max_z - min_z

    return max(diameter_x, diameter_y, diameter_z) * 0.5


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
