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

if "bpy" in locals():
    import importlib
    importlib.reload(common)
    importlib.reload(rvstruct)
    importlib.reload(img_in)
    importlib.reload(prm_in)
    
# Importing specific classes and functions
from .common import to_blender_coord, to_blender_scale, COL_BBOX, COL_BCUBE, COL_CUBE, create_material
from .rvstruct import World
from .prm_in import import_mesh

def import_file(filepath, scene, context):
    """
    Imports a .w file and links it to the scene as a Blender object.
    """

    props = scene.revolt

    with open(filepath, 'rb') as file:
        filename = os.path.basename(filepath)
        world = World(file)

    meshes = world.meshes
    print(f"Imported {filename} ({len(meshes)} meshes)")

    # Creates an empty object to parent meshes to if enabled in settings
    if props.w_parent_meshes:
        main_w = bpy.data.objects.new(os.path.basename(filename), None)
        context.collection.objects.link(main_w)

    for rvmesh in meshes:
        me = import_mesh(rvmesh, scene, filepath, world.env_list)
        ob = bpy.data.objects.new(filename, me)
        context.collection.objects.link(ob)
        context.view_layer.objects.active = ob

        if props.w_parent_meshes:
            ob.parent = main_w

        if props.w_import_bound_boxes:
            bbox = create_bound_box(scene, rvmesh.bbox, filename)
            # This should now adjust the visibility or collection assignment
            bbox.revolt.is_bbox = True
            bbox.parent = ob

        if props.w_import_cubes:
            cube = create_cube(scene, "CUBE", rvmesh.bound_ball_center.data, rvmesh.bound_ball_radius, filename)
            cube.revolt.is_cube = True
            cube.parent = ob

    if props.w_import_big_cubes:
        for cube in world.bigcubes:
            bcube = create_cube(scene, "BIGCUBE", cube.center.data, cube.size, filename)
            bcube.revolt.bcube_mesh_indices = ", ".join(map(str, cube.mesh_indices))
            bcube.revolt.is_bcube = True
            if props.w_parent_meshes:
                bcube.parent = main_w

    props.texture_animations = str([a.as_dict() for a in world.animations])
    props.ta_max_slots = world.animation_count

def create_bound_box(scene, bbox, filename):
    me = bpy.data.meshes.new(f"RVBBox_{filename}")
    bm = bmesh.new()

    # Bounding box vertex coordinates
    coords = [to_blender_coord(coord) for coord in [(bbox.xlo, bbox.ylo, bbox.zhi), (bbox.xhi, bbox.ylo, bbox.zhi),
                                                    (bbox.xlo, bbox.yhi, bbox.zhi), (bbox.xhi, bbox.yhi, bbox.zhi),
                                                    (bbox.xlo, bbox.ylo, bbox.zlo), (bbox.xhi, bbox.ylo, bbox.zlo),
                                                    (bbox.xlo, bbox.yhi, bbox.zlo), (bbox.xhi, bbox.yhi, bbox.zlo)]]

    for co in coords:
        bm.verts.new(co)
    bm.verts.ensure_lookup_table()

    # Bounding box faces
    face_indices = [(0, 1, 3, 2), (6, 7, 5, 4), (0, 2, 6, 4), (5, 7, 3, 1), (4, 5, 1, 0), (2, 3, 7, 6)]
    for indices in face_indices:
        bm.faces.new([bm.verts[i] for i in indices])

    bm.normal_update()
    bm.to_mesh(me)
    bm.free()

    # Get or create a transparent material for the bounding box
    mat = bpy.data.materials.get("RVBBox") or create_material("RVBBox", COL_BBOX, 0.3)
    me.materials.append(mat)

    ob = bpy.data.objects.new(f"RVBBox_{filename}", me)
    bpy.context.collection.objects.link(ob)

    # Set object properties
    ob.show_transparent = True
    ob.display_type = 'SOLID'
    ob.show_wire = True

    return ob

def create_cube(scene, sptype, center, radius, filename):
    mname = "RVCube" if sptype == "CUBE" else "RVBigCube"
    col = COL_CUBE if sptype == "CUBE" else COL_BCUBE

    center = to_blender_coord(center)
    radius = to_blender_scale(radius)
    me = bpy.data.meshes.get(mname) or bpy.data.meshes.new(mname)

    if not me.polygons:  # Create cube mesh if not already existing
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=2.0)
        bm.to_mesh(me)
        bm.free()
        me.materials.append(create_material(mname, col, 0.3))

    ob = bpy.data.objects.new(f"{mname}_{filename}", me)
    bpy.context.collection.objects.link(ob)
    ob.location = center
    ob.scale = (radius, radius, radius)
    ob.show_transparent = True
    ob.display_type = 'SOLID'
    ob.show_wire = True

    return ob
