"""
Name:    ta_csv_out
Purpose: Exports texture animation data saved as csv files

Description:
Texture animations are usually contained within world files (.w).
This module provides an easy way to transfer texture animations from one
file to another, as well as edit them in an external spread sheet program.

"""
import bmesh
import importlib
from . import common

# Check if 'common' is already in locals to determine if this is a reload scenario
if "common" in locals():
    importlib.reload(common)

# Add specific imports from common as needed
# Example: from .common import specific_function, SpecificClass

def export_file(filepath, scene):

    ta = eval(scene.revolt.texture_animations)
    lines = [TA_CSV_HEADER]

    for a in range(scene.revolt.ta_max_slots):
        for f in range(ta[a]["frame_count"]):
            line = "{},{},{},{},{},{},{},{},{},{},{},{}".format(
                a,
                f,
                ta[a]["frames"][f]["texture"],
                ta[a]["frames"][f]["delay"],
                ta[a]["frames"][f]["uv"][0]["u"],
                ta[a]["frames"][f]["uv"][0]["v"],
                ta[a]["frames"][f]["uv"][1]["u"],
                ta[a]["frames"][f]["uv"][1]["v"],
                ta[a]["frames"][f]["uv"][2]["u"],
                ta[a]["frames"][f]["uv"][2]["v"],
                ta[a]["frames"][f]["uv"][3]["u"],
                ta[a]["frames"][f]["uv"][3]["v"],
            )
            lines.append(line)
        lines.append("")

    file = open(filepath, "w")
    file.write("\n".join(lines))
    file.close()
