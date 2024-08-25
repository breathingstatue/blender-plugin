"""
Name:    ncp_out
Purpose: Exports Re-Volt collisision files (.ncp)

Description:
Exports collision files.

"""


if "bpy" in locals():
    import imp
    imp.reload(common)
    imp.reload(rvstruct)

import os
import bpy
import bmesh

from math import ceil
from mathutils import Color, Matrix
from . import common
from . import rvstruct

from .common import dprint, triangulate_ngons, apply_trs, NCP_NOCOLL, queue_error, DEBUG, NCP_PROP_MASK, to_revolt_axis, to_revolt_coord
from .common import NCP_QUAD, rvbbox_from_verts
from .rvstruct import (
    BoundingBox,
    LookupGrid,
    LookupList,
    NCP,
    Plane,
    Polyhedron,
    Vector
)


def export_file(filepath, scene):
    print("Exporting NCP to {}...".format(filepath))

    # Collects objects for export
    objs = []
    if scene.ncp_export_selected:
        # Accessing the 'ignore_ncp' property directly from the object
        # Using obj.get('ignore_ncp', False) provides a default value of False if the property is not found
        objs = [ob for ob in scene.objects if ob.select_get() and not ob.get('ignore_ncp', False)]
    else:
        for obj in scene.objects:
            conditions = (
                obj.data and
                obj.type == "MESH" and
                not obj.get('is_cube', False) and
                not obj.get('is_bcube', False) and
                not obj.get('is_bbox', False) and
                not obj.get('ignore_ncp', False) and
                not obj.get('is_mirror_plane', False) and
                not obj.get('is_track_zone', False)
            )
            if conditions:
                objs.append(obj)

    if not objs:
        common.queue_error("exporting NCP", "No suitable objects in scene.")
        return
    else:
        dprint("Suitable objects: {}".format(", ".join([o.name for o in objs])))


    ncp = NCP()

    # Determine if a transformation is necessary
    transform = len(objs) != 1 or scene.apply_translation

    # Adds all meshes to the NCP
    for obj in objs:
        dprint(f"Adding {obj.name} to ncp...")
        bm = bmesh.new()
        bm.from_mesh(obj.data)

        if scene.triangulate_ngons:
            num_ngons = triangulate_ngons(bm)
            if num_ngons > 0:
                print(f"Triangulated {num_ngons} n-gons")

        # Applies translation, rotation, and scale
        apply_trs(obj, bm, transform)

        add_bm_to_ncp(bm, ncp, scene)

    ncp.polyhedron_count = len(ncp.polyhedra)
    if ncp.polyhedron_count > 65535:
        common.queue_error("exporting ncp", "Too many collision polygons, try cutting it down.")
        return

    if scene.ncp_export_collgrid:
        dprint("Exporting collision grid...")
        ncp.generate_lookup_grid(grid_size=scene.ncp_collgrid_size)

    with open(filepath, "wb") as f:
        ncp.write(f)

    bm.free()

def add_bm_to_ncp(bm, ncp, scene):

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
            dprint("Ignoring polygon due to nocoll flag")
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
