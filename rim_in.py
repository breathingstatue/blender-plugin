"""
Name:    rim_in
Purpose: Imports Re-Volt mirror plane files (.rim)

Description:
Mirror planes are used to determine reflective surfaces.
"""

import os
import bpy
import bmesh
import importlib

from . import common
from . import rvstruct
from .common import dprint, queue_error, to_blender_coord

# --- Proper modern reload ---
if "common" in locals():
    importlib.reload(common)
    importlib.reload(rvstruct)


def _link_object_to_scene_collection(scene: bpy.types.Scene, obj: bpy.types.Object) -> None:
    # Avoid double-link errors
    try:
        scene.collection.objects.link(obj)
    except RuntimeError:
        pass


def import_file(filepath: str, scene: bpy.types.Scene):
    with open(filepath, "rb") as f:
        rim = rvstruct.RIM(f)

    dprint("Mirror planes:", rim.num_mirror_planes)

    base_filename = os.path.splitext(os.path.basename(filepath))[0]

    if rim.num_mirror_planes == 0 or not rim.mirror_planes:
        queue_error("importing mirror file", "File contains 0 mirror planes")
        return

    for index, mirror_plane in enumerate(rim.mirror_planes):
        unique_name = f"{base_filename}_{index:03}.rim"

        me = bpy.data.meshes.new(unique_name)
        bm = bmesh.new()

        # MirrorPlane has 4 vertices. Reverse order to keep consistent winding.
        verts = []
        for v in mirror_plane.vertices[::-1]:
            verts.append(bm.verts.new(to_blender_coord(v)))

        bm.verts.ensure_lookup_table()
        bm.faces.new(verts)

        bm.to_mesh(me)
        bm.free()

        ob = bpy.data.objects.new(unique_name, me)
        ob["is_mirror_plane"] = True
        try:
            ob.is_mirror_plane = True
        except Exception:
            pass

        _link_object_to_scene_collection(scene, ob)
