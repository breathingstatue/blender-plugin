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
from mathutils import Color, Vector
from . import common
from . import rvstruct
from . import img_in
from .rvstruct import PRM, Polygon, UV
from .common import to_blender_coord, to_blender_axis, FACE_QUAD, reverse_quad, get_texture_path, FACE_ENV
from .carinfo import read_parameters

# Check if 'bpy' is already in locals to determine if this is a reload scenario
if "bpy" in locals():
    importlib.reload(common)
    importlib.reload(rvstruct)
    importlib.reload(img_in)

def import_file(filepath, context, scene):
    """
    Imports a .prm/.m file and links it to the scene as a Blender object.
    It also imports all LoDs of a PRM file, which can be sequentially written
    to the file. There is no indicator for it, the file end has to be checked.
    """
    # Resets the index of the current env color
    scene = context.scene
    meshes = []

    # common.TEXTURES = {}

    with open(filepath, 'rb') as file:
        filename = os.path.basename(filepath)

        # Finds out the file end
        file_start = file.tell()
        file.seek(0, os.SEEK_END)
        file_end = file.tell()
        file.seek(file_start, os.SEEK_SET)

        # Reads meshes until the file ends
        while file.tell() < file_end:
            meshes.append(PRM(file))

    print("Imported {} ({} meshes)".format(filename, len(meshes)))

    for prm in meshes:
        me = import_mesh(prm, filepath, context, scene, envlist=None)

        if len(meshes) > 1:
            # Fake user if there are multiple LoDs so they're kept when saving
            me.use_fake_user = True

            # Append a quality suffix to meshes
            bname, number = me.name.rsplit(".", 1)
            me.name = "{}|q{}".format(bname, meshes.index(prm))

        # Assigns the highest quality mesh to an object and links it to the scn
        if meshes.index(prm) == 0:
            print("Creating Blender object for {}...".format(filename))
            ob = bpy.data.objects.new(filename, me)
            bpy.context.scene.collection.objects.link(ob)
            bpy.context.view_layer.objects.active = ob

    return ob


def import_mesh(prm, filepath, context, scene, envlist=None):
    filename = os.path.basename(filepath)
    
    # Create a new mesh
    me = bpy.data.meshes.new(filename)

    # Create a new bmesh
    bm = bmesh.new()
    
    add_rvmesh_to_bmesh(prm, bm, me, filepath, context, scene, envlist=None)

    # Convert the bmesh back to a mesh and free resources
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    
    # Create and assign materials based on color attributes with unique names
    materials = create_materials_for_attributes(me, bm, me.name)
    assign_materials_to_mesh(me, materials)

    return me

def add_rvmesh_to_bmesh(prm, bm, me, filepath, context, scene, envlist=None):
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
        normal = to_blender_axis(vert.normal.data)

        # Creates vertices
        bm.verts.new(Vector((position[0], position[1], position[2])))

        # Ensures lookup table (potentially puts out an error otherwise)
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
        if (poly.type & FACE_ENV) and envlist:
            face[env_alpha_layer] = envlist[scene.envidx % len(envlist)].alpha / 255

        # Assigns the UV mapping, colors and alpha
        for l in range(num_loops):
            # Converts the colors to float (req. by Blender)
            alpha = 1-(float(colors[l].alpha) / 255)
            color = [float(c) / 255 for c in colors[l].color]
            if envlist and (poly.type & FACE_ENV):
                env_col = [float(c) / 255 for c in envlist[scene.envidx].color]
                face.loops[l][env_layer][0] = env_col[0]
                face.loops[l][env_layer][1] = env_col[1]
                face.loops[l][env_layer][2] = env_col[2]

            face.loops[l][uv_layer].uv = (uvs[l].u, 1 - uvs[l].v)

            face.loops[l][vc_layer][0] = color[0]
            face.loops[l][vc_layer][1] = color[1]
            face.loops[l][vc_layer][2] = color[2]

            face.loops[l][va_layer][0] = alpha
            face.loops[l][va_layer][1] = alpha
            face.loops[l][va_layer][2] = alpha

        face.smooth = True
        if envlist and (poly.type & FACE_ENV):
            scene.envidx = (scene.envidx + 1) % len(envlist)

def create_materials_for_attributes(me, bm, obj_name):
    materials = {}
    for attr_name in ['Col', 'Env', 'Alpha']:
        mat_name = f"{obj_name}_{attr_name}"
        material = bpy.data.materials.get(mat_name)
        if not material:
            material = bpy.data.materials.new(name=mat_name)
            material.use_nodes = True
            nodes = material.node_tree.nodes
            links = material.node_tree.links

            # Ensure the Material Output node is available
            material_output = nodes.get('Material Output') or nodes.new(type='ShaderNodeOutputMaterial')
            attr_node = nodes.new(type='ShaderNodeAttribute')
            attr_node.attribute_name = attr_name
            attr_node.attribute_type = 'GEOMETRY'

            # Use Principled BSDF for all attributes
            principled_bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')

            if attr_name == 'Col':
                # Base color influenced by 'Col' vertex colors
                links.new(attr_node.outputs['Color'], principled_bsdf.inputs['Base Color'])

            elif attr_name == 'Env':
                # 'Env' influences another property like Metallic
                links.new(attr_node.outputs['Color'], principled_bsdf.inputs['Metallic'])

            elif attr_name == 'Alpha':
                # 'Alpha' vertex colors to drive grayscale visualized as base color
                color_ramp = nodes.new('ShaderNodeValToRGB')
                color_ramp.color_ramp.elements[0].color = (0, 0, 0, 1)  # Black
                color_ramp.color_ramp.elements[1].color = (1, 1, 1, 1)  # White
                links.new(attr_node.outputs['Color'], color_ramp.inputs['Fac'])
                links.new(color_ramp.outputs['Color'], principled_bsdf.inputs['Base Color'])

            # Connect the Principled BSDF to the material output
            links.new(principled_bsdf.outputs['BSDF'], material_output.inputs['Surface'])

        materials[attr_name] = material

    return materials

def assign_materials_to_mesh(me, materials):
    me.materials.clear()
    for mat in materials.values():
        me.materials.append(mat)

