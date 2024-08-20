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
            box = layout.box()
            col = box.column(align=True)
            col.operator("mesh.vertex_color_and_alpha_setup", text="Create Vertex Colour (Alpha)")
            col.operator("vertexcolor.remove_layer", text="Remove Col/Alpha")
            col.prop(scene, "vertex_color_picker")
            col.operator("vertexcolor.set_color", text="Set Color")
            col.prop(scene, "vertex_alpha_percentage", text="Alpha Level")
            col.operator("vertexcolor.set_alpha", text="Set Alpha")
        else:
            box = layout.box()
            col = box.column(align=True)
            col.label(text="SWITCH TO EDIT MODE FOR VERTEX COLORS.")