"""
Name:    texanim
Purpose: Provides operators and functions for the texture animation panel

Description:
Moved from operators and panels here to reduce script line amount
"""

import bmesh
import bpy
import os
from . import common
from . import rvstruct

if "common" in locals():
    import importlib
    importlib.reload(common)

from .common import TEX_PAGES_MAX, get_edit_bmesh, get_active_face, msg_box, FACE_TEXANIM
from .common import TEX_ANIM_MAX, int_to_texture
from .rvstruct import TexAnimation, Frame


def _normalize_texture_animations(scene):
    """Ensure texture animation data is safe to index."""
    ta = eval(scene.texture_animations)
    if not isinstance(ta, list):
        ta = []

    max_slots = max(scene.ta_max_slots, len(ta))
    while len(ta) < max_slots:
        ta.append(rvstruct.TexAnimation().as_dict())

    for slot_data in ta:
        frames = slot_data.get("frames")
        if not isinstance(frames, list):
            frames = []
            slot_data["frames"] = frames

        frame_count = slot_data.get("frame_count", len(frames))
        if frame_count < len(frames):
            frame_count = len(frames)
        slot_data["frame_count"] = frame_count

        while len(frames) < frame_count:
            frames.append(rvstruct.Frame().as_dict())

    scene.texture_animations = str(ta)
    return ta


def update_ta_max_slots(self, context):
    """Update the maximum number of slots for texture animations."""
    scene = context.scene
    if scene.ta_max_slots > 0:
        _normalize_texture_animations(scene)

def update_ta_max_frames(self, context):
    """Update the maximum number of frames in the current slot."""
    scene = context.scene
    slot = scene.ta_current_slot

    ta = _normalize_texture_animations(scene)
    if not ta or slot >= len(ta):
        return

    ta[slot]["frame_count"] = scene.ta_max_frames

    # Create new frames if necessary
    while len(ta[slot]["frames"]) < scene.ta_max_frames:
        new_frame = rvstruct.Frame().as_dict()
        ta[slot]["frames"].append(new_frame)

    scene.texture_animations = str(ta)  # Save the updated frames


def update_ta_current_slot(self, context):
    """Update the current texture animation slot."""
    scene = context.scene
    slot = scene.ta_current_slot

    # If no slots are available, keep the current slot at 0 and exit early to
    # avoid Blender repeatedly clamping the value and triggering a recursion.
    if scene.ta_max_slots == 0:
        if slot != 0:
            scene.ta_current_slot = 0
        return

    ta = _normalize_texture_animations(scene)

    # Ensure the current slot is within bounds
    if not ta:
        scene.ta_max_frames = 0
        return

    if slot > scene.ta_max_slots - 1 or slot >= len(ta):
        scene.ta_current_slot = min(scene.ta_max_slots - 1, len(ta) - 1)
        return

    scene.texture_animations = str(ta)  # Save the texture animations
    scene.ta_max_frames = ta[slot]["frame_count"]  # Update the max frames
    update_ta_current_frame(self, context)  # Update the current frame


def update_ta_current_frame(self, context):
    """Update the current texture animation frame."""
    scene = context.scene
    slot = scene.ta_current_slot
    frame = scene.ta_current_frame

    ta = _normalize_texture_animations(scene)
    if not ta or slot >= len(ta):
        return

    frames = ta[slot]["frames"]
    if not frames:
        scene.ta_current_frame = 0
        return

    # Ensure the current frame is within bounds
    if frame > scene.ta_max_frames - 1 or frame >= len(frames):
        scene.ta_current_frame = max(0, min(scene.ta_max_frames - 1, len(frames) - 1))
        return

    # Update the frame's texture and UV coordinates
    scene.ta_current_frame_tex = frames[frame]["texture"]
    scene.ta_current_frame_delay = frames[frame]["delay"]
    uv = frames[frame]["uv"]
    scene.ta_current_frame_uv0 = (uv[3]["u"], 1 - uv[3]["v"])
    scene.ta_current_frame_uv1 = (uv[2]["u"], 1 - uv[2]["v"])
    scene.ta_current_frame_uv2 = (uv[1]["u"], 1 - uv[1]["v"])
    scene.ta_current_frame_uv3 = (uv[0]["u"], 1 - uv[0]["v"])


def update_ta_current_frame_tex(self, context):
    """Update the texture of the current frame."""
    scene = context.scene
    slot = scene.ta_current_slot
    frame = scene.ta_current_frame

    ta = _normalize_texture_animations(scene)
    if not ta or slot >= len(ta) or frame >= len(ta[slot]["frames"]):
        return

    ta[slot]["frames"][frame]["texture"] = scene.ta_current_frame_tex  # Update texture
    scene.texture_animations = str(ta)  # Save the updated texture animations


def update_ta_current_frame_delay(self, context):
    """Update the delay of the current frame."""
    scene = context.scene
    slot = scene.ta_current_slot
    frame = scene.ta_current_frame

    ta = _normalize_texture_animations(scene)
    if not ta or slot >= len(ta) or frame >= len(ta[slot]["frames"]):
        return

    ta[slot]["frames"][frame]["delay"] = scene.ta_current_frame_delay  # Update delay
    scene.texture_animations = str(ta)  # Save the updated texture animations


def update_ta_current_frame_uv(context, num):
    """Update the UV coordinates of the current frame."""
    scene = bpy.context.scene
    prop_str = f"ta_current_frame_uv{num}"
    slot = scene.ta_current_slot
    frame = scene.ta_current_frame

    # Reverse the accessor since they're saved in reverse order
    num = [0, 1, 2, 3][::-1][num]

    ta = _normalize_texture_animations(scene)
    if not ta or slot >= len(ta) or frame >= len(ta[slot]["frames"]):
        return

    ta[slot]["frames"][frame]["uv"][num]["u"] = getattr(scene, prop_str)[0]
    ta[slot]["frames"][frame]["uv"][num]["v"] = 1 - getattr(scene, prop_str)[1]
    scene.texture_animations = str(ta)  # Save the updated UVs

def copy_uv_to_frame(context):
    scene = context.scene
    obj = context.object

    if not obj or obj.type != 'MESH' or not obj.data:
        msg_box("Please select a valid mesh object in Edit Mode.", "ERROR")
        return

    if obj.mode != 'EDIT':
        bpy.ops.object.mode_set(mode='EDIT')

    bm = bmesh.from_edit_mesh(obj.data)
            
    uv_layer = bm.loops.layers.uv.get("UVMap")
    if not uv_layer:
        msg_box("Please create a UV layer first", "ERROR")
        return
            
    # Iterate over selected faces
    selected_faces = [f for f in bm.faces if f.select]
    if not selected_faces:
        msg_box("Please select at least one face", "ERROR")
        return

    for face in selected_faces:
        for lnum, loop in enumerate(face.loops):
            uv = loop[uv_layer].uv
            if lnum == 0:
                scene.ta_current_frame_uv0 = (uv[0], uv[1])
            elif lnum == 1:
                scene.ta_current_frame_uv1 = (uv[0], uv[1])
            elif lnum == 2:
                scene.ta_current_frame_uv2 = (uv[0], uv[1])
            elif lnum == 3:
                scene.ta_current_frame_uv3 = (uv[0], uv[1])
            
    # Update the BMesh data back to the mesh
    bmesh.update_edit_mesh(obj.data)
        
def copy_frame_to_uv(context):
    scene = context.scene
    obj = context.object

    if not obj or obj.type != 'MESH' or not obj.data:
        msg_box("Please select a valid mesh object in Edit Mode.", "ERROR")
        return

    if obj.mode != 'EDIT':
        bpy.ops.object.mode_set(mode='EDIT')

    bm = bmesh.from_edit_mesh(obj.data)
        
    # Get the texture number from the current frame
    texture_number = scene.ta_current_frame_tex
        
    # Generate the texture letter using the int_to_texture function
    texture_letter = int_to_texture(texture_number)
        
    # Find the matching texture image
    texture_image = find_matching_texture(texture_letter)
        
    if not texture_image:
        msg_box(f"Texture ending with '{texture_letter}' not found in images!", "ERROR")
        return
        
    # Look for the material that uses this texture image
    material = find_material_using_texture(obj, texture_image)
        
    if not material:
        msg_box(f"Material using texture '{texture_image.name}' not found!", "ERROR")
        return

    # -------------------------------------------------
    # 🔹 ENSURE MATERIAL IS ON THIS OBJECT
    # -------------------------------------------------
    mats = obj.data.materials

    # Check if material already exists in the object’s slots
    existing_names = [m.name for m in mats if m]
    if material.name not in existing_names:
        mats.append(material)

    # Get the index again AFTER appending
    material_index = mats.find(material.name)

    # Safety check: if still invalid, bail out with an error
    if material_index < 0 or material_index >= len(mats):
        msg_box(
            f"Internal error: material index for '{material.name}' is invalid.",
            "ERROR"
        )
        return
    # -------------------------------------------------

    # Iterate over selected faces
    selected_faces = [f for f in bm.faces if f.select]
    if not selected_faces:
        msg_box("Please select at least one face", "ERROR")
        return

    # Assign the material to the selected faces
    for sel_face in selected_faces:
        sel_face.material_index = material_index

    # Now handle UV coordinates only if UV layer exists
    uv_layer = bm.loops.layers.uv.get("UVMap")
    if not uv_layer:
        msg_box("Please create a UV layer first")
        return

    for sel_face in selected_faces:
        for lnum, loop in enumerate(sel_face.loops):
            uv = getattr(scene, f"ta_current_frame_uv{lnum}")
            loop[uv_layer].uv = uv

    # Update the BMesh data back to the mesh
    bmesh.update_edit_mesh(obj.data)
    
def find_matching_texture(texture_letter):
    # Remove the file extension if present in the texture letter
    texture_letter = texture_letter.replace(".bmp", "").lower()
    
    # Iterate through all images in bpy.data.images
    for image in bpy.data.images:
        image_name_lower = image.name.lower()
        base_name, extension = os.path.splitext(image_name_lower)
        
        # Check if the base name ends with the texture letter
        if base_name.endswith(texture_letter):
            return image

    return None

def find_material_using_texture(obj, texture_image):
    """Find a material that uses the given texture image.

    1) First check materials already assigned to the object.
    2) If not found, search all materials in bpy.data.materials.
    """
    # --- 1) Search materials already on this object ---
    for material_slot in obj.material_slots:
        material = material_slot.material
        if material and material.use_nodes:
            for node in material.node_tree.nodes:
                if node.type == 'TEX_IMAGE' and node.image == texture_image:
                    return material

    # --- 2) Fallback: search all materials in the file ---
    for material in bpy.data.materials:
        if not material or not material.use_nodes:
            continue
        for node in material.node_tree.nodes:
            if node.type == 'TEX_IMAGE' and node.image == texture_image:
                return material

    return None
