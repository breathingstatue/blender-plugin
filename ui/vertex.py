"""
Panel for setting vertex colors in Edit Mode.
If there is no vertex color layer, the user will be prompted to create one.
It includes buttons for setting vertex colors in different shades of grey and
a custom color which is chosen with a color picker.
"""

import bpy
import bmesh

class RVIO_PT_VertexPanel(bpy.types.Panel):
    bl_label = "Vertex Colors"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "object"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        obj = context.object
        
        if obj.mode == 'EDIT':
            layout.operator("mesh.vertex_color_and_alpha_setup", text="Create Vertex Colour (Alpha)")
            layout.operator("vertexcolor.remove_layer", text="Remove Col/Alpha")
            layout.prop(scene, "vertex_color_picker")
            layout.operator("vertexcolor.set_color", text="Set Color")
            layout.prop(scene, "vertex_alpha_percentage", text="Alpha Level")
            layout.operator("vertexcolor.set_alpha", text="Set Alpha")
        else:
            layout.label(text="SWITCH TO EDIT MODE FOR VERTEX COLORS.")