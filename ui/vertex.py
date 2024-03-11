"""
Panel for setting vertex colors in Edit Mode.
If there is no vertex color layer, the user will be prompted to create one.
It includes buttons for setting vertex colors in different shades of grey and
a custom color which is chosen with a color picker.
"""

import bpy
import bmesh
from ..operators import *

class RVIO_PT_VertexPanel(bpy.types.Panel):
    bl_label = "Vertex Colors"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "object"
    bl_options = {"HIDE_HEADER"}

    def draw_header(self, context):
        self.layout.label(text="Vertex Colors")
        
    def draw(self, context):
        pass