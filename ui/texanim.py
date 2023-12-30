import bpy
import bmesh

class RVIO_PT_AnimModesPanel(bpy.types.Panel):
    bl_idname = "RVIO_PT_AnimModesPanel"
    bl_label = "Animation Mode"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "object"

    def draw(self, context):
        layout = self.layout

        layout.operator("texanim.transform", icon="ARROW_LEFTRIGHT")
        layout.operator("texanim.grid", icon="MESH_GRID")

