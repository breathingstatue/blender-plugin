"""
Name:    ncp_in
Purpose: Exports Re-Volt collisision files (.ncp)

Description:
Exports collision files.

"""

import os
import bpy
import bmesh
import importlib
from math import ceil
from mathutils import Color, Matrix
from . import common
from . import rvstruct

# Check if 'bpy' is already in locals to determine if this is a reload scenario
if "bpy" in locals():
    importlib.reload(common)
    importlib.reload(rvstruct)

# Importing specific classes and functions
from .common import NCP_NOCOLL, NCP_PROP_MASK, NCP_QUAD, to_revolt_axis, to_revolt_coord, rvbbox_from_verts
from .rvstruct import BoundingBox, LookupGrid, LookupList, NCP, Plane, Polyhedron, Vector

# Add specific imports from common as needed
# Example: from .common import specific_function, SpecificClass


def export_file(filepath, scene, context):
    print("Exporting NCP to {}...".format(filepath))

    # Collects objects for export
    objs = []
    if scene.ncp_export_selected:
        objs = [ob for ob in scene.objects if ob.select_get()]
    else:
        for obj in scene.objects:
            conditions = (
                obj.data and
                obj.type == "MESH" and
                not obj.revolt.is_cube and
                not obj.revolt.is_bcube and
                not obj.revolt.is_bbox and
                not obj.revolt.ignore_ncp and
                not obj.revolt.is_mirror_plane and
                not obj.revolt.is_track_zone
            )
            if conditions:
                objs.append(obj)

    if not objs:
        common.queue_error("exporting NCP", "No suitable objects in scene.")
        return
    else:
        print("Suitable objects: {}".format(", ".join([o.name for o in objs])))

    ncp = NCP()

    # Adds all meshes to the NCP
    for obj in objs:
        print("Adding {} to NCP...".format(obj.name))
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bm.transform(obj.matrix_world)

        if getattr(context.scene, 'triangulate_ngons_enabled', False):
            num_ngons = common.triangulate_ngons(bm)
            if num_ngons > 0:
                print(f"Triangulated {num_ngons} n-gons")

        add_bm_to_ncp(bm, ncp)
        bm.free()

    # Create a collision grid if needed
    if scene.ncp_export_collgrid:
        print("Exporting collision grid...")
        ncp.generate_lookup_grid(grid_size=scene.ncp_collgrid_size)

    # Writes the NCP to file
    with open(filepath, "wb") as f:
        ncp.write(f)

def add_bm_to_ncp(bm, ncp):

    # Material and type layers. The preview layer will be ignored.
    material_layer = (bm.faces.layers.int.get("Material") or
                      bm.faces.layers.int.new("Material"))
    type_layer = (bm.faces.layers.int.get("NCPType") or
                  bm.faces.layers.int.new("NCPType"))

    for face in bm.faces:
        poly = Polyhedron()

        # Doesn't export if material is NONE
        if face[material_layer] < 0:
            continue

        # Doesn't export if nocoll flag is set (non-RV)
        if face[type_layer] & NCP_NOCOLL:
            print("Ignoring polygon due to nocoll flag")
            continue

        # Sets polyhedron properties
        poly.material = face[material_layer]
        if poly.material > 26:
            print(face[material_layer])
            queue_error("exporting to .ncp", "Invalid material")
            if DEBUG:
                return

        poly.type = face[type_layer] & NCP_PROP_MASK

        verts = face.verts

        # Determines normal and distance for main plane
        normal = Vector(data=to_revolt_axis(face.normal))
        normal.normalize()

        vec = Vector(data=to_revolt_coord(verts[0].co))
        distance = -normal.dot(vec)

        # Creates main plane
        poly.planes.append(Plane(n=normal, d=distance))

        if len(face.verts) == 4:
            # Sets the quad flag because the poly has 4 vertices
            poly.type |= NCP_QUAD

        # Writes the cutting planes
        vcount = len(verts[:4])
        for i in range(vcount - 1, -1, -1):
            vec0 = Vector(data=to_revolt_coord(verts[i].co))
            vec1 = Vector(data=to_revolt_coord(verts[(i + 1) % vcount].co))

            pnormal = normal.cross(vec0 - vec1)
            pnormal.normalize()
            distance = -pnormal.dot(vec0)

            poly.planes.append(Plane(n=Vector(data=pnormal), d=distance))

        # Writes remaining empty planes
        for i in range(4 - vcount):
            poly.planes.append(Plane())

        # Creates a bbox and adds the poly to the ncp
        poly.bbox = BoundingBox(data=rvbbox_from_verts(verts))
        ncp.polyhedra.append(poly)
