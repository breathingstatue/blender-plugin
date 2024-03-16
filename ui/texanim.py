import bpy
import bmesh
from ..operators import OBJECT_OT_add_texanim_uv, TexAnimTransform

class RVIO_PT_AnimModesPanel(bpy.types.Panel):
    bl_idname = "RVIO_PT_AnimModesPanel"
    bl_label = "Animation Mode"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "object"
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        layout.prop(scene, 'ta_max_slots', slider=True)
        layout.prop(scene, 'ta_max_frames', slider=True)
        layout.prop(scene, "ta_current_slot", icon="ANIM")
        layout.prop(scene, "ta_current_frame", text="Current Frame")
        layout.operator("object.add_texanim_uv", text="Add Animation UV Layer")


        box = layout.box()
        row = box.row(align=True)
        row.prop(scene, "rvio_frame_start")
        row.prop(scene, "rvio_frame_end")

        row = box.row()
        row.prop(scene, "delay", icon="PREVIEW_RANGE")
        row.prop(scene, "texture", icon="TEXTURE")


        layout.operator("texanim.transform", text="TexAnim based on UV coordinates")
        layout.operator("texanim.grid", text="Grid TexAnim")
