"""
Name:    ta_csv_out
Purpose: Exports texture animation data saved as csv files

Description:
Texture animations are usually contained within world files (.w).
This module provides an easy way to transfer texture animations from one
file to another, as well as edit them in an external spread sheet program.

"""
import bmesh
import json
import importlib
from . import common

# Check if 'common' is already in locals to determine if this is a reload scenario
if "common" in locals():
    importlib.reload(common)

# Add specific imports from common as needed
# Example: from .common import specific_function, SpecificClass

def export_file(filepath, scene):
    lines = [TA_CSV_HEADER]

    for a in range(1, scene.ta_max_slots + 1):  # Starting from 1 to match "texan001", "texan002", etc.
        image_name = f"texan{a:03}"  # Generating the image name based on the current index
        image = bpy.data.images.get(image_name)  # Attempting to fetch the image by name

        if image:
            # If the image exists, retrieve its file path
            uv_image_path = image.filepath

        # Composing the line with the image name and its path or a placeholder text
        line = f"{image_name},{uv_image_path}"
        lines.append(line)

    # Adding a final line break for the CSV format
    lines.append("")

    # Writing the composed lines to the specified file path
    with open(filepath, "w") as file:
        file.write("\n".join(lines))
