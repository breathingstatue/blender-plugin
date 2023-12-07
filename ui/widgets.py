"""
Widgets are little panel snippets that generally warn users if something isn't
set up correctly to use a feature. They return true if something isn't right.
They return false if everything is alright.
"""
import bpy
from ..common import *

def widget_texture_mode(self):
    if not texture_mode_enabled():
        props = bpy.context.scene.revolt
        box = self.layout.box()
        box.label(text="Preferred Shading Mode is not enabled.", icon='INFO')
        row = box.row()
        
        # Check user preference and provide button to switch to the preferred mode
        if props.prefer_tex_solid_mode:
            # If user prefers 'SOLID' mode
            row.operator("helpers.enable_solid_mode",
                         text="Enable Solid Mode",
                         icon="SHADING_SOLID")
        else:
            # If user prefers 'MATERIAL' mode or any other mode
            row.operator("helpers.enable_material_mode",
                         text="Enable Material Preview",
                         icon="MATERIAL")
        
        return True
    return False

def widget_vertex_color_channel(self, obj):
    if obj and obj.type == 'MESH':
        if not obj.data.vertex_colors:
            box = self.layout.box()
            box.label(text="No Vertex Color Layer.", icon='INFO')
            row = box.row()

            # The operator might require the object to be in Edit mode
            # Ensure the object is in the correct mode or inform the user
            if obj.mode == 'EDIT':
                row.operator("mesh.vertex_color_add", icon='PLUS',
                             text="Create Vertex Color Layer")
            else:
                row.label(text="Switch to Edit Mode to add Vertex Color Layer", icon='ERROR')
            return True
    return False

dprint