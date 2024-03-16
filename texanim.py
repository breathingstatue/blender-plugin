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
    
from .common import TEX_PAGES_MAX, get_edit_bmesh, get_active_face, msg_box, TEX_ANIM_MAX
from .rvstruct import TexAnimation, Frame

def get_texture_items(self, context):
    items = []
    obj = context.active_object

    if not obj or not obj.material_slots:
        return items

    for mat_slot in obj.material_slots:
        mat = mat_slot.material
        if mat and mat.use_nodes:
            for node in mat.node_tree.nodes:
                if node.type == 'TEX_IMAGE':
                    tex_name = node.image.name if node.image else "Unnamed"
                    item = (tex_name, tex_name, f"Use texture: {tex_name}")
                    if item not in items:
                        items.append(item)
    return items

def update_ta_max_slots(self, context):
    scene = context.scene
    slot = scene.ta_current_slot
    frame = scene.ta_current_frame

    if scene.ta_max_slots > 0:
        print("TexAnim: Updating max slots..")

        ta = json.loads(scene.texture_animations)

        while len(ta) < scene.ta_max_slots:
            print("TexAnim: Creating new animation slot... ({}/{})".format(
                len(ta) + 1, scene.ta_max_slots)
            )
            ta.append(rvstruct.TexAnimation().as_dict())

        scene.texture_animations = json.dumps(ta)

def update_ta_max_frames(self, context):
    scene = context.scene
    slot = scene.ta_current_slot

    print("TexAnim: Updating max frames..")
    ta = json.loads(scene.texture_animations)
    ta[slot]["frame_count"] = scene.ta_max_frames

    # Creates new empty frames if there are none for the current slot
    while len(ta[slot]["frames"]) < scene.ta_max_frames:
        print("Creating new animation frame... ({}/{})".format(
            len(ta[slot]["frames"]) + 1, scene.ta_max_frames))

        new_frame = rvstruct.Frame().as_dict()
        ta[slot]["frames"].append(new_frame)

    scene.texture_animations = json.dumps(ta)

def update_ta_current_slot(self, context):
    scene = context.scene
    # Adjust for 0-based index only when accessing lists, ensuring it's never negative
    slot = max(scene.ta_current_slot - 1, 0)

    if scene.texture_animations:
        ta = json.loads(scene.texture_animations)

        if slot >= len(ta) or slot < 0:
            print("Invalid slot index.")
            return

        # Now you can use the adjusted 'slot' to access elements in 'ta'
        # Example: accessing 'frames' in the adjusted slot
        if 'frames' in ta[slot]:
            # Perform actions with the frames
            pass
        else:
            print(f"No frames available in slot {slot + 1}.")
    else:
        print("No texture animation data available.")

# Texture Animation
def update_ta_current_frame(self, context):
    scene = context.scene
    slot = scene.ta_current_slot - 1
    frame = scene.ta_current_frame
    maxframes = scene.ta_max_frames

    print("TexAnim: Updating current frame..")

    # Load the texture animations data
    ta = json.loads(scene.texture_animations)

    # Check if the slot is valid
    if slot < 0 or slot >= len(ta):
        print(f"Invalid slot index: {slot}.")
        return

    if frame >= 0 and (frame < maxframes or frame == maxframes):
        scene.ta_current_frame_tex = slot
        scene.ta_current_frame_delay = ta[slot]['frames'][frame]['delay']
        uv = ta[slot]['frames'][frame]['uv']
        # Assuming you want to update all UVs; adjust based on your needs
        scene.ta_current_frame_uv0 = (uv[0]['u'], uv[0]['v'])
        scene.ta_current_frame_uv1 = (uv[1]['u'], uv[1]['v'])
        scene.ta_current_frame_uv2 = (uv[2]['u'], uv[2]['v'])
        scene.ta_current_frame_uv3 = (uv[3]['u'], uv[3]['v'])
    else:
        print(f"Invalid frame index: {frame} for slot {slot}.")
    
    scene.texture_animations = json.dumps(ta)

def update_ta_current_frame_tex(self, context):
    scene = context.scene
    slot = scene.ta_current_slot - 1
    frame = scene.ta_current_frame - 1

    print("TexAnim: Updating current frame texture..")

    # Load texture animations data
    ta = json.loads(scene.texture_animations)

    # Validate slot index
    if not 0 <= slot < len(ta):
        print(f"Invalid slot index: {slot + 1}. Aborting update.")
        return

    # Validate frame index
    if 'frames' in ta[slot] and not 0 <= frame < len(ta[slot]["frames"]):
        print(f"Invalid frame index: {frame + 1} for slot {slot + 1}. Aborting update.")
        return

    # Update the frame's texture index
    ta[slot]["frames"][frame]["texture"] = scene.ta_current_frame_tex

    # Save the updated texture animations data
    scene.texture_animations = json.dumps(ta)
    

def update_ta_current_frame_delay(self, context):
    scene = context.scene
    # Adjust for zero-based indexing if necessary
    slot = scene.ta_current_slot - 1
    frame = scene.ta_current_frame - 1

    print("TexAnim: Updating current frame delay..")

    # Load texture animations data
    ta = json.loads(scene.texture_animations)

    # Validate slot index
    if not 0 <= slot < len(ta):
        print(f"Invalid slot index: {slot + 1}.")
        return

    # Validate frame index
    if not 0 <= frame < len(ta[slot]["frames"]):
        print(f"Invalid frame index: {frame + 1} for slot {slot + 1}.")
        return

    # Update the frame's delay/duration
    ta[slot]["frames"][frame]["delay"] = scene.ta_current_frame_delay

    # Save the updated texture animations data
    scene.texture_animations = json.dumps(ta)
    

def update_ta_current_frame_uv(context, num):
    scene = context.scene
    prop_str = "ta_current_frame_uv{}".format(num)
    slot = scene.ta_current_slot
    frame = scene.ta_current_frame

    # Reverses the accessor since they're saved in reverse order
    num = [0, 1, 2, 3][::-1][num]

    print("TexAnim: Updating current frame UV for {}..".format(num))

    ta = json.loads(scene.texture_animations)
    ta[slot]["frames"][frame]["uv"][num]["u"] = getattr(scene, prop_str)[0]
    ta[slot]["frames"][frame]["uv"][num]["v"] = 1 - getattr(scene, prop_str)[1]
    scene.texture_animations = json.dumps(ta)

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
