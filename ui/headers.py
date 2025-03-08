import bpy
import bmesh
from ..common import *

class RVIO_PT_RevoltIOToolPanel(bpy.types.Panel):
    bl_label = "Import/Export"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "output"
    bl_options = {"HIDE_HEADER"}

    def draw(self, context):

        row = self.layout.row(align=True)
        row.operator("import_scene.revolt", text="Import", icon="IMPORT")
        row.operator("wm.select_default_texture", text="Export", icon="EXPORT")
        row.operator("export_scene.revolt_redo", text="Re-Export", icon="FILE_REFRESH")
        
        box = self.layout.box()
        box.label(text="Car tools:")
        box.operator("headers.copy_wheel_params", text="Copy Wheel Params")
        box.operator("headers.axle_message_box", text="Copy Axle Params")
        box.operator("headers.spring_message_box", text="Copy Spring Params")
        box.operator("headers.pin_message_box", text="Copy Pin Params")
        box.operator("headers.copy_aerial_params", text="Copy Aerial Params")