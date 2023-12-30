import bpy
import bmesh

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
        box.label(text="Texture tools:")
        box.operator("helpers.textures_save")
        
        box = layout.box()
        box.label(text="Rename texture")
        box.operator("helpers.texture_rename")

        box = layout.box()
        box.label(text="Car tools:")
        box.operator("helpers.car_parameters_export")
