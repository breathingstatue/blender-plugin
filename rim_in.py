"""
Name:    rim_in
Purpose: Imports mirror plane files

Description:
Mirror planes are used to determine reflective surfaces.

"""

import bpy

if "common" in locals():
    import imp
    imp.reload(common)
    imp.reload(rvstruct)

from . import common
from . import rvstruct
from .rvstruct import RIM, MirrorPlane
from .common import *

def import_file(filepath, scene):
    with open(filepath, "rb") as f:
        rim = rvstruct.RIM(f)

    dprint("Mirror planes:", rim.num_mirror_planes)

    # Extracts the base filename without path and extension
    base_filename = filepath.rsplit(os.sep, 1)[1].rsplit('.', 1)[0]

    if rim.num_mirror_planes == 0 or rim.mirror_planes == []:
        queue_error("importing mirror file", "File contains 0 mirror planes")
        return

    for index, mirror_plane in enumerate(rim.mirror_planes):
        # Modified to include '.rim' in the unique name
        unique_name = f"{base_filename}_{index:03}.rim"  # Appends the index and '.rim'
        
        me = bpy.data.meshes.new(unique_name)
        bm = bmesh.new()

        verts = []
        for v in mirror_plane.vertices[::-1]:
            verts.append(bm.verts.new(to_blender_coord(v)))
            bm.verts.ensure_lookup_table()

        bm.faces.new(verts)

        bm.to_mesh(me)
        bm.free()

        ob = bpy.data.objects.new(unique_name, me)  # Use the unique name here
        ob["is_mirror_plane"] = True
        scene.collection.objects.link(ob)