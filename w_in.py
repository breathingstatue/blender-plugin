"""
Name:    w_in
Purpose: Imports Re-Volt level world files (.w)

Description:
World files contain meshes, optimization data, and texture animations.
"""

import os
import bpy
import bmesh
from mathutils import Color, Vector
from . import common
from . import rvstruct
from . import img_in
from . import prm_in

from .rvstruct import World
from .common import int_to_texture, msg_box, to_blender_coord, COL_BBOX, create_material, to_blender_scale, COL_BCUBE, COL_CUBE

if "bpy" in locals():
    import importlib
    importlib.reload(common)
    importlib.reload(rvstruct)
    importlib.reload(img_in)
    importlib.reload(prm_in)
   
# Define envidx here
envidx = 0

def import_file(filepath, scene):
    """
    Imports a .w file and links it to the scene as a Blender object.
    """
    from .prm_in import import_w_mesh
    global envidx
    scene = bpy.context.scene
    envidx = 0

    with open(filepath, 'rb') as file:
        filename = os.path.basename(filepath)
        world = World(file)

    meshes = world.meshes
    print("Imported {} ({} meshes)".format(filename, len(meshes)))

    if scene.w_parent_meshes:
        main_w = bpy.data.objects.new(bpy.path.basename(filepath), None)
        bpy.context.scene.collection.objects.link(main_w)

    for rvmesh in meshes:
        me = import_w_mesh(rvmesh, os.path.basename(filepath),filepath, scene, world, envlist=None)
        ob = bpy.data.objects.new(os.path.basename(filepath), me)
        bpy.context.collection.objects.link(ob)
        bpy.context.view_layer.objects.active = ob

        if scene.w_parent_meshes:
            ob.parent = main_w

        if scene.w_import_bound_boxes:
            bbox = create_bound_box(scene, rvmesh.bbox, os.path.basename(filepath))
            bbox["is_bbox"] = True
            bbox.parent = ob

        if scene.w_import_cubes:
            radius = rvmesh.bound_ball_radius
            center = rvmesh.bound_ball_center.data
            cube = create_cube(scene, "CUBE", center, radius, os.path.basename(filepath))
            cube["is_cube"] = True
            cube.parent = ob

    if scene.w_import_big_cubes:
        for cube in world.bigcubes:
            radius = cube.size
            center = cube.center.data
            bcube = create_cube(scene, "BIGCUBE", center, radius, os.path.basename(filepath))
            bcube["bcube_mesh_indices"] = ", ".join([str(c) for c in cube.mesh_indices])
            bcube["is_bcube"] = True
            if scene.w_parent_meshes:
                bcube.parent = main_w

    texture_animations = [animation.as_dict() for animation in world.animations]
    scene.texture_animations = str(texture_animations)
    scene.ta_max_slots = world.animation_count

def create_bound_box(scene, bbox, filename):
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
        (bm.verts[0], bm.verts[1], bm.verts[3], bm.verts[2]),
        (bm.verts[6], bm.verts[7], bm.verts[5], bm.verts[4]),
        (bm.verts[0], bm.verts[2], bm.verts[6], bm.verts[4]),
        (bm.verts[5], bm.verts[7], bm.verts[3], bm.verts[1]),
        (bm.verts[4], bm.verts[5], bm.verts[1], bm.verts[0]),
        (bm.verts[2], bm.verts[3], bm.verts[7], bm.verts[6])
    ]

    for f in faces:
        bm.faces.new(f)

    bm.normal_update()
    bm.to_mesh(me)
    bm.free()

    mat = bpy.data.materials.get("RVBBox")
    if not mat:
        if isinstance(COL_BBOX, Color):
            diffuse = (COL_BBOX.r, COL_BBOX.g, COL_BBOX.b)
        else:
            diffuse = COL_BBOX
        mat = create_material("RVBBox", diffuse, 0.3)
    me.materials.append(mat)

    ob = bpy.data.objects.new("RVBBox_{}".format(filename), me)
    bpy.context.collection.objects.link(ob)
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
        bmesh.ops.create_cube(bm, size=2, calc_uvs=True)
        bm.to_mesh(me)
        bm.free()
        if isinstance(col, Color):
            diffuse = (col.r, col.g, col.b)
        else:
            diffuse = col
        me.materials.append(create_material(mname, diffuse, 0.3))
        for poly in me.polygons:
            poly.use_smooth = True
    else:
        me = bpy.data.meshes[mname]

    ob = bpy.data.objects.new("{}_{}".format(mname, filename), me)
    bpy.context.collection.objects.link(ob)
    ob.location = center
    ob.scale = (radius, radius, radius)
    ob.display_type = "SOLID"
    ob.show_wire = True

    return ob