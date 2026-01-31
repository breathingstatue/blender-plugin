"""
Name:    prm_out
Purpose: Exports Probe mesh files (.prm)

Description:
Meshes used for cars and world meshes.
"""

import os
import bpy
import bmesh
import importlib
from mathutils import Color, Vector, Matrix

from . import common
from . import rvstruct
from . import img_in
from . import layers

from .common import (
    dprint, get_all_lod, triangulate_ngons, queue_error,
    FACE_QUAD, FACE_PROP_MASK, texture_to_int, FACE_ENV, FACE_TEXANIM
)
from .common import to_revolt_coord, to_revolt_axis, rvbbox_from_bm, center_from_rvbbox, radius_from_bmesh
from .layers import *

# --- Proper module reloads for development mode ---
if "bpy" in locals():
    importlib.reload(common)
    importlib.reload(rvstruct)
    importlib.reload(img_in)
    importlib.reload(layers)


# Track logs to avoid spamming the console during export
_material_texture_logs = set()
_texture_assignment_logs = set()
_missing_texture_logged = False

def export_file(filepath, scene):
    obj = bpy.context.view_layer.objects.active
    print("Exporting PRM for {}...".format(obj.name))
    meshes = []

    # Preserve user selection and mode to avoid leaving Blender in an unexpected state
    original_mode = bpy.context.mode
    original_active = bpy.context.view_layer.objects.active
    original_selection = list(bpy.context.selected_objects)

    # Reset log caches for this export run
    _material_texture_logs.clear()
    _texture_assignment_logs.clear()
    global _missing_texture_logged
    _missing_texture_logged = False

    try:
        # Ensure we're in object mode before any operations
        bpy.ops.object.mode_set(mode='OBJECT')

        # Get all mesh objects in the scene
        mesh_objects = [obj for obj in scene.objects if obj.type == 'MESH']
        print(f"Found {len(mesh_objects)} mesh objects in the scene.")

        # Run material assignment for both COL and UV_TEX
        set_material_to_col(mesh_objects)

        # Force an update of the view layer
        bpy.context.view_layer.update()

        set_material_to_texture(mesh_objects)

        # Checks if other LoDs are present
        if "|q" in obj.data.name:
            dprint("LODs present.")
            meshes = get_all_lod(obj.data.name.split('|')[0])
            print([m.name for m in meshes])
        else:
            dprint("No LOD present.")
            meshes.append(obj.data)

        # Exports all meshes to the PRM file
        with open(filepath, "wb") as file:
            for me in meshes:
                print("Exporting mesh {} of {}".format(
                    meshes.index(me), len(meshes)))
                # Exports the mesh as a PRM object
                prm = export_mesh(me, obj, scene, filepath)
                # Writes the PRM object to a file
                if prm:
                    prm.write(file)
    finally:
        # Restore selection and mode so the user is not left in a different context
        bpy.ops.object.select_all(action='DESELECT')
        for sel_obj in original_selection:
            if sel_obj.name in bpy.context.scene.objects:
                sel_obj.select_set(True)

        if original_active and original_active.name in bpy.context.scene.objects:
            bpy.context.view_layer.objects.active = original_active

        if original_mode != bpy.context.mode:
            try:
                bpy.ops.object.mode_set(mode=original_mode)
            except Exception:
                # If returning to the original mode fails, stay in object mode silently
                pass

def get_texture_from_material(face, obj, default_texture_name=None):
    global _material_texture_logs, _missing_texture_logged
    # Check if the object has materials
    if obj.material_slots:
        if face.material_index < len(obj.material_slots):
            mat = obj.material_slots[face.material_index].material
            if mat and mat.node_tree:
                for node in mat.node_tree.nodes:
                    if node.type == 'TEX_IMAGE':
                        image = node.image
                        if image:
                            # Check if the image name matches 'car' or the object's name
                            if image.name == 'car' or image.name == obj.name.split('.')[0]:
                                log_key = (mat.name, image.name)
                                if log_key not in _material_texture_logs:
                                    dprint(f"Found matching image: {image.name} for material: {mat.name} on {obj.name}")
                                    _material_texture_logs.add(log_key)
                                # Rename the material to match the texture name without duplicating '.bmp'
                                if not image.name.endswith('.bmp'):
                                    mat.name = f"{image.name}.bmp"
                                else:
                                    mat.name = image.name
                                return image
                            else:
                                log_key = (mat.name, image.name)
                                if log_key not in _material_texture_logs:
                                    dprint(f"Found image: {image.name} for material: {mat.name} on {obj.name}")
                                    _material_texture_logs.add(log_key)
                                # Rename the material to match the texture name without duplicating '.bmp'
                                if not image.name.endswith('.bmp'):
                                    mat.name = f"{image.name}.bmp"
                                else:
                                    mat.name = image.name
                                return image
                        else:
                            log_key = (mat.name, "NO_IMAGE")
                            if log_key not in _material_texture_logs:
                                dprint(f"No image found for material: {mat.name} on {obj.name}")
                                _material_texture_logs.add(log_key)

    # Fallback to default texture if specified
    if default_texture_name:
        default_texture = bpy.data.images.get(default_texture_name)
        if default_texture:
            log_key = ("DEFAULT", default_texture_name)
            if log_key not in _material_texture_logs:
                dprint(f"Using default texture image {default_texture_name} for {obj.name}")
                _material_texture_logs.add(log_key)
            return default_texture
        else:
            log_key = ("DEFAULT_MISSING", default_texture_name)
            if log_key not in _material_texture_logs:
                dprint(f"Default texture {default_texture_name} not found for {obj.name}")
                _material_texture_logs.add(log_key)

    # Final fallback if no image is found
    if not _missing_texture_logged:
        print(f"Error: No material or texture found for {obj.name}")
        _missing_texture_logged = True
    return None

def export_mesh(me, obj, scene, filepath, world=None):
    global _missing_texture_logged
    """
    This exports an object to an rvstruct object. This is also used for .w
    meshes since they're pretty much the same as PRM. The only additions are
    boundaries and the per-face environment color.
    If an rvstruct world object is provided, this will return an rvstruct.mesh
    instead of an rvstruct.PRM.
    """
    # Creates a bmesh from the supplied mesh
    bm = bmesh.new()
    bm.from_mesh(me)

    if world is None:
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
    else:
        # Removes the parent for exporting
        parent = obj.parent
        if parent:
            mat = obj.matrix_world.copy()
            old_mat = obj.matrix_basis.copy()
            obj.parent = None
            obj.matrix_world = mat

        spc = obj.matrix_basis
        bmesh.ops.scale(
            bm,
            vec=obj.scale,
            space=spc,
            verts=bm.verts
        )
        bmesh.ops.transform(
            bm,
            matrix=Matrix.Translation(obj.location),
            space=spc,
            verts=bm.verts
        )
        bmesh.ops.rotate(
            bm,
            cent=obj.location,
            matrix=obj.rotation_euler.to_matrix(),
            space=spc,
            verts=bm.verts
        )

        # Restores the parent relationship
        if parent and not obj.parent:
            obj.parent = parent
            obj.matrix_basis = old_mat

    if scene.triangulate_ngons:
        num_ngons = triangulate_ngons(bm)
        if num_ngons > 0:
            print("Triangulated {} n-gons".format(num_ngons))

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
    texnum_layer = (bm.faces.layers.int.get("Texture Number") or
                bm.loops.layers.int.new("Texture Number"))
    type_layer = (bm.faces.layers.int.get("Type") or 
                bm.faces.layers.int.new("Type"))

    # Creates an empty PRM or Mesh structure
    if world is None:
        prm = rvstruct.PRM()
    else:
        prm = rvstruct.Mesh()

    prm.polygon_count = len(bm.faces)
    if prm.polygon_count > 65535:
        queue_error(
            "exporting mesh",
            "Too many polygons, try splitting up your mesh."
        )
        return None

    prm.vertex_count = len(bm.verts)
    if prm.vertex_count > 65535:
        queue_error(
            "exporting mesh",
            "Too many vertices, try splitting up your mesh."
        )
        return None

    for face in bm.faces:
        poly = rvstruct.Polygon()
        is_quad = len(face.verts) == 4

        poly.type = face[type_layer] & FACE_PROP_MASK

        # Sets the quad flag on the polygon
        if is_quad:
            poly.type |= FACE_QUAD

        # --- NEW: resolve animation slot vs texture page ---
        anim_slot_layer = bm.faces.layers.int.get("Anim Slot")
        is_texanim = bool(poly.type & FACE_TEXANIM)

        if is_texanim and anim_slot_layer:
            # Animated face: poly.texture is index into World.animations[]
            poly.texture = face[anim_slot_layer]
            print(f"[ANIM] Face {face.index}: Using Anim Slot layer → {poly.texture}")
            image = None  # purely for debug print below
        elif scene.use_tex_num and texnum_layer:
            # Non-animated or no Anim Slot: use Texture Number layer
            poly.texture = face[texnum_layer]
            print(f"[OK] Face {face.index}: Using Texture Number layer → {poly.texture}")
            image = None
        else:
            # Falls back to material-based texture name
            if world is None:
                # PRM export
                image = get_texture_from_material(face, obj)
            else:
                # World export: may use scene.default_texture_name
                image = get_texture_from_material(face, obj, scene.default_texture_name)

            if image:
                print(f"Assigning texture: {image.name} to face")
                poly.texture = texture_to_int(image.name)
            else:
                print(f"No texture assigned to face")
                poly.texture = -1
        # --- END slot / page resolution ---

        print(f"Face texture index = {poly.texture} ({image.name if image else 'NO IMAGE'})")

        # Sets vertex indices for the polygon
        vert_order = [2, 1, 0, 3] if not is_quad else [3, 2, 1, 0]
        for i in vert_order:
            if i < len(face.verts):
                poly.vertex_indices.append(face.verts[i].index)
            else:
                # Fills up unused indices with 0s
                poly.vertex_indices.append(0)

        # Write the vertex colors
        for i in vert_order:
            if i < len(face.verts):
                # Gets color from the channel or falls back to a default value
                white = Color((1, 1, 1))
                color = face.loops[i][vc_layer] if vc_layer else white
                alpha = face.loops[i][va_layer] if va_layer else white
                col = rvstruct.Color(color=(int(color[0] * 255),
                                            int(color[1] * 255),
                                            int(color[2] * 255)),
                                     alpha=255 - int(((alpha[0] + alpha[1] + alpha[2]) * 255) / 3))
                poly.colors.append(col)
            else:
                # Writes white
                col = rvstruct.Color(color=(255, 255, 255), alpha=255)
                poly.colors.append(col)

        # Writes the UV
        for i in vert_order:
            if i < len(face.verts) and uv_layer:
                uv = face.loops[i][uv_layer].uv
                poly.uv.append(rvstruct.UV(uv=(uv[0], 1 - uv[1])))
            else:
                poly.uv.append(rvstruct.UV())

        if world is not None:
            if (poly.type & FACE_ENV):
                rgb = [int(c * 255) for c in get_average_vcol2([face], env_layer)]
                alpha = int(face[env_alpha_layer] * 255)
                col = rvstruct.Color(color=rgb, alpha=alpha)
                world.env_list.append(col)

        prm.polygons.append(poly)

    # Export vertex positions and normals
    for vertex in bm.verts:
        coord = to_revolt_coord(vertex.co)
        normal = to_revolt_axis(vertex.normal)
        rvvert = rvstruct.Vertex()
        rvvert.position = rvstruct.Vector(data=coord)
        rvvert.normal = rvstruct.Vector(data=normal)
        prm.vertices.append(rvvert)

    # World extras
    if world is not None:
        # Skip empty meshes (0 verts) – they have no valid PRM representation
        if len(bm.verts) == 0:
            dprint(f"[Re-Volt Export] Skipping empty mesh (0 verts): {obj.name}")
            bm.free()
            return None

        rvbbox = rvbbox_from_bm(bm)
        center = center_from_rvbbox(rvbbox)
        radius = radius_from_bmesh(bm, center)
        prm.bound_ball_center = rvstruct.Vector(data=center)
        prm.bound_ball_radius = radius
        prm.bbox = rvstruct.BoundingBox(data=rvbbox)

    bm.free()
    return prm

def set_material_to_col(mesh_objects):
    """Sets the material to Vertex Colour (COL) for all mesh objects."""
    if not mesh_objects:
        print("No mesh objects selected for material assignment.")
        return

    scene = bpy.context.scene
    if not hasattr(scene, "material_choice"):
        print("[WARN] Scene has no 'material_choice' property; cannot assign COL materials.")
        return

    # Set the global Scene-level choice
    scene.material_choice = 'COL'

    # Select all target meshes
    bpy.ops.object.select_all(action='DESELECT')
    for obj in mesh_objects:
        obj.select_set(True)

    # Ensure a valid active object
    bpy.context.view_layer.objects.active = mesh_objects[0]

    # Make sure we are in OBJECT mode
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    # Let the operator handle edit mode + face selection
    bpy.ops.object.assign_materials_impexp()

    print("Assigned COL materials to all mesh objects.")


def set_material_to_texture(mesh_objects):
    """Sets the material to Texture (UV_TEX) for all mesh objects."""
    if not mesh_objects:
        print("No mesh objects selected for material assignment.")
        return

    scene = bpy.context.scene
    if not hasattr(scene, "material_choice"):
        print("[WARN] Scene has no 'material_choice' property; cannot assign UV_TEX materials.")
        return

    # Set the global Scene-level choice
    scene.material_choice = 'UV_TEX'

    # Select all target meshes
    bpy.ops.object.select_all(action='DESELECT')
    for obj in mesh_objects:
        obj.select_set(True)

    # Ensure a valid active object
    bpy.context.view_layer.objects.active = mesh_objects[0]

    # Make sure we are in OBJECT mode
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    # Let the operator handle edit mode + face selection
    bpy.ops.object.assign_materials_impexp()

    print("Assigned UV_TEX materials to all mesh objects.")
