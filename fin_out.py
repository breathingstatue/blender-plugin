"""
Name:    fin_out
Purpose: Exports Re-Volt instance files (.fin)

Description:
Exports Instance files.
"""

import os
import re
import bpy
from . import common, rvstruct, prm_out_for_fin
from .rvstruct import Instances, Instance, Vector, Matrix, Color
from .common import (
    to_revolt_coord, to_or_matrix, clean_model_base_name,
    FIN_SET_MODEL_RGB, FIN_ENV, FIN_HIDE, FIN_NO_MIRROR, FIN_NO_LIGHTS,
    FIN_NO_CAMERA_COLLISION, FIN_NO_OBJECT_COLLISION
)

if "bpy" in locals():
    import importlib
    importlib.reload(common)
    importlib.reload(rvstruct)
    importlib.reload(prm_out_for_fin)

def export_file(filepath, scene):
    print("Starting export...")
    fin = rvstruct.Instances()

    bpy.ops.object.mode_set(mode='OBJECT')
    print("Switched to Object Mode")

    mesh_objects = [obj for obj in bpy.data.objects if obj.type == 'MESH' and obj.get("is_instance", False)]
    if not mesh_objects:
        print("No mesh objects available for export.")
        return

    print(f"Found {len(mesh_objects)} mesh objects")

    assign_material_to_meshes(mesh_objects, 'COL')
    assign_material_to_meshes(mesh_objects, 'UV_TEX')

    exported_mesh_names = set()
    folder = os.path.dirname(filepath)

    for obj in mesh_objects:
        mesh_full_name = os.path.splitext(obj.name.lower())[0]
        mesh_base_name = clean_model_base_name(mesh_full_name)
        model_fname = f"{mesh_base_name}.prm"
        export_path = os.path.join(folder, model_fname)

        if mesh_base_name not in exported_mesh_names:
            print(f"Exporting model: {os.path.basename(export_path)}")
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            prm_out_for_fin.export_file(export_path, scene)
            exported_mesh_names.add(mesh_base_name)
        else:
            print(f"Skipping duplicate export for: {mesh_base_name}")

        instance_name = mesh_base_name[:8].upper()

        instance = Instance()
        instance.name = instance_name + "\x00"

        fin_col = obj.get("fin_col", [0.5, 0.5, 0.5])
        instance.color = (
            int(fin_col[0] * 255) - 128,
            int(fin_col[1] * 255) - 128,
            int(fin_col[2] * 255) - 128,
        )

        fin_envcol = obj.get("fin_envcol", [0.5, 0.5, 0.5, 1.0])
        instance.env_color = Color(
            color=(int(fin_envcol[0] * 255),
                   int(fin_envcol[1] * 255),
                   int(fin_envcol[2] * 255)),
            alpha=int((1 - fin_envcol[3]) * 255)
        )

        instance.position = Vector(data=to_revolt_coord(obj.location))
        instance.or_matrix = Matrix()
        instance.or_matrix.data = to_or_matrix(obj.matrix_world)

        instance.flag = 0
        if obj.get("fin_env", False):
            instance.flag |= FIN_ENV
        if obj.get("fin_model_rgb", False):
            instance.flag |= FIN_SET_MODEL_RGB
        if obj.get("fin_hide", False):
            instance.flag |= FIN_HIDE
        if obj.get("fin_no_mirror", False):
            instance.flag |= FIN_NO_MIRROR
        if obj.get("fin_no_lights", False):
            instance.flag |= FIN_NO_LIGHTS
        if obj.get("fin_no_cam_coll", False):
            instance.flag |= FIN_NO_CAMERA_COLLISION
        if obj.get("fin_no_obj_coll", False):
            instance.flag |= FIN_NO_OBJECT_COLLISION

        fin.instances.append(instance)

    fin.instance_count = len(fin.instances)

    print("Writing to FIN file...")
    with open(filepath, "wb") as fd:
        fin.write(fd)
    print(f"Export complete: {len(fin.instances)} instances exported to {filepath}")

def assign_material_to_meshes(mesh_objects, material_type):
    if not mesh_objects:
        return
    bpy.ops.object.select_all(action='DESELECT')
    for obj in mesh_objects:
        obj.select_set(True)
        obj.data.material_choice = material_type
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.object.assign_materials_impexp()
    bpy.ops.object.mode_set(mode='OBJECT')

def get_base_name_for_layers(obj):
    if obj.get("is_instance") and "fin_texture_base" in obj:
        return obj["fin_texture_base"], ''
    name = re.sub(r'[\._-]\d+$', '', obj.name.lower())
    for ext in ('.prm', '.w'):
        if name.endswith(ext):
            name = name[:-len(ext)]
            break
    return name, ''

def texture_available(prefix, use_suffixing):
    for img in bpy.data.images:
        name = img.name.lower()
        if name.startswith("render") or name.startswith("viewer"):
            continue
        base = os.path.splitext(name)[0]
        if use_suffixing and base.startswith(prefix):
            return True
        if not use_suffixing and base == prefix or name == prefix or name == prefix + ".bmp":
            return True
    return False