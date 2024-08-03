"""
Name:    texanim
Purpose: Provides operators and functions for the texture animation panel

Description:
Moved from operators and panels here to reduce script line amount

"""

import bmesh
import bpy
from . import common
from . import rvstruct

if "bpy" in locals():
    import importlib
    importlib.reload(common)
    
from .common import TEX_PAGES_MAX, get_edit_bmesh, get_active_face, msg_box, TEX_ANIM_MAX
from .rvstruct import TexAnimation, Frame


def update_ta_max_slots(self, context):
    scene = context.scene
    slot = scene.ta_current_slot
    frame = scene.ta_current_frame

    if scene.ta_max_slots > 0:
        print("TexAnim: Updating max slots..")

        # Converts the texture animations from string to dict
        ta = eval(scene.texture_animations)

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
    # frame = scene.ta_current_frame

    print("TexAnim: Updating max frames..")
    ta = eval(scene.texture_animations)
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
    frame = scene.ta_current_frame

    print("TexAnim: Updating current slot..")

    # Converts the texture animations from string to dict
    ta = eval(scene.texture_animations)

    # Resets the number if it's out of bounds
    if slot > scene.ta_max_slots - 1:
        scene.ta_current_slot = scene.ta_max_slots - 1
        return

    # Saves the texture animations
    scene.texture_animations = str(ta)

    # Updates the rest of the UI
    # scene.ta_max_frames = len(ta[slot]["frames"])
    scene.ta_max_frames = ta[slot]["frame_count"]
    # update_ta_max_frames(self, context)
    update_ta_current_frame(self, context)


# Texture Animation
def update_ta_current_frame(self, context):
    scene = context.scene
    slot = scene.ta_current_slot
    frame = scene.ta_current_frame

    print("TexAnim: Updating current frame..")

    # Converts the texture animations from string to dict
    ta = eval(scene.texture_animations)

    # Resets the number if it's out of bounds
    if frame > scene.ta_max_frames - 1:
        scene.ta_current_frame = scene.ta_max_frames - 1
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
    frame = scene.ta_current_frame

    print("TexAnim: Updating current frame texture..")

    # Converts the texture animations from string to dict
    ta = eval(scene.texture_animations)
    # Sets the frame's texture
    ta[slot]["frames"][frame]["texture"] = scene.ta_current_frame_tex
    # Saves the string again
    scene.texture_animations = str(ta)


def update_ta_current_frame_delay(self, context):
    scene = context.scene
    slot = scene.ta_current_slot
    frame = scene.ta_current_frame

    print("TexAnim: Updating current frame delay..")

    # Converts the texture animations from string to dict
    ta = eval(scene.texture_animations)
    # Sets the frame's delay/duration
    ta[slot]["frames"][frame]["delay"] = scene.ta_current_frame_delay
    # Saves the string again
    scene.texture_animations = str(ta)


def update_ta_current_frame_uv(context, num):
    scene = bpy.context.scene
    prop_str = "ta_current_frame_uv{}".format(num)
    slot = scene.ta_current_slot
    frame = scene.ta_current_frame

    # Reverses the accessor since they're saved in reverse order
    num = [0, 1, 2, 3][::-1][num]

    print("TexAnim: Updating current frame UV for {}..".format(num))

    ta = eval(scene.texture_animations)
    ta[slot]["frames"][frame]["uv"][num]["u"] = getattr(scene, prop_str)[0]
    ta[slot]["frames"][frame]["uv"][num]["v"] = 1 - getattr(scene, prop_str)[1]
    scene.texture_animations = str(ta)


def copy_uv_to_frame(context):
    scene = context.scene
    # Copies over UV coordinates from the mesh
    if context.object.data:
        bm = get_edit_bmesh(context.object)
        uv_layer = bm.loops.layers.uv.get("UVMap")
        sel_face = get_active_face(bm)
        if not sel_face:
            msg_box("Please select a face first")
            return
        if not uv_layer:
            msg_box("Please create a UV layer first")
            return
        for lnum in range(len(sel_face.loops)):
            uv = sel_face.loops[lnum][uv_layer].uv
            if lnum == 0:
                scene.ta_current_frame_uv0 = (uv[0], uv[1])
            elif lnum == 1:
                scene.ta_current_frame_uv1 = (uv[0], uv[1])
            elif lnum == 2:
                scene.ta_current_frame_uv2 = (uv[0], uv[1])
            elif lnum == 3:
                scene.ta_current_frame_uv3 = (uv[0], uv[1])
    else:
        print("No object for UV anim")


def copy_frame_to_uv(context):
    scene = context.scene
    if context.object.data:
        bm = get_edit_bmesh(context.object)
        uv_layer = bm.loops.layers.uv.get("UVMap")
        sel_face = get_active_face(bm)
        if not sel_face:
            msg_box("Please select a face first")
            return
        if not uv_layer:
            msg_box("Please create a UV layer first")
            return
        for lnum in range(len(sel_face.loops)):
            uv0 = scene.ta_current_frame_uv0
            uv1 = scene.ta_current_frame_uv1
            uv2 = scene.ta_current_frame_uv2
            uv3 = scene.ta_current_frame_uv3
            if lnum == 0:
                sel_face.loops[lnum][uv_layer].uv = uv0
            elif lnum == 1:
                sel_face.loops[lnum][uv_layer].uv = uv1
            elif lnum == 2:
                sel_face.loops[lnum][uv_layer].uv = uv2
            elif lnum == 3:
                sel_face.loops[lnum][uv_layer].uv = uv3
    else:
        print("No object for UV anim")