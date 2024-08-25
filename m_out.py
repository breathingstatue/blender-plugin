"""
Name:    m_out
Purpose: Exports model files (.m)

Description:
Mesh used for models.

"""


if "bpy" in locals():
    import imp
    imp.reload(common)
    imp.reload(rvstruct)
    imp.reload(img_in)
    imp.reload(layers)

import os
import bpy
import bmesh
from mathutils import Color, Vector, Matrix
from . import common
from . import rvstruct
from . import img_in
from . import layers

from .common import dprint, get_all_lod, triangulate_ngons, queue_error, FACE_PROP_MASK, FACE_QUAD, texture_to_int, FACE_ENV, to_revolt_coord
from. common import to_revolt_axis, rvbbox_from_bm, center_from_rvbbox, radius_from_bmesh
from .layers import *
from .rvstruct import Model
from .tools import set_material_to_texture_for_object


def export_file(filepath, scene):
    obj = bpy.context.view_layer.objects.active
    print(f"Exporting M for {obj.name}...")
    
    # Ensure we're in object mode before any operations
    bpy.ops.object.mode_set(mode='OBJECT')

    # Assign Texture (UV_TEX) material where applicable
    set_material_to_texture_for_object(obj)

    # Check if other LoDs are present
    meshes = []
    if "|q" in obj.data.name:
        dprint("LODs present.")
        meshes = get_all_lod(obj.data.name.split('|')[0])
        print([m.name for m in meshes])
    else:
        dprint("No LOD present.")
        meshes.append(obj.data)

    # Create one instance of the Model class
    model = rvstruct.Model()

    # Process all meshes but merge them into the single model instance
    for me in meshes:
        print(f"Exporting mesh {meshes.index(me)} of {len(meshes)}")
        export_mesh(me, obj, scene, filepath, model)

    # Exports the texture animation
    animations = eval(scene.texture_animations)
    for animdict in animations:
        anim = rvstruct.TexAnimation()
        anim.from_dict(animdict)
        model.animations.append(anim)
    model.animation_count = scene.ta_max_slots

    # Write the single Model instance to the file
    with open(filepath, "wb") as file:
        model.write(file)
                
def get_texture_from_material(face, obj):
    # Check if the object has materials
    if obj.material_slots:
        # Ensure the material index is within the valid range
        if face.material_index < len(obj.material_slots):
            # Get the material from the corresponding slot
            mat = obj.material_slots[face.material_index].material
            if mat and mat.node_tree:
                # Iterate over all nodes in the material
                for node in mat.node_tree.nodes:
                    # Check if the node is an image texture node
                    if node.type == 'TEX_IMAGE':
                        # Return the first image texture found
                        return node.image
    return None

def export_mesh(me, obj, scene, filepath, model):
    # Creates a bmesh from the supplied mesh
    bm = bmesh.new()
    bm.from_mesh(me)

    # Applies the object scale if enabled
    if scene.apply_scale:
        bmesh.ops.scale(
            bm,
            vec=obj.scale,
            verts=bm.verts
        )
    # Applies the object rotation if enabled
    if scene.apply_rotation:
        bmesh.ops.rotate(
            bm,
            cent=obj.location,
            matrix=obj.rotation_euler.to_matrix(),
            space=obj.matrix_basis,
            verts=bm.verts
        )

    if scene.triangulate_ngons:
        num_ngons = triangulate_ngons(bm)
        if num_ngons > 0:  # Check if the number of n-gons is greater than zero
            print(f"Triangulated {num_ngons} n-gons")

    # Gets layers
    uv_layer = bm.loops.layers.uv.get("UVMap")
    vc_layer = (bm.loops.layers.color.get("Col") or 
                bm.loops.layers.color.new("Col"))
    env_layer = (bm.loops.layers.color.get("Env") or
                 bm.loops.layers.color.new("Env"))
    env_alpha_layer = (bm.faces.layers.float.get("EnvAlpha") or
                       bm.faces.layers.float.new("EnvAlpha"))
    va_layer = (bm.loops.layers.color.get("Alpha") or
                bm.loops.layers.color.new("Alpha"))
    texnum_layer = bm.faces.layers.int.get("Texture Number")
    type_layer = (bm.faces.layers.int.get("Type") or
                  bm.faces.layers.int.new("Type"))

    # Append polygons and vertices to the existing model instance
    model.polygon_count += len(bm.faces)
    model.vertex_count += len(bm.verts)

    for face in bm.faces:
        poly = rvstruct.Polygon()
        is_quad = len(face.verts) == 4

        poly.type = face[type_layer] & FACE_PROP_MASK

        # Sets the quad flag on the polygon
        if is_quad:
            poly.type |= FACE_QUAD

        # Gets the texture number from the integer layer if setting enabled
        if scene.use_tex_num and texnum_layer:
            poly.texture = face[texnum_layer]
        else:
            image = get_texture_from_material(face, obj)
            if image:
                poly.texture = texture_to_int(image.name)
            else:
                poly.texture = -1

        # Sets vertex indices for the polygon
        vert_order = [2, 1, 0, 3] if not is_quad else [3, 2, 1, 0]
        for i in vert_order:
            if i < len(face.verts):
                poly.vertex_indices.append(face.verts[i].index)
            else:
                poly.vertex_indices.append(0)  # Fills up unused indices with 0s

        # Write the vertex colors
        for i in vert_order:
            if i < len(face.verts):
                white = Color((1, 1, 1))
                color = face.loops[i][vc_layer] if vc_layer else white
                alpha = face.loops[i][va_layer] if va_layer else white
                col = rvstruct.Color(color=(int(color[0] * 255),
                                            int(color[1] * 255),
                                            int(color[2] * 255)),
                                     alpha=255-int(((alpha[0] + alpha[1] + alpha[2]) * 255) / 3))
                poly.colors.append(col)
            else:
                poly.colors.append(rvstruct.Color(color=(255, 255, 255), alpha=255))  # Writes white

        # Writes the UV
        for i in vert_order:
            if i < len(face.verts) and uv_layer:
                uv = face.loops[i][uv_layer].uv
                poly.uv.append(rvstruct.UV(uv=(uv[0], 1 - uv[1])))
            else:
                poly.uv.append(rvstruct.UV())

        model.polygons.append(poly)

    # Append vertex positions and normals to the model instance
    for vertex in bm.verts:
        coord = to_revolt_coord(vertex.co)
        normal = to_revolt_axis(vertex.normal)
        rvvert = rvstruct.Vertex()
        rvvert.position = rvstruct.Vector(data=coord)
        rvvert.normal = rvstruct.Vector(data=normal)
        model.vertices.append(rvvert)

    bm.free()