"""
Name:    prm_in
Purpose: Imports Probe mesh files (.prm)

Description:
Meshes used for cars, game objects and track instances.
"""

import os
import bpy
import bmesh
import importlib
from mathutils import Vector
from . import common
from . import layers
from .layers import set_face_env
from . import rvstruct
from . import img_in
from . import w_in
from .rvstruct import PRM
from .common import to_blender_coord, to_blender_axis, FACE_QUAD, reverse_quad, FACE_ENV

# Reload imports if 'bpy' is already in locals
if "bpy" in locals():
    importlib.reload(common)
    importlib.reload(rvstruct)
    importlib.reload(img_in)

def import_file(filepath, scene):
    """
    Imports a .prm/.m file and links it to the scene as a Blender object.
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

    print(f"Imported {filename} ({len(meshes)} meshes)")

    for index, prm in enumerate(meshes):
        me = import_prm_mesh(prm, filename, filepath, scene)
        
        if len(meshes) > 1:
            # Fake user if there are multiple LoDs so they're kept when saving
            me.use_fake_user = True

            # Append a quality suffix to meshes
            bname, number = me.name.rsplit(".", 1)
            me.name = "{}|q{}".format(bname, meshes.index(prm))
            
        if meshes.index(prm) == 0:
            print("Creating Blender object for {}...".format(filename))
            
            obj = bpy.data.objects.new(filename, me)
            bpy.context.scene.collection.objects.link(obj)
            bpy.context.view_layer.objects.active = obj
            assign_uv_tex_material(obj)
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

def import_w_mesh(prm, filename, filepath, scene, world, envlist=None):
    me = bpy.data.meshes.new(name=filename)
    bm = bmesh.new()
    add_rvmesh_to_bmesh(prm, bm, me, filepath, scene, envlist)
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    materials = create_materials_for_attributes(me, bm, filename)
    if envlist is None:
        envlist = world.env_list
    apply_env_data(me, world, prm.polygons, envlist, filename)
    return me

def add_rvmesh_to_bmesh(prm, bm, me, filepath, scene, envlist=None):
    from .common import get_texture_path
    
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
            print(f"Could not create face: {e}")
            continue

        if poly.texture >= 0:
            texture_path = get_texture_path(filepath, poly.texture, scene)
            if texture_path and os.path.isfile(texture_path):
                material_name = os.path.basename(texture_path)
                material = bpy.data.materials.get(material_name)
                if not material:
                    image = bpy.data.images.load(texture_path, check_existing=True)
                    material = bpy.data.materials.new(name=material_name)
                    material.use_nodes = True
                    bsdf = material.node_tree.nodes.get('Principled BSDF')
                    tex_image = material.node_tree.nodes.new('ShaderNodeTexImage')
                    tex_image.image = image
                    material.node_tree.links.new(bsdf.inputs['Base Color'], tex_image.outputs['Color'])
                if material_name not in me.materials:
                    me.materials.append(material)
                face.material_index = me.materials.find(material_name)

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
                    
def assign_uv_tex_material(obj):
    bm = bmesh.from_edit_mesh(obj.data) if obj.mode == 'EDIT' else bmesh.new()
    bm.from_mesh(obj.data)

    uv_layer = bm.loops.layers.uv.verify()
    texnum_layer = bm.faces.layers.int.get("Texture Number") or bm.faces.layers.int.new("Texture Number")

    # Fetch .bmp materials
    bmp_materials = get_bmp_materials()

    # Assign materials based on texture number
    for face in bm.faces:
        tex_num = face[texnum_layer]
        material_key = f"texture{tex_num}.bmp"  # Construct the key as you expect it to appear
        if material_key in bmp_materials:
            material = bmp_materials[material_key]
            face.material_index = obj.data.materials.find(material.name)

    if obj.mode != 'EDIT':
        bm.to_mesh(obj.data)
        bm.free()

    obj.data.update()  # Ensure the mesh updates in the viewport
                
def get_bmp_materials():
    bmp_materials = {}
    for mat in bpy.data.materials:
        if mat.use_nodes:
            for node in mat.node_tree.nodes:
                if node.type == 'TEX_IMAGE' and node.image and node.image.filepath.lower().endswith('.bmp'):
                    bmp_materials[node.image.name] = mat
    return bmp_materials


def apply_env_data(mesh_data, world, polygons, envlist, obj_name):
    """
    Apply environment settings to a mesh in Blender by setting vertex colors and adjusting the Principled BSDF node's base color and alpha.
    """
    global w_in

    bm = bmesh.new()
    bm.from_mesh(mesh_data)

    # Ensure environment layers are added or retrieved correctly
    env_layer = bm.loops.layers.color.get("Env") or bm.loops.layers.color.new("Env")
    env_alpha_layer = bm.faces.layers.float.get("EnvAlpha") or bm.faces.layers.float.new("EnvAlpha")

    # Retrieve or create the material with environmental settings
    env_material_name = f"{obj_name}_Env"
    env_material = bpy.data.materials.get(env_material_name)
    if not env_material:
        env_material = bpy.data.materials.new(name=env_material_name)
        env_material.use_nodes = True
        nodes = env_material.node_tree.nodes
        links = env_material.node_tree.links
        bsdf = nodes.new('ShaderNodeBsdfPrincipled')
        mat_output = nodes.new('ShaderNodeOutputMaterial')
        links.new(bsdf.outputs['BSDF'], mat_output.inputs['Surface'])
    else:
        nodes = env_material.node_tree.nodes
        links = env_material.node_tree.links
        bsdf = env_material.node_tree.nodes.get('Principled BSDF')
        if not bsdf:
            bsdf = env_material.node_tree.nodes.new('ShaderNodeBsdfPrincipled')

    # Validate the number of faces and polygons
    if len(bm.faces) == len(polygons):
        for face_index, (face, poly) in enumerate(zip(bm.faces, polygons)):
            if poly.type & FACE_ENV:
                env_index = w_in.envidx % len(envlist)
                env_col = envlist[env_index]
                scaled_color = tuple(c / 255.0 for c in env_col.color)
                scaled_alpha = env_col.alpha / 255.0

                full_color = (*scaled_color, scaled_alpha)  # Ensure we have RGBA values

                for loop in face.loops:
                    loop[env_layer] = full_color  # Assign RGBA to the Env layer
                face[env_alpha_layer] = scaled_alpha

                if bsdf:
                    bsdf.inputs['Base Color'].default_value = (*scaled_color, 1)
                    bsdf.inputs['Alpha'].default_value = scaled_alpha

                face.smooth = True
                w_in.envidx += 1  # Increment the global index after processing each face

    bm.to_mesh(mesh_data)
    mesh_data.update()
    bm.free()