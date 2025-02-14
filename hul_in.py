"""
Name:    hul_in
Purpose: Imports hull collision files.

Description:

"""

import os
import subprocess
import re
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
from .common import COL_SPHERE, COL_HULL, to_blender_coord, to_blender_scale, create_material
from .rvstruct import Hull
from mathutils import Color, Vector

def import_file(filepath, scene):
    return import_hull(filepath, scene)

def import_hull(filepath, scene):
    with open(filepath, "rb") as fd:
        hull = Hull(fd)

    script_dir = os.path.dirname(os.path.realpath(__file__))
    qhull_in = os.path.join(script_dir, "hull", "qhull_in.txt")
    qhull_out = os.path.join(script_dir, "hull", "qhull_out.txt")
    qhull_exe = os.path.join(script_dir, "hull", "qhull.exe") if os.name == "nt" else "qhull"

    for chull in hull.chulls:
        offset = rvstruct.Vector(data=(
            (chull.bbox.xlo + chull.bbox.xhi) / 2,
            (chull.bbox.ylo + chull.bbox.yhi) / 2,
            (chull.bbox.zlo + chull.bbox.zhi) / 2
        ))
        chull.bbox_offset += offset

        bm = bmesh.new()
        me = bpy.data.meshes.new("Hull_Convex")  # Changed name to "Hull_Convex"

        with open(qhull_in, "w") as file:
            file.write("3 1\n")
            file.write("{} {} {}\n".format(*chull.bbox_offset))
            file.write("4\n")
            file.write("{}\n".format(len(chull.faces)))
            for face in chull.faces:
                file.write("{} {} {} {}\n".format(*face.normal, face.distance))

        subprocess.Popen([qhull_exe, "H", "Fp", "FN", "E0.0001", "TI", qhull_in, "TO", qhull_out]).wait()

        with open(qhull_out, "r") as file:
            if not file.readline():
                continue

            for _ in range(int(file.readline())):
                bm.verts.new(to_blender_coord([float(s) for s in re.findall(r"\S+", file.readline())]))

            bm.verts.ensure_lookup_table()
            for _ in range(int(file.readline())):
                face = [int(s) for s in re.findall(r"\S+", file.readline())][:0:-1]
                if len(face) > 2:
                    bm.faces.new([bm.verts[i] for i in face])

        me.materials.append(create_material("RVHull", COL_HULL, 0.3))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(me)

        ob = bpy.data.objects.new("Hull_Convex", me)  # Changed name here
        ob.show_transparent = True
        ob.show_wire = True
        ob.is_hull_convex = True
        ob["is_hull_convex"] = True
        bpy.context.collection.objects.link(ob)

    for sphere in hull.interior.spheres:
        create_sphere(scene, sphere.center, sphere.radius, "Hull_Sphere")


def create_sphere(scene, center, radius, filename):
    # Convert center and radius to Blender scale
    center = to_blender_coord(center)
    radius = to_blender_scale(radius)

    mname = "RVSphere"
    me = bpy.data.meshes.new(mname) if mname not in bpy.data.meshes else bpy.data.meshes[mname]
    bm = bmesh.new()

    # Create the sphere using Blender's radius
    bmesh.ops.create_uvsphere(bm, radius=radius, u_segments=16, v_segments=8, calc_uvs=True)
    bm.to_mesh(me)
    bm.free()

    me.materials.append(create_material(mname, COL_SPHERE, 0))
    for poly in me.polygons:
        poly.use_smooth = True

    ob = bpy.data.objects.new("Hull_Sphere", me)
    ob.location = center
    ob.scale = (1, 1, 1)  # Avoid double-scaling by setting uniform scale
    ob.display_type = "SOLID"
    ob.is_hull_sphere = True
    ob["is_hull_sphere"] = True
    bpy.context.collection.objects.link(ob)
    return ob


def import_file(filepath, scene):
    return import_hull(filepath, scene)
