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


def export_file(filepath, scene):
    return export_hull(filepath, scene)

def export_hull(filepath, scene):
    hull = Hull()

    # Get convex hull objects
    chull_objs = [
        obj for obj in scene.objects
        if getattr(obj, "is_hull_convex", obj.get("is_hull_convex", False))
    ]
    hull.chull_count = len(chull_objs)

    for obj in chull_objs:
        chull = rvstruct.ConvexHull()
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        apply_trs(obj, bm)

        # Calculate and assign the bounding box
        define_bounding_box(chull, bm, obj.matrix_world)

        # Process faces into planes
        for face in bm.faces:
            plane = create_plane_from_face(face, obj.matrix_world)  # Apply object transformations
            chull.faces.append(plane)
            chull.face_count += 1

        # Optional: Process edges and vertices (if needed)
        process_edges_and_vertices(chull, bm)

        hull.chulls.append(chull)

    # Process hull spheres
    hull.interior = process_sphere_hulls(scene)

    # Write the hull data to a file
    try:
        with open(filepath, "wb") as f:
            hull.write(f)
    except IOError as e:
        print(f"Failed to write hull data: {e}")

def create_plane_from_face(face, obj_matrix):
    plane = rvstruct.Plane()
    # Apply world transformations to the face normal and vertex coordinates
    normal = rvstruct.Vector(data=to_revolt_axis(obj_matrix @ face.normal))
    vec = rvstruct.Vector(data=to_revolt_coord(obj_matrix @ face.verts[0].co))
    distance = -normal.dot(vec)

    plane.normal = normal
    plane.distance = distance
    return plane

def define_bounding_box(chull, bm, obj_matrix):
    # Create a temporary class to mimic .co attribute
    class TempVert:
        def __init__(self, co):
            self.co = co

    # Transform vertices and wrap them in the temporary class
    transformed_verts = [TempVert(obj_matrix @ vert.co) for vert in bm.verts]

    # Calculate bounding box
    bbox = rvstruct.BoundingBox(data=rvbbox_from_verts(transformed_verts))

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
    
def process_sphere_hulls(scene):
    interior = rvstruct.Interior()
    sphere_objs = [
        obj for obj in scene.objects
        if getattr(obj, "is_hull_sphere", obj.get("is_hull_sphere", False))
    ]
    interior.sphere_count = len(sphere_objs)

    for obj in sphere_objs:
        sphere = rvstruct.Sphere()

        # Convert location to Re-Volt coordinates
        sphere.center = rvstruct.Vector(data=to_revolt_coord(obj.location))
        
        # Use the geometry-based radius calculation
        sphere.radius = to_revolt_scale(calculate_radius_from_geometry(obj))
        
        interior.spheres.append(sphere)

    return interior

def calculate_radius_from_geometry(obj):
    """
    Calculate the radius of a spherical object based on its vertex geometry.
    Works for UV spheres or similar.
    """
    if not obj.data.vertices:
        return 0  # No geometry, return a default radius

    # Get all vertex coordinates in the local space of the object
    verts = [v.co for v in obj.data.vertices]

    # Calculate the min and max coordinates along each axis
    min_x = min(v.x for v in verts)
    max_x = max(v.x for v in verts)
    min_y = min(v.y for v in verts)
    max_y = max(v.y for v in verts)
    min_z = min(v.z for v in verts)
    max_z = max(v.z for v in verts)

    # Compute the bounding box diameter along each axis
    diameter_x = max_x - min_x
    diameter_y = max_y - min_y
    diameter_z = max_z - min_z

    # The radius is half the largest diameter
    max_diameter = max(diameter_x, diameter_y, diameter_z)
    radius = max_diameter / 2

    return radius

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