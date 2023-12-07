import bpy
from ..common import *

from bpy.props import StringProperty

class RVIO_PT_RevoltScenePanel(bpy.types.Panel):
    """ Panel for .w properties """
    bl_label = "Re-Volt .w Properties"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"

    def draw(self, context):
        props = context.scene.revolt
        layout = self.layout

        layout.prop(props, "texture_animations")
        
dprint