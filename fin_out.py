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

    assign_textures_and_vc_by_texnum(mesh_objects, scene)

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
    """Assign materials to given meshes using the global Scene material_choice."""
    if not mesh_objects:
        return

    scene = bpy.context.scene

    # Make sure the Scene has the property
    if not hasattr(scene, "material_choice"):
        print("[WARN] Scene has no 'material_choice' property; cannot assign materials.")
        return

    # Set the global choice (e.g. 'UV_TEX', 'COL', etc.)
    scene.material_choice = material_type

    # Select target meshes
    bpy.ops.object.select_all(action='DESELECT')
    for obj in mesh_objects:
        obj.select_set(True)

    # Ensure a valid active object
    bpy.context.view_layer.objects.active = mesh_objects[0]

    # Ensure we are in OBJECT mode before running the operator
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    # The operator will now read scene.material_choice internally
    bpy.ops.object.assign_materials_impexp()

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

def assign_textures_and_vc_by_texnum(mesh_objects, scene):
    """
    For each mesh object:
      - Read per-face 'Texture Number' (int) layer
      - texnum >= 0  -> assign the corresponding <base><suffix>.bmp material
      - texnum == -1 -> assign a Vertex Colour material (uses 'Col' and 'Alpha' attributes)
    Runs fully in OBJECT mode; no operators or active object required.
    """

    # Cache BMP materials once: image.name -> material
    def collect_bmp_materials():
        m = {}
        for mat in bpy.data.materials:
            if not mat.use_nodes:
                continue
            for node in mat.node_tree.nodes:
                if node.type == 'TEX_IMAGE' and node.image:
                    img_name = os.path.basename(node.image.name).lower()
                    if img_name.endswith('.bmp'):
                        m[img_name] = mat
        return m

    # base: prefer FIN base, then scene level, then cleaned object name
    def resolve_base(obj):
        if obj.get("is_instance") and "fin_texture_base" in obj:
            return str(obj["fin_texture_base"]).strip().lower()
        if "level_texture_base" in scene and scene["level_texture_base"]:
            return os.path.splitext(scene["level_texture_base"].strip().lower())[0]
        name = obj.name.lower()
        name = os.path.splitext(name)[0]
        # strip trailing .001 style suffixes
        while name and name[-1].isdigit():
            name = name[:-1]
        return ''.join(ch for ch in name if ch.isalnum() or ch in ('_', '-'))

    # 0->'a', 1->'b', ..., 25->'z', 26->'aa', ...
    def int_to_suffix(tex_num: int) -> str:
        if tex_num < 0:
            return ""
        s = ""
        n = tex_num
        # ‘a’ = 0 in your pipeline
        while True:
            s = chr((n % 26) + 97) + s
            n = n // 26 - 1
            if n < 0:
                break
        return s

    def get_or_create_vc_material(obj) -> bpy.types.Material:
        """Per-object VC material (uses Col + Alpha)."""
        vc_name = f"{obj.name.split('.')[0]}_Col"
        mat = bpy.data.materials.get(vc_name)
        if mat:
            return mat
        mat = bpy.data.materials.new(vc_name)
        mat.use_nodes = True
        nt = mat.node_tree
        nt.nodes.clear()

        attr_col = nt.nodes.new('ShaderNodeAttribute')
        attr_col.attribute_name = 'Col'
        attr_col.attribute_type = 'GEOMETRY'

        attr_a = nt.nodes.new('ShaderNodeAttribute')
        attr_a.attribute_name = 'Alpha'
        attr_a.attribute_type = 'GEOMETRY'

        sep = nt.nodes.new('ShaderNodeSeparateXYZ')

        bsdf = nt.nodes.new('ShaderNodeBsdfPrincipled')
        outp = nt.nodes.new('ShaderNodeOutputMaterial')

        ln = nt.links
        ln.new(attr_col.outputs['Color'], bsdf.inputs['Base Color'])
        ln.new(attr_a.outputs['Color'], sep.inputs['Vector'])
        ln.new(sep.outputs['X'], bsdf.inputs['Alpha'])
        ln.new(bsdf.outputs['BSDF'], outp.inputs['Surface'])

        # (Optional) make alpha visible in viewport rendering modes
        try:
            mat.blend_method = 'BLEND'
            mat.shadow_method = 'CLIP'
            mat.use_backface_culling = False
        except Exception:
            pass

        return mat

    bmp_mats = collect_bmp_materials()

    for obj in mesh_objects:
        if obj.type != 'MESH' or not obj.data:
            continue

        base = resolve_base(obj)
        me = obj.data

        bm = bmesh.new()
        bm.from_mesh(me)

        texnum_layer = bm.faces.layers.int.get("Texture Number")
        if not texnum_layer:
            # nothing to do if no layer
            bm.free()
            continue

        # ensure VC material is available and in slot list
        vc_mat = get_or_create_vc_material(obj)
        if vc_mat.name not in me.materials:
            me.materials.append(vc_mat)
        vc_idx = me.materials.find(vc_mat.name)

        for face in bm.faces:
            tnum = face[texnum_layer]
            if tnum is None:
                tnum = -1

            if tnum < 0:
                # Vertex Colour face
                face.material_index = vc_idx
                continue

            # Textured face -> lookup <base><suffix>.bmp
            suffix = int_to_suffix(int(tnum))
            img_key = f"{base}{suffix}.bmp"
            mat = bmp_mats.get(img_key)

            # Fallbacks: direct material by name (with/without .bmp)
            if not mat:
                mat = bpy.data.materials.get(img_key) or bpy.data.materials.get(img_key[:-4])

            if not mat:
                # If we can’t find a material, leave current material as-is
                # (exporter will still write the correct texnum)
                continue

            if mat.name not in me.materials:
                me.materials.append(mat)
            face.material_index = me.materials.find(mat.name)

        bm.to_mesh(me)
        me.update()
        bm.free()