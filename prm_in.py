"""
Name:    prm_in
Purpose: Imports Probe mesh files (.prm)

Description:
Meshes used for cars.
"""

import os
import bpy
import bmesh
from mathutils import Vector
from . import common
from . import rvstruct
from .rvstruct import PRM
from .common import (
    to_blender_coord,
    to_blender_axis,
    FACE_QUAD,
    reverse_quad,
    FACE_ENV,
    dprint,
    set_scene_value,
)

def import_file(filepath, scene):
    """
    Imports a .prm file and links it to the scene as a Blender object.
    It also imports all LoDs of a PRM file, which can be sequentially written
    to the file. There is no indicator for it, the file end has to be checked.
    """
    meshes = []

    with open(filepath, 'rb') as file:
        filename = os.path.basename(filepath)
        file.seek(0, os.SEEK_END)
        file_end = file.tell()
        file.seek(0, os.SEEK_SET)

        while file.tell() < file_end:
            meshes.append(PRM(file))

    dprint(f"Imported {filename} ({len(meshes)} meshes)")

    for index, prm in enumerate(meshes):
        me = import_prm_mesh(prm, filename, filepath, scene)

        if len(meshes) > 1:
            # Fake user if there are multiple LoDs so they're kept when saving
            me.use_fake_user = True

            # Append a quality suffix to meshes
            bname, number = me.name.rsplit(".", 1)
            me.name = "{}|q{}".format(bname, meshes.index(prm))

        if meshes.index(prm) == 0:
            dprint("Creating Blender object for {}...".format(filename))

            obj = bpy.data.objects.new(filename, me)
            bpy.context.scene.collection.objects.link(obj)
            bpy.context.view_layer.objects.active = obj
            set_material_to_prm_col([obj])  # First assign COL
            assign_uv_tex_material(obj, filepath)  # Then assign UV_TEX

            mesh_objects = [obj for obj in scene.objects if obj.type == 'MESH']
            set_material_to_prm_texture(mesh_objects)

    return obj

def import_prm_mesh(prm, filename, filepath, scene, envlist=None):
    me = bpy.data.meshes.new(name=filename)
    bm = bmesh.new()
    add_rvmesh_to_bmesh(prm, bm, me, filepath, scene, envlist)
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    materials = create_materials_for_attributes(me, bm, filename)

    return me

def add_rvmesh_to_bmesh(prm, bm, me, filepath, scene, envlist=None):
    from .common import get_car_texture_path

    uv_layer = bm.loops.layers.uv.new("UVMap")
    vc_layer = bm.loops.layers.color.new("Col")
    env_layer = bm.loops.layers.color.new("Env")
    env_alpha_layer = bm.faces.layers.float.new("EnvAlpha")
    va_layer = bm.loops.layers.color.new("Alpha")
    texnum_layer = bm.faces.layers.int.new("Texture Number")
    type_layer = bm.faces.layers.int.new("Type")
    created_faces = []

    for vert in prm.vertices:
        position = to_blender_coord(vert.position.data)
        bm.verts.new(Vector((position[0], position[1], position[2])))

    bm.verts.ensure_lookup_table()

    for poly in prm.polygons:
        is_quad = poly.type & FACE_QUAD
        num_loops = 4 if is_quad else 3
        indices = [poly.vertex_indices[i] for i in reversed(range(num_loops))]
        verts = [bm.verts[idx] for idx in indices]
        uvs = reverse_quad(poly.uv, tri=not is_quad)
        colors = reverse_quad(poly.colors, tri=not is_quad)

        try:
            face = bm.faces.new(verts)
            created_faces.append(face)
        except ValueError as e:
            continue

        if poly.texture >= 0:
            texture_path, material_name = get_car_texture_path(filepath, poly.texture, scene)
            if texture_path and os.path.isfile(texture_path):
                material = bpy.data.materials.get(material_name)
                if not material:
                    image = bpy.data.images.load(texture_path, check_existing=True)
                    material = bpy.data.materials.new(name=material_name)
                    material.use_nodes = True
                    bsdf = material.node_tree.nodes.get('Principled BSDF')
                    tex_image = material.node_tree.nodes.new('ShaderNodeTexImage')
                    tex_image.image = image
                    material.node_tree.links.new(bsdf.inputs['Base Color'], tex_image.outputs['Color'])
                    print(f"Created new material: {material_name}")
                set_scene_value(scene, "selected_car_texture", material_name)

                if material_name not in me.materials:
                    me.materials.append(material)
                    print(f"Added material to mesh: {material_name}")
                face.material_index = me.materials.find(material_name)
            else:
                # Fallback logic for car textures
                car_texture = bpy.data.images.get('car') or bpy.data.images.get('car.bmp')
                if car_texture:
                    material_name = car_texture.name
                    material = bpy.data.materials.get(material_name)
                    if not material:
                        material = bpy.data.materials.new(name=material_name)
                        material.use_nodes = True
                        bsdf = material.node_tree.nodes.get('Principled BSDF')
                        tex_image = material.node_tree.nodes.new('ShaderNodeTexImage')
                        tex_image.image = car_texture
                        material.node_tree.links.new(bsdf.inputs['Base Color'], tex_image.outputs['Color'])
                        print(f"Created fallback material: {material_name}")
                    set_scene_value(scene, "selected_car_texture", material_name)

                    if material_name not in me.materials:
                        me.materials.append(material)
                        print(f"Added fallback material to mesh: {material_name}")
                    face.material_index = me.materials.find(material_name)
                else:
                    print("No suitable fallback texture found.")
                    print(f"No suitable texture found for face, skipping texture assignment.")

        face[type_layer] = poly.type
        face[texnum_layer] = poly.texture

        for l in range(num_loops):
            alpha = 1 - (float(colors[l].alpha) / 255)
            color = [float(c) / 255 for c in colors[l].color]

            face.loops[l][uv_layer].uv = (uvs[l].u, 1 - uvs[l].v)

            face.loops[l][vc_layer][0] = color[0]
            face.loops[l][vc_layer][1] = color[1]
            face.loops[l][vc_layer][2] = color[2]

            face.loops[l][va_layer][0] = alpha
            face.loops[l][va_layer][1] = alpha
            face.loops[l][va_layer][2] = alpha

        face.smooth = True

def create_materials_for_attributes(me, bm, obj_name):
    materials = {}
    for attr_name in ['Col', 'Alpha', 'Env']:
        mat_name = f"{obj_name}_{attr_name}"
        material = bpy.data.materials.get(mat_name)
        if not material:
            material = bpy.data.materials.new(name=mat_name)
            material.use_nodes = True
            nodes = material.node_tree.nodes
            links = material.node_tree.links

            material_output = nodes.get('Material Output') or nodes.new(type='ShaderNodeOutputMaterial')
            attr_node = nodes.new(type='ShaderNodeAttribute')
            attr_node.attribute_name = attr_name
            attr_node.attribute_type = 'GEOMETRY'

            if attr_name == 'Col':
                principled_bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
                links.new(attr_node.outputs['Color'], principled_bsdf.inputs['Base Color'])
                links.new(principled_bsdf.outputs['BSDF'], material_output.inputs['Surface'])

            elif attr_name == 'Alpha':
                principled_bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
                links.new(attr_node.outputs['Color'], principled_bsdf.inputs['Base Color'])
                links.new(principled_bsdf.outputs['BSDF'], material_output.inputs['Surface'])

            elif attr_name == 'Env':
                principled_bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
                links.new(attr_node.outputs['Color'], principled_bsdf.inputs['Base Color'])
                links.new(principled_bsdf.outputs['BSDF'], material_output.inputs['Surface'])

        materials[attr_name] = material

    return materials

def assign_uv_tex_material(obj, filepath):
    bm = bmesh.from_edit_mesh(obj.data) if obj.mode == 'EDIT' else bmesh.new()
    bm.from_mesh(obj.data)

    uv_layer = bm.loops.layers.uv.verify()

    # Ensure the mesh is updated in the viewport
    if obj.mode != 'EDIT':
        bm.to_mesh(obj.data)
        bm.free()

    obj.data.update()

def set_material_to_prm_texture(mesh_objects):
    """Sets the material to Texture (UV_TEX) for all mesh objects."""
    if not mesh_objects:
        print("No mesh objects selected for material assignment.")
        return

    scene = bpy.context.scene
    scene.material_choice = 'UV_TEX'  # <-- now on Scene

    # Select only the meshes we care about
    bpy.ops.object.select_all(action='DESELECT')
    for obj in mesh_objects:
        if obj.type == 'MESH':
            obj.select_set(True)

    # Make the first mesh active so the operator has a valid context
    bpy.context.view_layer.objects.active = mesh_objects[0]

    # Run the import/export material assigner once over all selected meshes
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.object.assign_materials_impexp()
    bpy.ops.object.mode_set(mode='OBJECT')


def set_material_to_prm_col(mesh_objects):
    """Sets the material to Vertex Colour (COL) for all mesh objects."""
    if not mesh_objects:
        print("No mesh objects selected for material assignment.")
        return

    scene = bpy.context.scene
    scene.material_choice = 'COL'  # <-- now on Scene

    bpy.ops.object.select_all(action='DESELECT')
    for obj in mesh_objects:
        if obj.type == 'MESH':
            obj.select_set(True)

    bpy.context.view_layer.objects.active = mesh_objects[0]

    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.object.assign_materials_impexp()
    bpy.ops.object.mode_set(mode='OBJECT')