"""
Name:    texanim
Purpose: Provides operators and functions for the texture animation panel

Description:
Moved from operators and panels here to reduce script line amount

"""

import json
import bmesh
import bpy
from . import common
from . import rvstruct

if "bpy" in locals():
    import importlib
    importlib.reload(common)
    
from .common import TEX_PAGES_MAX, get_edit_bmesh, get_active_face, msg_box

def update_ta_max_slots(self, context):
    scene = context.scene
    slot = scene.ta_current_slot
    frame = scene.frame_current

    if scene.ta_max_slots > 0:
        print("TexAnim: Updating max slots..")

        # Converts the texture animations from string to dict
        ta = json.loads(scene.texture_animations)

        # Creates a new texture animation if there is none in the slot
        while len(ta) < scene.ta_max_slots:
            print("TexAnim: Creating new animation slot... ({}/{})".format(
                len(ta) + 1, scene.ta_max_slots)
            )
            ta.append(rvstruct.TexAnimation().as_dict())

        # Saves the texture animation
        scene.texture_animations = str(ta)

        # Updates the rest of the UI
        # update_ta_current_slot(self, context)

def update_ta_max_frames(self, context):
    scene = context.scene
    slot = scene.ta_current_slot
    # frame = scene.frame_current

    print("TexAnim: Updating max frames..")
    ta = json.loads(scene.texture_animations)
    ta[slot]["frame_count"] = scene.ta_max_frames

    # Creates new empty frames if there are none for the current slot
    while len(ta[slot]["frames"]) < scene.ta_max_frames:
        print("Creating new animation frame... ({}/{})".format(
            len(ta[slot]["frames"]) + 1, scene.ta_max_frames))

        new_frame = rvstruct.Frame().as_dict()
        ta[slot]["frames"].append(new_frame)

    scene.texture_animations = str(ta)

def update_ta_current_slot(self, context):
    scene = context.scene
    slot = scene.ta_current_slot

    print("TexAnim: Updating current slot..")

    # Converts the texture animations from string to dict using json
    ta = json.loads(scene.texture_animations)

    # Check if the slot is within the range. Adjust if necessary.
    if slot >= len(ta) or slot < 0:
        print("Slot is out of range, adjusting...")
        scene.ta_current_slot = max(min(slot, len(ta) - 1), 0)  # Clamp the slot value within valid range
        slot = scene.ta_current_slot  # Update the slot after clamping

    if slot < len(ta):
        # Update the maximum frames based on the new slot
        scene.ta_max_frames = len(ta[slot]['frames']) if 'frames' in ta[slot] else 0

        # Call update on the current frame to refresh related data
        update_ta_current_frame(self, context)
    else:
        print("Invalid slot: No data available.")

    # No need to serialize back to string if no changes were made to 'ta'

# Texture Animation
def update_ta_current_frame(self, context):
    scene = context.scene
    slot = scene.ta_current_slot
    frame = scene.frame_current

    print("TexAnim: Updating current frame..")

    # Converts the texture animations from string to dict
    ta = json.loads(scene.texture_animations)

    # Resets the number if it's out of bounds
    if frame > scene.ta_max_frames - 1:
        scene.frame_current = scene.ta_max_frames - 1
        return

    scene.ta_current_frame_tex = ta[slot]["frames"][frame]["texture"]
    scene.ta_current_frame_delay = ta[slot]["frames"][frame]["delay"]
    uv = ta[slot]["frames"][frame]["uv"]
    scene.ta_current_frame_uv0 = (uv[3]["u"], 1 - uv[3]["v"])
    scene.ta_current_frame_uv1 = (uv[2]["u"], 1 - uv[2]["v"])
    scene.ta_current_frame_uv2 = (uv[1]["u"], 1 - uv[1]["v"])
    scene.ta_current_frame_uv3 = (uv[0]["u"], 1 - uv[0]["v"])

def update_ta_current_frame_tex(self, context):
    scene = context.scene
    slot = scene.ta_current_slot
    frame = scene.frame_current

    print("TexAnim: Updating current frame texture..")

    # Converts the texture animations from string to dict
    ta = json.loads(scene.texture_animations)
    # Sets the frame's texture
    ta[slot]["frames"][frame]["texture"] = scene.ta_current_frame_tex
    # Saves the string again
    scene.texture_animations = str(ta)

def update_ta_current_frame_delay(self, context):
    scene = context.scene
    slot = scene.ta_current_slot
    frame = scene.frame_current

    print("TexAnim: Updating current frame delay..")

    # Converts the texture animations from string to dict
    ta = json.loads(scene.texture_animations)
    # Sets the frame's delay/duration
    ta[slot]["frames"][frame]["delay"] = scene.ta_current_frame_delay
    # Saves the string again
    scene.texture_animations = str(ta)

def update_ta_current_frame_uv(context, num):
    scene = context.scene
    prop_str = "ta_current_frame_uv{}".format(num)
    slot = scene.ta_current_slot
    frame = scene.frame_current

    # Reverses the accessor since they're saved in reverse order
    num = [0, 1, 2, 3][::-1][num]

    print("TexAnim: Updating current frame UV for {}..".format(num))

    ta = json.loads(scene.texture_animations)
    ta[slot]["frames"][frame]["uv"][num]["u"] = getattr(scene, prop_str)[0]
    ta[slot]["frames"][frame]["uv"][num]["v"] = 1 - getattr(scene, prop_str)[1]
    scene.texture_animations = str(ta)

def copy_uv_to_frame(context):
    scene = context.scene
    # Ensure there's a selected object and it's a mesh
    if context.object and context.object.type == 'MESH':
        # Ensure the object is in edit mode to get the BMesh
        if context.object.mode == 'EDIT':
            bm = get_edit_bmesh(context.object)
            if not bm:
                print("Failed to get BMesh.")
                return False

            uv_layer = bm.loops.layers.uv.get("UVMap")
            if not uv_layer:
                msg_box("Please create a UV layer first", 'ERROR')
                return False

            sel_face = get_active_face(bm)
            if not sel_face:
                msg_box("Please select a face first", 'ERROR')
                return False

            # Assign UVs to the corresponding property
            for loop in sel_face.loops:
                uv = loop[uv_layer].uv
                # Map loop index to UV properties
                if loop.index == 0:
                    scene.ta_current_frame_uv0 = (uv[0], uv[1])
                elif loop.index == 1:
                    scene.ta_current_frame_uv1 = (uv[0], uv[1])
                elif loop.index == 2:
                    scene.ta_current_frame_uv2 = (uv[0], uv[1])
                elif loop.index == 3:
                    scene.ta_current_frame_uv3 = (uv[0], uv[1])

            return True
        else:
            msg_box("Object is not in edit mode", 'ERROR')
            return False
    else:
        print("No mesh object selected.")
        return False

def copy_frame_to_uv(context):
    obj = context.object
    scene = context.scene

    if not obj or obj.type != 'MESH':
        print("No mesh object selected.")
        return

    # Make sure we're dealing with the object in edit mode
    if obj.mode != 'EDIT':
        print("Object is not in edit mode.")
        msg_box("Object is not in edit mode.", "ERROR")
        return

    bm = bmesh.from_edit_mesh(obj.data)

    if not bm:
        print("Failed to retrieve BMesh.")
        msg_box("Failed to retrieve BMesh.", "ERROR")
        return

    uv_layer = bm.loops.layers.uv.get("UVMap")
    sel_face = get_active_face(bm)

    if not sel_face:
        msg_box("Please select a face first", "ERROR")
        return

    if not uv_layer:
        msg_box("Please create a UV layer first", "ERROR")
        return

    # Assuming the face is a quad. Adapt accordingly for tris or n-gons.
    uvs = [scene.ta_current_frame_uv0, scene.ta_current_frame_uv1,
           scene.ta_current_frame_uv2, scene.ta_current_frame_uv3]

    for lnum, loop in enumerate(sel_face.loops):
        if lnum < len(uvs):
            loop[uv_layer].uv = uvs[lnum]
        else:
            print(f"No UV coordinate set for loop {lnum}.")
