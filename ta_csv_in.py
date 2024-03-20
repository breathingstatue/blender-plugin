"""
Name:    ta_csv_in
Purpose: Imports texture animation data saved as csv files

Description:
Texture animations are usually contained within world files (.w).
This module provides an easy way to transfer texture animations from one
file to another, as well as edit them in an external spread sheet program.

"""

import bmesh
import importlib
from . import common
from . import rvstruct

# Check if 'common' is already in locals to determine if this is a reload scenario
if "common" in locals():
    importlib.reload(common)
    importlib.reload(rvstruct)

from .common import TA_CSV_HEADER

def import_file(filepath, scene):
    f = open(filepath, "r")
    lines = f.readlines()
    f.close()

    if not TA_CSV_HEADER in lines[0]:
        common.queue_error(
            "reading texture animation file",
            "File does not include texture animation header."
        )
    # Removes the header
    lines = lines[1:]

    # Initializes an empty list for animations
    animations = []

    for line in lines:
        if line == "\n":
            continue
        values = line.split(",")
        slot_num = int(values[0])
        frame_num = int(values[1])
        frame_tex = int(values[2])
        frame_delay = float(values[3])
        u0, v0, u1, v1, u2, v2, u3, v3 = [float(c) for c in values[4:12]]

        # Ensure the slot exists in animations
        while len(animations) <= slot_num:
            animations.append(rvstruct.TexAnimation())

        # Since we're directly inserting frames, ensure slots are pre-initialized
        animation = animations[slot_num]
        while len(animation.frames) <= frame_num:
            animation.frames.append(rvstruct.Frame())  # Initialize with empty frames

        # Create and set the actual frame
        frame = animation.frames[frame_num]
        frame.texture = frame_tex
        frame.delay = frame_delay
        frame.uv = [rvstruct.UV(uv=(u0, v0)), rvstruct.UV(uv=(u1, v1)), rvstruct.UV(uv=(u2, v2)), rvstruct.UV(uv=(u3, v3))]

        # Update frame_count after all insertions
        animation.frame_count = len(animation.frames)

    # Converts animations to dictionary format and dumps to JSON string
    scene.texture_animations = json.dumps([a.as_dict() for a in animations])

    scene.ta_max_slots = len(animations)
