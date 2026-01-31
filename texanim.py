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

def ensure_slot_frames(ta, slot, frame_count):
    """Make sure ta[slot]['frames'] contains at least frame_count frames.
       Also ensure UV dicts are not shared references.
    """
    frames = ta[slot].setdefault("frames", [])
    while len(frames) < frame_count:
        f = rvstruct.Frame().as_dict()

        # Safety: if uv dicts were created with * 4, they may be the same object.
        uv = f.get("uv")
        if isinstance(uv, list) and len(uv) == 4:
            f["uv"] = [{"u": p.get("u", 0.0), "v": p.get("v", 0.0)} for p in uv]

        frames.append(f)

def update_ta_max_slots(self, context):
    """Update the maximum number of slots for texture animations."""
    scene = context.scene
    if scene.ta_max_slots > 0:
        ta = eval(scene.texture_animations)  # Convert string to dictionary

        # Create new animation slots if needed
        while len(ta) < scene.ta_max_slots:
            ta.append(rvstruct.TexAnimation().as_dict())

        scene.texture_animations = str(ta)  # Save the updated texture animations

def update_ta_max_frames(self, context):
    """Update the maximum number of frames in the current slot."""
    scene = context.scene
    slot = scene.ta_current_slot

    ta = eval(scene.texture_animations)
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

    ta = eval(scene.texture_animations)  # Convert string to dictionary

    # Ensure the current slot is within bounds
    if slot > scene.ta_max_slots - 1:
        scene.ta_current_slot = scene.ta_max_slots - 1
        return

    scene.texture_animations = str(ta)  # Save the texture animations
    scene.ta_max_frames = ta[slot].get("frame_count", scene.ta_max_frames)
    ensure_slot_frames(ta, slot, scene.ta_max_frames)
    scene.texture_animations = str(ta)
    update_ta_current_frame(self, context)


def update_ta_current_frame(self, context):
    """Update the current texture animation frame."""
    scene = context.scene
    slot = scene.ta_current_slot
    frame = scene.ta_current_frame

    ta = eval(scene.texture_animations)  # Convert string to dictionary

    # Ensure the current frame is within bounds
    if frame > scene.ta_max_frames - 1:
        scene.ta_current_frame = scene.ta_max_frames - 1
        return

    # Update the frame's texture and UV coordinates
    scene.ta_current_frame_tex = ta[slot]["frames"][frame]["texture"]
    scene.ta_current_frame_delay = ta[slot]["frames"][frame]["delay"]
    uv = ta[slot]["frames"][frame]["uv"]
    scene.ta_current_frame_uv0 = (uv[3]["u"], 1 - uv[3]["v"])
    scene.ta_current_frame_uv1 = (uv[2]["u"], 1 - uv[2]["v"])
    scene.ta_current_frame_uv2 = (uv[1]["u"], 1 - uv[1]["v"])
    scene.ta_current_frame_uv3 = (uv[0]["u"], 1 - uv[0]["v"])


def update_ta_current_frame_tex(self, context):
    """Update the texture of the current frame."""
    scene = context.scene
    slot = scene.ta_current_slot
    frame = scene.ta_current_frame

    ta = eval(scene.texture_animations)
    ta[slot]["frames"][frame]["texture"] = scene.ta_current_frame_tex  # Update texture
    scene.texture_animations = str(ta)  # Save the updated texture animations


def update_ta_current_frame_delay(self, context):
    """Update the delay of the current frame."""
    scene = context.scene
    slot = scene.ta_current_slot
    frame = scene.ta_current_frame

    ta = eval(scene.texture_animations)
    ta[slot]["frames"][frame]["delay"] = scene.ta_current_frame_delay  # Update delay
    scene.texture_animations = str(ta)  # Save the updated texture animations


def update_ta_current_frame_uv(context, ui_index):
    """Write UI UV(ui_index) into stored TA UV (allocation-safe)."""
    scene = context.scene
    slot = scene.ta_current_slot
    frame = scene.ta_current_frame

    ta = eval(scene.texture_animations)

    # Ensure slot frames exist at least up to current frame
    needed = max(int(scene.ta_max_frames), int(frame) + 1)
    ensure_slot_frames(ta, slot, needed)

    # UI0->stored3, UI1->stored2, UI2->stored1, UI3->stored0
    stored_index = (3 - ui_index)

    u, v_ui = getattr(scene, f"ta_current_frame_uv{ui_index}")
    ta[slot]["frames"][frame]["uv"][stored_index]["u"] = float(u)
    ta[slot]["frames"][frame]["uv"][stored_index]["v"] = 1.0 - float(v_ui)

    scene.texture_animations = str(ta)

def sync_ui_uvs_to_frame(scene, ta, slot, frame):
    """Sync current UI UVs into the specified TA frame (allocation-safe)."""
    needed = max(int(scene.ta_max_frames), int(frame) + 1)
    ensure_slot_frames(ta, slot, needed)

    ui_uv = [
        scene.ta_current_frame_uv0,
        scene.ta_current_frame_uv1,
        scene.ta_current_frame_uv2,
        scene.ta_current_frame_uv3,
    ]

    for ui_index, (u, v_ui) in enumerate(ui_uv):
        stored_index = 3 - ui_index
        ta[slot]["frames"][frame]["uv"][stored_index]["u"] = float(u)
        ta[slot]["frames"][frame]["uv"][stored_index]["v"] = 1.0 - float(v_ui)

def sync_frame_uvs_from_mesh(context, ta, slot, frame):
    """Sync UVs from the active edit-mode face into the specified TA frame."""
    obj = context.object
    if not obj or obj.type != 'MESH' or obj.mode != 'EDIT':
        return False

    bm = get_edit_bmesh(obj)
    if not bm:
        return False

    uv_layer = bm.loops.layers.uv.active
    if not uv_layer:
        return False

    face = get_active_face(bm)
    if not face:
        selected_faces = [f for f in bm.faces if f.select]
        if not selected_faces:
            return False
        face = selected_faces[0]

    loops = list(face.loops)
    if len(loops) != 4:
        return False

    needed = max(int(context.scene.ta_max_frames), int(frame) + 1)
    ensure_slot_frames(ta, slot, needed)

    # UI0<-loop3, UI1<-loop2, UI2<-loop1, UI3<-loop0
    loop_to_ui = {3: 0, 2: 1, 1: 2, 0: 3}

    for loop_index, ui_index in loop_to_ui.items():
        uv = loops[loop_index][uv_layer].uv
        stored_index = 3 - ui_index
        ta[slot]["frames"][frame]["uv"][stored_index]["u"] = float(uv.x)
        ta[slot]["frames"][frame]["uv"][stored_index]["v"] = 1.0 - float(uv.y)

    return True

def copy_uv_to_frame(context):
    scene = context.scene
    obj = context.object

    if not obj or obj.type != 'MESH' or not obj.data:
        msg_box("Please select a valid mesh object.", "ERROR")
        return
    if obj.mode != 'EDIT':
        msg_box("Please go to Edit Mode and select a quad face.", "ERROR")
        return

    bm = bmesh.from_edit_mesh(obj.data)
    uv_layer = bm.loops.layers.uv.active
    if not uv_layer:
        msg_box("Please create a UV layer first.", "ERROR")
        return

    selected_faces = [f for f in bm.faces if f.select]
    if not selected_faces:
        msg_box("Please select a face first.", "ERROR")
        return

    face = selected_faces[0]
    loops = list(face.loops)
    if len(loops) != 4:
        msg_box("UV to Frame supports quads only.", "ERROR")
        return

    # Force allocation for current slot/frame before writing
    ta = eval(scene.texture_animations)
    needed = max(int(scene.ta_max_frames), int(scene.ta_current_frame) + 1)
    ensure_slot_frames(ta, scene.ta_current_slot, needed)
    scene.texture_animations = str(ta)

    # UI0<-loop3, UI1<-loop2, UI2<-loop1, UI3<-loop0
    loop_to_ui = {3: 0, 2: 1, 1: 2, 0: 3}

    for loop_index, ui_index in loop_to_ui.items():
        uv = loops[loop_index][uv_layer].uv
        setattr(scene, f"ta_current_frame_uv{ui_index}", (float(uv.x), float(uv.y)))
        update_ta_current_frame_uv(context, ui_index)

    update_ta_current_frame(None, context)
    ta = eval(scene.texture_animations)
    uv = ta[scene.ta_current_slot]["frames"][scene.ta_current_frame]["uv"]
    print("AFTER UV->FRAME:", scene.ta_current_frame, [(p["u"], p["v"]) for p in uv])

    bmesh.update_edit_mesh(obj.data)
    if context.area:
        context.area.tag_redraw()
        
def copy_frame_to_uv(context):
    """
    Apply current TA frame (via UI props) -> selected mesh faces.
    Correctly maps UI UVs to face loop order:
      UI0->loop3, UI1->loop2, UI2->loop1, UI3->loop0
    UI props already represent unflipped Blender UV space (because update_ta_current_frame() flips them for display).
    """
    scene = context.scene
    obj = context.object

    if not obj or obj.type != 'MESH' or not obj.data:
        msg_box("Please select a valid mesh object.", "ERROR")
        return

    if obj.mode != 'EDIT':
        msg_box("Please go to Edit Mode and select face(s) first.", "ERROR")
        return

    bm = bmesh.from_edit_mesh(obj.data)

    # -------------------------------
    # Optional: assign material based on current frame texture
    # -------------------------------
    texture_number = scene.ta_current_frame_tex
    texture_letter = int_to_texture(texture_number)
    texture_image = find_matching_texture(texture_letter)

    if not texture_image:
        msg_box(f"Texture ending with '{texture_letter}' not found in images!", "ERROR")
        return

    material = find_material_using_texture(obj, texture_image)
    if not material:
        msg_box(f"Material using texture '{texture_image.name}' not found!", "ERROR")
        return

    # Ensure material exists in object's material slots
    mats = obj.data.materials
    existing_names = [m.name for m in mats if m]
    if material.name not in existing_names:
        mats.append(material)

    material_index = mats.find(material.name)
    if material_index < 0 or material_index >= len(mats):
        msg_box(f"Internal error: material index for '{material.name}' is invalid.", "ERROR")
        return
    # -------------------------------

    selected_faces = [f for f in bm.faces if f.select]
    if not selected_faces:
        msg_box("Please select at least one face.", "ERROR")
        return

    uv_layer = bm.loops.layers.uv.active
    if not uv_layer:
        msg_box("Please create a UV layer first.", "ERROR")
        return

    # UI -> loop mapping: UI0->loop3, UI1->loop2, UI2->loop1, UI3->loop0
    ui_to_loop = {0: 3, 1: 2, 2: 1, 3: 0}

    # Read UI UVs once (Blender UV space)
    ui_uv = [
        scene.ta_current_frame_uv0,
        scene.ta_current_frame_uv1,
        scene.ta_current_frame_uv2,
        scene.ta_current_frame_uv3,
    ]

    for face in selected_faces:
        if len(face.loops) != 4:
            # Skip non-quads to avoid broken mapping
            continue

        face.material_index = material_index
        loops = list(face.loops)

        for ui_index, loop_index in ui_to_loop.items():
            u, v = ui_uv[ui_index]
            loops[loop_index][uv_layer].uv = (float(u), float(v))

    bmesh.update_edit_mesh(obj.data)
    if context.area:
        context.area.tag_redraw()
    
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
