"""
Panel for setting vertex colors in Edit Mode.
If there is no vertex color layer, the user will be prompted to create one.
It includes buttons for setting vertex colors in different shades of grey and
a custom color which is chosen with a color picker.
"""

import bpy
import bmesh
from ..operators import *

class VertexColorPickerProperties(bpy.types.PropertyGroup):
    vertex_color: bpy.props.FloatVectorProperty(
        name="Vertex Color",
        subtype='COLOR',
        default=(1.0, 1.0, 1.0),  # Default to white
        min=0.0,
        max=1.0,
        description="Vertex color picker"
    )
    
class RVIO_PT_VertexPanel(bpy.types.Panel):
    bl_label = "Vertex Colors"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "object"
    bl_options = {"HIDE_HEADER"}

    def draw_header(self, context):
        self.layout.label(text="Vertex Colors")

    def draw(self, context):
        layout = self.layout
                        
        # Button for Creating Vertex Color Layer
        box = layout.box()
        box.operator("vertexcolor.create_layer", icon="COLOR", text="Create Vertex Color Layer")

        # Vertex Color Layer Selection
        box = layout.box()
        row = box.row()
        col = row.column(align=True)
        col.operator("vertexcolor.set", icon="ADD", text="Apply Color")
        col.operator("vertexcolor.remove", icon="REMOVE", text="Remove Color")

        # Add the color picker
        box = layout.box()
        box.label(text="Vertex Color Picker:")
        box.prop(color_props, "vertex_color", text="")

    # Preset Alphas
    def draw_alpha_presets(self, layout):
        alpha_presets = [(1.0, "Opaque"), (0.9, "90% Alpha"), (0.8, "80% Alpha"),
                        (0.7, "70% Alpha"), (0.6, "60% Alpha"), (0.5, "50% Alpha"),
                        (0.4, "40% Alpha"), (0.3, "30% Alpha"), (0.2, "20% Alpha"),
                        (0.1, "10% Alpha"), (0.0, "Transparent")]

        box = layout.box()
        box.label(text="Set Alpha:")
        for alpha, label in alpha_presets:
            op = box.operator("vertexcolor.set_alpha", text=label)
            op.alpha = alpha