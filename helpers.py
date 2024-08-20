import bpy
import bmesh
from .. import operators

class RVIO_PT_RevoltHelpersPanelMesh(bpy.types.Panel):
    bl_label = "Helpers"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "output"

    def draw(self, context):
        layout = self.layout

        # Directory selection
        layout.label(text="Select RVGL Directory:")
        box = layout.box()
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
        
        box = layout.box()
        box.label(text="Read Car Parameters")
        box.operator("rvio.read_car_parameters")

        box = layout.box()
        box.label(text="RVGL:")
        box.operator("helpers.launch_rv")
        
        box = layout.box()
        box.label(text="Select by Data:")
        box.operator("helpers.select_by_data")
        
        box = layout.box()
        box.label(text="Select by Name:")
        box.operator("helpers.select_by_name")

        box = layout.box()
        box.label(text="Rename Selected Objects:")
        box.operator("helpers.rename_selected_objects")
        
        box = layout.box()
        box.label(text="Rename texture")
        box.operator("helpers.texture_rename")

        box = layout.box()
        box.label(text="Texture tools:")
        box.operator("helpers.textures_save")