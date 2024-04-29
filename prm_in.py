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
from .rvstruct import PRM
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

    return me

def get_or_create_material(texture_path):
    # If texture path is empty or the file does not exist, return None or a placeholder
    if not texture_path or not os.path.isfile(texture_path):
        print(f"Warning: Texture file '{texture_path}' not found.")
        # You can choose to return None or use a default/placeholder texture
        # Returning None will skip the texture, alternatively, you could specify a path to a default texture
        return None

    # Check if the material already exists
    for mat in bpy.data.materials:
        if mat.name == texture_path:
            return mat

    # Create a new material with the texture
    mat = bpy.data.materials.new(name=texture_path)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    
    # Create image texture node and load the texture
    tex_image = mat.node_tree.nodes.new('ShaderNodeTexImage')
    tex_image.image = bpy.data.images.load(texture_path)
    mat.node_tree.links.new(bsdf.inputs['Base Color'], tex_image.outputs['Color'])

    return mat

def add_rvmesh_to_bmesh(prm, bm, me, filepath, context, scene, envlist=None):
    """
    Adds PRM data to an existing bmesh. Returns the resulting bmesh.
    """
    scene = context.scene
    uv_layer = bm.loops.layers.uv.new("UVMap")
    vc_layer = bm.loops.layers.color.new("Col")
    env_layer = bm.loops.layers.color.new("Env")
    env_alpha_layer = bm.faces.layers.float.new("EnvAlpha")
    va_layer = bm.loops.layers.color.new("Alpha")
    texnum_layer = bm.faces.layers.int.new("Texture Number")
    type_layer = bm.faces.layers.int.new("Type")
    material_dict = {}
    created_faces = []

    if not envlist:
        print("Warning: envlist is empty.")
    elif scene.envidx >= len(envlist):
        print(f"Error: 'scene.envidx' ({scene.envidx}) is out of range for 'envlist' ({len(envlist)}). Resetting to 0.")
        scene.envidx = 0  # Optionally reset to 0 or handle as needed

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
        indices = poly.vertex_indices

        if is_quad:
            verts = (bm.verts[indices[3]], bm.verts[indices[2]],
                     bm.verts[indices[1]], bm.verts[indices[0]])
            # Reversed list of UVs and colors
            uvs = reverse_quad(poly.uv)
            colors = reverse_quad(poly.colors)

        else:
            verts = (bm.verts[indices[2]], bm.verts[indices[1]],
                     bm.verts[indices[0]])
            # Reversed list of UVs and colors without the last element
            uvs = reverse_quad(poly.uv, tri=True)
            colors = reverse_quad(poly.colors, tri=True)

        # Tries to create a face and yells at you when the face already exists
        try:
            face = bm.faces.new(verts)
            created_faces.append(face)
        except ValueError as e:
            print(f"Could not create face: {e}")
            continue
        
        bm.verts.ensure_lookup_table()
        bm.faces.ensure_lookup_table()

        # Assigns env alpha to face. Colors are on a vcol layer
        if (poly.type & FACE_ENV) and envlist:
            env_col_alpha = envlist[scene.envidx % len(envlist)].alpha
            face[env_alpha_layer] = float(env_col_alpha) / 255
            scene.envidx = (scene.envidx + 1) % len(envlist)  # Safely increment index
        
        # Assign UVs and colors
        for l, loop in enumerate(face.loops):
            loop[uv_layer].uv = (uvs[l].u, 1 - uvs[l].v)
            # Converts the colors to float (req. by Blender)
            alpha = 1-(float(colors[l].alpha) / 255)
            color = [float(c) / 255 for c in colors[l].color]

            loop[vc_layer][0] = color[0]
            loop[vc_layer][1] = color[1]
            loop[vc_layer][2] = color[2]

            loop[va_layer][0] = alpha
            loop[va_layer][1] = alpha
            loop[va_layer][2] = alpha
            
            if envlist and (poly.type & FACE_ENV):
                env_col = [float(c) / 255 for c in envlist[scene.envidx].color]
                loop[env_layer][0] = env_col[0]
                loop[env_layer][1] = env_col[1]
                loop[env_layer][2] = env_col[2]
                
                face[env_alpha_layer] = envlist[scene.envidx].alpha / 255
                
            # Enables smooth shading for that face
            face.smooth = True
            if envlist and (poly.type & FACE_ENV):
                scene.envidx = (scene.envidx + 1) % len(envlist)
    
        # Assign the material to the face
    for face, poly in zip(created_faces, prm.polygons):
        if poly.texture >= 0:
            texture_path = get_texture_path(filepath, poly.texture, scene)
            if texture_path not in material_dict:
                mat = get_or_create_material(texture_path)
                me.materials.append(mat)
                material_dict[texture_path] = len(me.materials) - 1
            face.material_index = material_dict[texture_path]

        # Assigns the face properties (bit field, one int per face)
        face[type_layer] = poly.type
        face[texnum_layer] = poly.texture

