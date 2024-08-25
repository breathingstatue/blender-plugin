import bpy
import bmesh

class RVIO_PT_AnimModesPanel(bpy.types.Panel):
    bl_idname = "RVIO_PT_AnimModesPanel"
    bl_label = "Animation Mode"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "object"
    
    def draw(self, context):
        pass
        layout = self.layout
        obj = context.object
        scene = context.scene
        
        box = layout.box()
        col = box.column(align=True)
        col.prop(scene, "ta_max_slots", text="Slots Limit")
        col.prop(scene, "ta_current_slot", text="Current Slot")
        col.prop(scene, "ta_max_frames", text="Frames Limit")
        col.prop(scene, "ta_current_frame", text="Current Frame")
        row = box.row(align=True)
        row.operator("texanim.prev_next")
        row.operator("texanim.copy_frame_to_uv", text="", icon='VIEWZOOM')
        row.operator("texanim.prev_prev")
        box = layout.box()
        row = box.row(align=True)
        row.prop(scene, "ta_frame_start")
        row.prop(scene, "ta_frame_end")
        row = box.row(align=True)
        row.prop(scene, "ta_current_frame_tex", icon="TEXTURE")
        row.prop(scene, "ta_delay", text="Frame Time")
        row = box.row(align=True)
        row.operator("texanim.transform")
        box = layout.box()
        row = box.row(align=True)
        row.prop(scene, "ta_frame_start")
        row = box.row(align=True)
        row.prop(scene, "grid_x")
        row.prop(scene, "grid_y")
        row = box.row(align=True)
        row.prop(scene, "ta_current_frame_tex", icon="TEXTURE")
        row.prop(scene, "ta_delay", text="Frame Time")
        row = box.row(align=True)
        row.operator("texanim.grid", icon="GRID")
        layout.operator("texanim.copy_uv_to_frame")
        row = layout.row()
        row = layout.row(align=True)
        row.prop(scene, "ta_current_frame_uv0")
        row.prop(scene, "ta_current_frame_uv1")
        row = layout.row()
        row = layout.row(align=True)
        row.prop(scene, "ta_current_frame_uv2")
        row.prop(scene, "ta_current_frame_uv3")