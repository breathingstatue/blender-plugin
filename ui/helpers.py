import bpy
import bmesh
from .. import operators

class RVIO_PT_RevoltHelpersPanelMesh(bpy.types.Panel):
    bl_label = "Helpers"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "output"

    def draw_header(self, context):
        pass

    def draw(self, context):
        layout = self.layout

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
        box.label(text="Texture tools:")
        box.operator("helpers.textures_save")
        
        box = layout.box()
        box.label(text="Rename texture")
        box.operator("helpers.texture_rename")
        
        box = layout.box()
        box.label(text="Use Texture Number")
        box.operator("helpers.use_texture_number")

        box = layout.box()
        box.label(text="Car tools:")
        box.operator("helpers.car_parameters_export")
