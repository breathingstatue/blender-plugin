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

from .common import TEX_PAGES_MAX, get_edit_bmesh, get_active_face, msg_box
from .common import TEX_ANIM_MAX, int_to_texture
from .rvstruct import TexAnimation, Frame


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

    ta = eval(scene.texture_animations)  # Convert string to dictionary

    # Ensure the current slot is within bounds
    if slot > scene.ta_max_slots - 1:
        scene.ta_current_slot = scene.ta_max_slots - 1
        return

    scene.texture_animations = str(ta)  # Save the texture animations
    scene.ta_max_frames = ta[slot]["frame_count"]  # Update the max frames
    update_ta_current_frame(self, context)  # Update the current frame


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


def update_ta_current_frame_uv(context, num):
    """Update the UV coordinates of the current frame."""
    scene = bpy.context.scene
    prop_str = f"ta_current_frame_uv{num}"
    slot = scene.ta_current_slot
    frame = scene.ta_current_frame

    # Reverse the accessor since they're saved in reverse order
    num = [0, 1, 2, 3][::-1][num]

    ta = eval(scene.texture_animations)
    ta[slot]["frames"][frame]["uv"][num]["u"] = getattr(scene, prop_str)[0]
    ta[slot]["frames"][frame]["uv"][num]["v"] = 1 - getattr(scene, prop_str)[1]
    scene.texture_animations = str(ta)  # Save the updated UVs

def copy_uv_to_frame(context):
    scene = context.scene
    obj = context.object

    if context.object.data:
        try:
            bm = bmesh.from_edit_mesh(obj.data)
            if bm is None:
                msg_box("Failed to access BMesh. Ensure the object is in Edit Mode.", "ERROR")
                return
            
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
        
        except RuntimeError as e:
            msg_box(f"An error occurred: {str(e)}", "ERROR")
    
    else:
        print("No object for UV anim")

def copy_frame_to_uv(context):
    scene = context.scene
    obj = context.object

    if obj.data:
        bm = get_edit_bmesh(obj)
        
        # Check if bm is None
        if bm is None:
            msg_box("No BMesh data available. Ensure the object is in edit mode and has a valid mesh.", "ERROR")
            return
        
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
        
        # Get the index of the material in the object's material slots
        material_index = obj.data.materials.find(material.name)
        
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
    else:
        print("No object for UV anim")

def find_matching_texture(texture_letter):
    # Remove the file extension if present in the texture letter
    texture_letter = texture_letter.replace(".bmp", "").lower()
    print(f"Looking for texture ending with: {texture_letter}")
    
    # Iterate through all images in bpy.data.images
    for image in bpy.data.images:
        image_name_lower = image.name.lower()
        base_name, extension = os.path.splitext(image_name_lower)
        print(f"Checking image: {image.name}, base_name: {base_name}, extension: {extension}")
        
        # Check if the base name ends with the texture letter
        if base_name.endswith(texture_letter):
            print(f"Found matching texture: {image.name}")
            return image

    return None

def find_material_using_texture(obj, texture_image):
    """Find a material on the object that uses the given texture image."""
    for material_slot in obj.material_slots:
        material = material_slot.material
        if material and material.use_nodes:
            for node in material.node_tree.nodes:
                if node.type == 'TEX_IMAGE' and node.image == texture_image:
                    return material
    return None