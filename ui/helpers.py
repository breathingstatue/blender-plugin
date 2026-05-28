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

        box = layout.box()
        box.label(text="Read Car Parameters")
        box.operator("rvio.read_car_parameters")

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
