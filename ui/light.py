import bpy
from ..common import *
from .widgets import *
from .. import tools

from ..props.props_scene import RVSceneProperties
from ..tools import ButtonBakeShadow

class RVIO_PT_RevoltLightPanel(bpy.types.Panel):
    bl_label = "Light and Shadow"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "object"
    bl_options = {"HIDE_HEADER"}

    def draw_header(self, context):
        self.layout.label(text="Light and Shadow")

    def draw(self, context):
        view = context.space_data
        obj = context.object
        props = context.scene.revolt

        # Warns if texture mode is not enabled
        widget_texture_mode(self)

        if obj and obj.select_get():
            # Checks if the object has a vertex color layer
            if widget_vertex_color_channel(self, obj):
                pass
            else:
                # Light orientation selection
                box = self.layout.box()
                box.label(text="Shade Object")
                row = box.row()
                row.prop(props, "light_orientation", text="Orientation")
                if props.light_orientation == "X":
                    dirs = ["Left", "Right"]
                if props.light_orientation == "Y":
                    dirs = ["Front", "Back"]
                if props.light_orientation == "Z":
                    dirs = ["Top", "Bottom"]
                # Headings
                row = box.row()
                row.label(text="Direction")
                row.label(text="Light")
                row.label(text="Intensity")
                # Settings for the first light
                row = box.row(align=True)
                row.label(text=dirs[0])
                row.prop(props, "light1", text="")
                row.prop(props, "light_intensity1", text="")
                # Settings for the second light
                row = box.row(align=True)
                row.label(text=dirs[1])
                row.prop(props, "light2", text="")
                row.prop(props, "light_intensity2", text="")
                # Bake button
                row = box.row()
                row.operator("lighttools.bakevertex",
                             text="Generate Shading",
                             icon="LIGHTPAINT")

class ButtonBakeLightToVertex(bpy.types.Operator):
    bl_idname = "lighttools.bakevertex"
    bl_label = "Bake light"
    bl_description = "Bakes the light to the active vertex color layer"

    def execute(self, context):
        tools.bake_vertex(self, context)
        return{"FINISHED"}
    
dprint