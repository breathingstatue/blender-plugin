"""
Name:    rim_in
Purpose: Imports mirror plane files

Description:
Mirror planes are used to determine reflective surfaces.
"""

import os
import bpy
import bmesh
import importlib

from . import common
from . import rvstruct
from .rvstruct import RIM, MirrorPlane
from .common import dprint, queue_error, to_blender_coord

# --- Proper modern reload ---
if "common" in locals():
    importlib.reload(common)
    importlib.reload(rvstruct)

def import_file(filepath, scene):
    with open(filepath, "rb") as f:
        rim = rvstruct.RIM(f)

    dprint("Mirror planes:", rim.num_mirror_planes)

    base_filename = filepath.rsplit(os.sep, 1)[1].rsplit('.', 1)[0]

    if rim.num_mirror_planes == 0 or not rim.mirror_planes:
        queue_error("importing mirror file", "File contains 0 mirror planes")
        return

    for index, mirror_plane in enumerate(rim.mirror_planes):
        unique_name = f"{base_filename}_{index:03}.rim"

        me = bpy.data.meshes.new(unique_name)
        bm = bmesh.new()

        verts = []
        for v in mirror_plane.vertices[::-1]:
            verts.append(bm.verts.new(to_blender_coord(v)))
            bm.verts.ensure_lookup_table()

        bm.faces.new(verts)
        bm.to_mesh(me)
        bm.free()

        ob = bpy.data.objects.new(unique_name, me)
        ob["is_mirror_plane"] = True

        if ob.name not in bpy.context.scene.collection.objects:
            bpy.context.scene.collection.objects.link(ob)
        else:
            print(f"Object '{ob.name}' is already in the scene collection.")
