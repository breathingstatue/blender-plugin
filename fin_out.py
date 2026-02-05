"""
Name:    fin_out
Purpose: Exports Re-Volt instance files (.fin)

Description:
Exports Instance files.
"""

import os
import re
import bpy
import bmesh
from . import common, rvstruct, prm_out_for_fin
from .rvstruct import Instances, Instance, Vector, Matrix, Color
from .common import (
    to_revolt_coord, to_or_matrix, clean_model_base_name,
    FIN_SET_MODEL_RGB, FIN_ENV, FIN_HIDE, FIN_NO_MIRROR, FIN_NO_LIGHTS,
    FIN_NO_CAMERA_COLLISION, FIN_NO_OBJECT_COLLISION, dprint, msg_box
)

if "bpy" in locals():
    import importlib
    importlib.reload(common)
    importlib.reload(rvstruct)
    importlib.reload(prm_out_for_fin)

def export_file(filepath, scene):
    dprint("Starting FIN export...")
    fin = rvstruct.Instances()

    def _is_instance(obj):
        return getattr(obj, "is_instance", obj.get("is_instance", False))

    bpy.ops.object.mode_set(mode='OBJECT')

    mesh_objects = [
        obj for obj in bpy.data.objects
        if obj.type == 'MESH' and _is_instance(obj)
    ]
    if not mesh_objects:
        msg_box("No mesh instance objects found for export.", icon="ERROR")
        return

    dprint(f"Exporting {len(mesh_objects)} FIN instances")

    assign_textures_and_vc_by_texnum(mesh_objects, scene)

    exported_mesh_names = set()
    folder = os.path.dirname(filepath)

    for obj in mesh_objects:
        mesh_full_name = os.path.splitext(obj.name.lower())[0]
        mesh_base_name = clean_model_base_name(mesh_full_name)
        model_fname = f"{mesh_base_name}.prm"
        export_path = os.path.join(folder, model_fname)

        if mesh_base_name not in exported_mesh_names:
            dprint(f"Exporting model: {os.path.basename(export_path)}")
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            prm_out_for_fin.export_file(export_path, scene)
            exported_mesh_names.add(mesh_base_name)
        else:
            dprint(f"Skipping duplicate model export for: {mesh_base_name}")

        instance_name = mesh_base_name[:8].upper()

        instance = Instance()
        instance.name = instance_name + "\x00"

        fin_col = getattr(obj, "fin_col", obj.get("fin_col", [0.5, 0.5, 0.5]))
        instance.color = (
            int(fin_col[0] * 255) - 128,
            int(fin_col[1] * 255) - 128,
            int(fin_col[2] * 255) - 128,
        )

        fin_envcol = getattr(obj, "fin_envcol", obj.get("fin_envcol", [0.5, 0.5, 0.5, 1.0]))
        instance.env_color = Color(
            color=(int(fin_envcol[0] * 255),
                   int(fin_envcol[1] * 255),
                   int(fin_envcol[2] * 255)),
            alpha=int((1 - fin_envcol[3]) * 255)
        )

        instance.position = Vector(data=to_revolt_coord(obj.location))
        instance.or_matrix = Matrix()
        instance.or_matrix.data = to_or_matrix(obj.matrix_world)

        def _flag(obj, name):
            return getattr(obj, name, obj.get(name, False))

        instance.flag = 0
        if _flag(obj, "fin_env"):
            instance.flag |= FIN_ENV
        if _flag(obj, "fin_model_rgb"):
            instance.flag |= FIN_SET_MODEL_RGB
        if _flag(obj, "fin_hide"):
            instance.flag |= FIN_HIDE
        if _flag(obj, "fin_no_mirror"):
            instance.flag |= FIN_NO_MIRROR
        if _flag(obj, "fin_no_lights"):
            instance.flag |= FIN_NO_LIGHTS
        if _flag(obj, "fin_no_cam_coll"):
            instance.flag |= FIN_NO_CAMERA_COLLISION
        if _flag(obj, "fin_no_obj_coll"):
            instance.flag |= FIN_NO_OBJECT_COLLISION

        fin.instances.append(instance)

    fin.instance_count = len(fin.instances)

    dprint("Writing FIN file...")
    with open(filepath, "wb") as fd:
        fin.write(fd)
    dprint(f"FIN export complete: {len(fin.instances)} instances -> {filepath}")

def assign_material_to_meshes(mesh_objects, material_type, scene=None):
    if not mesh_objects:
        return

    scene = scene or bpy.context.scene

    if not hasattr(scene, "material_choice"):
        return

    previous_choice = scene.material_choice
    scene.material_choice = material_type

    bpy.ops.object.select_all(action='DESELECT')
    for obj in mesh_objects:
        obj.select_set(True)

    bpy.context.view_layer.objects.active = mesh_objects[0]

    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    bpy.ops.object.assign_materials_impexp()

    if previous_choice is not None:
        scene.material_choice = previous_choice

def assign_textures_and_vc_by_texnum(mesh_objects, scene=None):
    """Ensure instance meshes have up-to-date texture/VC materials before export."""
    if not mesh_objects:
        return

    scene = scene or bpy.context.scene
    previous_choice = getattr(scene, "material_choice", None) if scene else None

    try:
        assign_material_to_meshes(mesh_objects, 'TEX_VC', scene=scene)
    finally:
        if scene and previous_choice is not None:
            scene.material_choice = previous_choice

# Remaining helper functions unchanged from original implementation...
