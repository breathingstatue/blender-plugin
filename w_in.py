"""
Name:    w_in
Purpose: Imports Re-Volt level world files (.w)

Description:
World files contain meshes, optimization data and texture animations.

"""

import os
import bpy
import bmesh
import json
from mathutils import Vector
from . import common, rvstruct, img_in, prm_in
from .rvstruct import World
from .common import *
from .prm_in import import_mesh

# Reload modules if already loaded
if "bpy" in locals():
    import imp
    imp.reload(common)
    imp.reload(rvstruct)
    imp.reload(img_in)
    imp.reload(prm_in)

def import_file(filepath, scene):
    with open(filepath, 'rb') as file:
        filename = os.path.basename(filepath)
        world = World(file)

    meshes = world.meshes
    print(f"Imported {filename} with {len(meshes)} meshes")

    main_w = None
    if scene.get('w_parent_meshes', False):
        main_w = bpy.data.objects.new(filename, None)
        scene.collection.objects.link(main_w)

    for index, rvmesh in enumerate(meshes):
        mesh_name = filename if index == 0 else f"{filename}.{str(index).zfill(3)}"
        me = import_mesh(rvmesh, scene, filepath, world.env_list)
        ob = bpy.data.objects.new(mesh_name, me)
        scene.collection.objects.link(ob)

        if main_w:
            ob.parent = main_w

        if scene.get('w_import_bound_boxes', False):
            bbox = create_bound_box(scene, rvmesh.bbox, mesh_name)
            bbox.parent = ob if not main_w else main_w
            bbox["is_bbox"] = True

        if scene.get('w_import_cubes', False):
            center = rvmesh.bound_ball_center.data
            radius = rvmesh.bound_ball_radius
            cube = create_cube(scene, "CUBE", center, radius, mesh_name)
            cube.parent = ob if not main_w else main_w
            cube["is_cube"] = True

    # Import big cubes - should be outside the mesh loop
    if scene.get('w_import_big_cubes', False):
        if world.bigcubes:
            cube_data = world.bigcubes[0]
            radius = cube_data.size
            center = cube_data.center.data
            bcube = create_cube(scene, "BIGCUBE", center, radius, filename)
            if main_w:
                bcube.parent = main_w
            bcube["is_bcube"] = True

    scene.texture_animations = json.dumps([a.as_dict() for a in world.animations])
    scene.ta_max_slots = world.animation_count

    # Clears the used texture paths
    # # global textures
    # textures = {}
    # print("Cleared textures...")


def create_bound_box(scene, bbox, filename):
    # Creates a new mesh and bmesh
    me = bpy.data.meshes.new("RVBBox_{}".format(filename))
    bm = bmesh.new()

    coords = [
        to_blender_coord((bbox.xlo, bbox.ylo, bbox.zhi)),
        to_blender_coord((bbox.xhi, bbox.ylo, bbox.zhi)),
        to_blender_coord((bbox.xlo, bbox.yhi, bbox.zhi)),
        to_blender_coord((bbox.xhi, bbox.yhi, bbox.zhi)),
        to_blender_coord((bbox.xlo, bbox.ylo, bbox.zlo)),
        to_blender_coord((bbox.xhi, bbox.ylo, bbox.zlo)),
        to_blender_coord((bbox.xlo, bbox.yhi, bbox.zlo)),
        to_blender_coord((bbox.xhi, bbox.yhi, bbox.zlo))
    ]
    for co in coords:
        bm.verts.new(co)
    bm.verts.ensure_lookup_table()

    faces = [
        # Front
        (bm.verts[0], bm.verts[1], bm.verts[3], bm.verts[2]),
        # Back
        (bm.verts[6], bm.verts[7], bm.verts[5], bm.verts[4]),
        # Left
        (bm.verts[0], bm.verts[2], bm.verts[6], bm.verts[4]),
        # Right
        (bm.verts[5], bm.verts[7], bm.verts[3], bm.verts[1]),
        # Top
        (bm.verts[4], bm.verts[5], bm.verts[1], bm.verts[0]),
        # Bottom
        (bm.verts[2], bm.verts[3], bm.verts[7], bm.verts[6])
    ]

    # Creates faces of the bbox
    for f in faces:
        bm.faces.new(f)

    bm.normal_update()
    bm.to_mesh(me)
    bm.free()

    # Gets or creates a transparent material for the boxes
    mat = bpy.data.materials.get("RVBBox")
    if not mat:
        mat = create_material("RVBBox", COL_BBOX, 0.3)
    me.materials.append(mat)

    ob = bpy.data.objects.new("RVBBox_{}".format(filename), me)
    bpy.context.collection.objects.link(ob)

    # Makes the object transparent
    ob.show_transparent = True
    ob.display_type = "SOLID"
    ob.show_wire = True

    return ob


def create_cube(scene, sptype, center, radius, filename):
    if sptype == "CUBE":
        mname = "RVCube"
        col = COL_CUBE
    elif sptype == "BIGCUBE":
        mname = "RVBigCube"
        col = COL_BCUBE

    center = to_blender_coord(center)
    radius = to_blender_scale(radius)
    if mname not in bpy.data.meshes:
        me = bpy.data.meshes.new(mname)
        bm = bmesh.new()
        # Creates a box
        bmesh.ops.create_cube(bm, size=2, calc_uvs=True)
        bm.to_mesh(me)
        bm.free()
        # Creates a transparent material for the object
        me.materials.append(create_material(mname, col, 0.3))
        # Makes polygons smooth
        for poly in me.polygons:
            poly.use_smooth = True
    else:
        me = bpy.data.meshes[mname]

    # Links the object and sets position and scale
    ob = bpy.data.objects.new("{}_{}".format(mname, filename), me)
    bpy.context.collection.objects.link(ob)
    ob.location = center
    ob.scale = (radius, radius, radius)

    # Makes the object transparent
    ob.show_transparent = True
    ob.display_type = "SOLID"
    ob.show_wire = True

    return ob
