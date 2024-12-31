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


import os
import subprocess
import re
import bpy
import bmesh
import importlib
from . import common, rvstruct

if "bpy" in locals():
    importlib.reload(common)
    importlib.reload(rvstruct)

from .common import COL_SPHERE, COL_HULL, to_blender_coord, to_blender_scale, create_material
from .rvstruct import Hull
from mathutils import Vector


def import_hull(filepath, scene):
    with open(filepath, "rb") as fd:
        hull = Hull(fd)

    script_dir = os.path.dirname(os.path.realpath(__file__))
    qhull_in = os.path.join(script_dir, "hull", "qhull_in.txt")
    qhull_out = os.path.join(script_dir, "hull", "qhull_out.txt")
    qhull_exe = os.path.join(script_dir, "hull", "qhull.exe") if os.name == "nt" else "qhull"

    filename = os.path.basename(filepath)

    for chull in hull.chulls:
        offset = rvstruct.Vector(data=(
            (chull.bbox.xlo + chull.bbox.xhi) / 2,
            (chull.bbox.ylo + chull.bbox.yhi) / 2,
            (chull.bbox.zlo + chull.bbox.zhi) / 2
        ))
        chull.bbox_offset += offset
    
        # Apply offset to shift the bounding box
        chull.bbox.xlo -= offset[0]
        chull.bbox.xhi -= offset[0]
        chull.bbox.ylo -= offset[1]
        chull.bbox.yhi -= offset[1]
        chull.bbox.zlo -= offset[2]
        chull.bbox.zhi -= offset[2]

        bm = bmesh.new()
        me = bpy.data.meshes.new(filename)

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
        ob = bpy.data.objects.new(filename, me)
        ob.show_transparent = True
        ob.show_wire = True
        ob.is_hull_convex = True
        ob["is_hull_convex"] = True
        bpy.context.collection.objects.link(ob)

    for sphere in hull.interior.spheres:
        create_sphere(scene, sphere.center, sphere.radius, filename)


def create_sphere(scene, center, radius, filename):
    center = to_blender_coord(center)
    radius = to_blender_scale(radius)
    mname = "RVSphere"
    
    me = bpy.data.meshes.new(mname) if mname not in bpy.data.meshes else bpy.data.meshes[mname]
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, radius=radius, u_segments=16, v_segments=8, calc_uvs=True)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(create_material(mname, COL_SPHERE, 0))

    ob = bpy.data.objects.new("Hull_Sphere", me)
    ob.location = center
    ob.scale = (radius, radius, radius)
    ob.display_type = "SOLID"
    ob.is_hull_sphere = True
    ob["is_hull_sphere"] = True
    bpy.context.collection.objects.link(ob)
    return ob


def import_file(filepath, scene):
    return import_hull(filepath, scene)

def import_chull(chull, scene, filename):
    #unused
    print("Importing convex hull...")

    me = bpy.data.meshes.new(filename)
    bm = bmesh.new()

    print("verts:", len(chull.vertices))
    print("edges:", len(chull.edges))
    print("faces:", len(chull.faces))

    for vert in chull.vertices:
        position = to_blender_coord(vert)
        print("vertex position:", position)

        # Creates vertices
        bm.verts.new(Vector((position[0], position[1], position[2])))

        bm.verts.ensure_lookup_table()

    for edge in chull.edges:
        e = bm.edges.new([bm.verts[edge[0]], bm.verts[edge[1]]])
        if e is None:
            print("could not create edge")
    for face in chull.faces:
        print("FACE-----------------")
        verts = []
        for vert in chull.vertices:
            if face.contains_vertex(vert):
                position = to_blender_coord(vert)
                # Creates vertices
                v = bm.verts.new(Vector((position[0], position[1], position[2])))
                verts.append(v)
        if len(verts) > 2:
            # bm.faces.append(bmesh.ops.contextual_create(bm, verts, 0, False)["faces"])
            bmesh.ops.contextual_create(bm, geom=verts, use_smooth=True)
            # bm.faces.new(verts)

    bpy.context.collection.objects.link(ob)
    context.view_layer.objects.active = ob

    # Converts the bmesh back to a mesh and frees resources
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()

def create_sphere(scene, center, radius, filename):
    col = COL_SPHERE
    center = to_blender_coord(center)
    radius = to_blender_scale(radius)
    mname = "RVSphere"
    if mname not in bpy.data.meshes:
        me = bpy.data.meshes.new(mname)
        bm = bmesh.new()
        # Creates a UV sphere
        bmesh.ops.create_uvsphere(bm, radius=radius, u_segments=16, v_segments=8, calc_uvs=True)
        bm.to_mesh(me)
        bm.free()
        # Creates a transparent material for the object
        me.materials.append(create_material(mname, col, 0))
        # Makes polygons smooth
        for poly in me.polygons:
            poly.use_smooth = True
    else:
        me = bpy.data.meshes[mname]

    # Links the object and sets position and scale
    ob = bpy.data.objects.new(f"hull_sphere", me)
    bpy.context.collection.objects.link(ob)
    ob.location = center
    ob.scale = (radius, radius, radius)
    ob.display_type = "SOLID"
    ob.is_hull_sphere = True
    return ob

def import_file(filepath, scene):
    return import_hull(filepath, scene)
