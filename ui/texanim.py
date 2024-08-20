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
        scene = context.scene
        
        box = layout.box()
        col = box.column(align=True)
        col.operator("texanim.copy_uv_to_frame")
        col.operator("texanim.copy_frame_to_uv")
        col.prop(scene, "ta_max_frames")
        col.prop(scene, "ta_max_slots")
        col.operator("texanim.prev_next")
        col.operator("texanim.prev_prev")
        
        layout = self.layout
        row = layout.row(align=True)
        row.prop(scene, "ta_frame_start")
        row.prop(scene, "ta_frame_end")
        row = layout.row()
        row.prop(scene, "ta_texture", icon="TEXTURE")
        layout = self.layout
        layout.operator("texanim.transform")
        col = layout.column(align=True)
        col.prop(scene, "ta_delay")
        row = layout.row(align=True)
        row.prop(scene, "grid_x")
        row.prop(scene, "grid_y")
        layout.operator("texanim.grid", icon="GRID")
