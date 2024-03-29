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
        
        layout.operator("vertexcolor.create_layer")
        layout.prop(scene, 'vertex_color_picker', text="Choose Color")
        layout.operator("vertexcolor.set_color")
        layout.operator("vertexcolor.remove_layer")