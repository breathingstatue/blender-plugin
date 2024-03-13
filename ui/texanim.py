import bpy
import bmesh
from ..operators import OBJECT_OT_add_texanim_uv, RVIO_OT_TexAnimTransform

class RVIO_PT_AnimModesPanel(bpy.types.Panel):
    bl_idname = "RVIO_PT_AnimModesPanel"
    bl_label = "Animation Mode"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "object"
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene

        layout.prop(scene, 'ta_max_frames', slider=True)
        layout.prop(scene, 'ta_max_slots', slider=True)
        layout.prop(scene, 'frame_duration', slider=True)
        layout.operator("object.add_texanim_uv", text="Add Animation UV Layer")
        layout.operator("rvio.texanim_transform", text="Send UV AnimLayers for Export")
