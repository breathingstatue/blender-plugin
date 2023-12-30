"""
Name:    parameters_out
Purpose: Exporting cars parameters useful for the parameters.txt files

Description:
Prints most valuable car parameters into clipboard.

"""

import os
import bpy
import bmesh
import importlib
from bpy import context
from . import common

# Check if 'bpy' is already in locals to determine if this is a reload scenario
if "bpy" in locals():
    importlib.reload(common)

# Add specific imports from common as needed
# Example: from .common import specific_function, SpecificClass

def export_file(filepath = None, scene = None):
    """
    This function builds a parameters string for wheels and antenna locations 
    and puts it into clipboard.
    """
    params = ""
    # Proceed if there is main car body
    if "body.prm" in bpy.data.objects:
        body = bpy.data.objects["body.prm"]
        for child in body.children:
            location = to_revolt_coord(child.location)
            if "wheel" in child.name:
                w_num = 0
                if "wheelfr.prm" in child.name:
                    w_num = 1
                elif "wheelbl.prm" in child.name:
                    w_num = 2
                elif "wheelbr.prm" in child.name:
                    w_num = 3
                params += "WHEEL %d {\n" % w_num
                params += "Offset1\t %f %f %f \n}\n" % location
            elif "aerial" in child.name:
                params += "AERIAL {\n"
                params += "Offset\t %f %f %f \n}\n" % location
    
    bpy.context.window_manager.clipboard = params
