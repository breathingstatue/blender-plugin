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
        col.prop(scene, "ta_max_frames")
        col.prop(scene, "ta_max_slots")
        col.prop(scene, "ta_current_slot")
        col.prop(scene, "ta_delay")
        col.prop(scene, "ta_current_frame")
        
        # layout.operator("object.add_texanim_uv", text="Add Animation UV Layer")
        # layout.operator("uv.texanim_direction", text="Animation Direction")
        # layout.operator("texanim.transform", icon="UV", text="Transform Animation")
        
        # box = layout.box()
        # col = box.column(align=True)
        # col.prop(scene, "grid_x", slider=True)
        # col.prop(scene, "grid_y", slider=True)
        # col.operator("texanim.grid", icon="GRID", text="Grid Animation")
        
        # layout.prop(scene, "ta_max_slots", slider=True)
