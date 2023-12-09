import bpy
import bmesh
from ..common import *

class RVIO_PT_RevoltHelpersPanelMesh(bpy.types.Panel):
    bl_label = "Helpers"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "data"

    def draw_header(self, context):
        self.layout.label(text="Help")

    def draw(self, context):
        layout = self.layout

        box = layout.box()
        box.label(text="Properties:")
        col = box.column(align=True)
        col.operator("helpers.enable_material_mode", text="Material Preview", icon="MATERIAL")
        col.operator("helpers.enable_solid_mode", text="Solid Mode", icon="SHADING_SOLID")

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
        
dprint
