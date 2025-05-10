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

        box = self.layout.box()
        box.label(text="Texture Tools:")
        box.operator("helpers.textures_save")
        
        box = self.layout.box()
        box.label(text="Rename Textures")
        box.operator("helpers.texture_rename")
        
        box = self.layout.box()
        box.label(text="Rename Selected Objects:")
        box.operator("helpers.rename_selected_objects")
        
        box = self.layout.box()
        box.label(text="Select by Data:")
        box.operator("helpers.select_by_data")
        
        box = self.layout.box()
        box.label(text="Select by Name:")
        box.operator("helpers.select_by_name")
        
        box = self.layout.box()
        box.label(text="Read Car Parameters")
        box.operator("rvio.read_car_parameters")
        
        # Directory selection
        box = self.layout.box()
        box.label(text="Select RVGL Directory:")
        box.operator("rvio.select_rvgl_dir", text="Browse")
        # Tagging the area for a redraw
        for area in context.screen.areas:
            if area.type == 'PROPERTIES':
                area.tag_redraw()

        # Display current directory
        rvgl_dir = context.scene.rvgl_dir
        directory = rvgl_dir
        if directory:
            box.label(text=f"Current Directory: {directory}")
        else:
            box.label(text="No directory selected")

        box = self.layout.box()
        box.label(text="RVGL:")
        box.operator("helpers.launch_rv")