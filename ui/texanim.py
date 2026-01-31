import bpy
import bmesh
from .. import common
from ..common import texnum_to_label

class RVIO_PT_AnimModesPanel(bpy.types.Panel):
    bl_idname = "RVIO_PT_AnimModesPanel"
    bl_label = "Animation Mode"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "data"
    bl_options = {"HIDE_HEADER"}

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        # -------- Main top box --------
        box = layout.box()
        col = box.column(align=True)

        # ---- Limits / Slot selection ----
        col.prop(scene, "ta_max_slots", text="Slots Limit")
        col.prop(scene, "ta_current_slot", text="Current Slot")
        col.prop(scene, "ta_max_frames", text="Frames Limit")

        # ---- Preview + current frame/tex (same box) ----
        preview_box = box.box()
        pcol = preview_box.column(align=True)
        pcol.prop(scene, "ta_current_frame", text="Current Frame")
        pcol.prop(scene, "ta_current_frame_tex", text="Current Texture")

        prow = preview_box.row(align=True)
        prow.operator("texanim.prev_prev", text="", icon='TRIA_LEFT')
        prow.operator("texanim.copy_frame_to_uv", text="", icon='VIEWZOOM')          # Frame -> UV
        prow.operator("texanim.copy_uv_to_frame", text="", icon='IMPORT')           # UV -> Frame
        prow.operator("texanim.prev_next", text="", icon='TRIA_RIGHT')

        # ---- Assignment tools (same box) ----
        tools_box = box.box()
        tcol = tools_box.column(align=True)

        tcol.operator("texanim.assign_anim_slot", text="Assign Animation", icon='KEY_HLT')
        tcol.operator("texanim.clear_selected_faces", text="Remove Assign", icon='X')
        tcol.operator("texanim.clear_current_slot", text="Clear Slot", icon='TRASH')

        # -------- Transform animation box --------
        box = layout.box()
        row = box.row(align=True)
        row.prop(scene, "ta_frame_start")
        row.prop(scene, "ta_frame_end")

        row = box.row(align=True)
        row.label(text=f"Texture: {texnum_to_label(scene.ta_texture)} ({scene.ta_texture})")
        row.prop(scene, "ta_texture", text="")

        row = box.row(align=True)
        row.prop(scene, "ta_delay", text="Frame Time")

        row = box.row(align=True)
        row.operator("texanim.transform")

        # -------- Grid animation box --------
        box = layout.box()
        row = box.row(align=True)
        row.prop(scene, "ta_frame_start")

        row = box.row(align=True)
        row.prop(scene, "grid_x")
        row.prop(scene, "grid_y")

        row = box.row(align=True)
        row.label(text=f"Texture: {texnum_to_label(scene.ta_texture)} ({scene.ta_texture})")
        row.prop(scene, "ta_texture", text="")

        row = box.row(align=True)
        row.prop(scene, "ta_delay", text="Frame Time")

        row = box.row(align=True)
        row.operator("texanim.grid", icon="GRID")

        uv_row = preview_box.row(align=True)
        uv_row.label(text="UV0")
        uv_row.prop(scene, "ta_current_frame_uv0", index=0, text="U")
        uv_row.prop(scene, "ta_current_frame_uv0", index=1, text="V")

        uv_row = preview_box.row(align=True)
        uv_row.label(text="UV1")
        uv_row.prop(scene, "ta_current_frame_uv1", index=0, text="U")
        uv_row.prop(scene, "ta_current_frame_uv1", index=1, text="V")

        uv_row = preview_box.row(align=True)
        uv_row.label(text="UV2")
        uv_row.prop(scene, "ta_current_frame_uv2", index=0, text="U")
        uv_row.prop(scene, "ta_current_frame_uv2", index=1, text="V")

        uv_row = preview_box.row(align=True)
        uv_row.label(text="UV3")
        uv_row.prop(scene, "ta_current_frame_uv3", index=0, text="U")
        uv_row.prop(scene, "ta_current_frame_uv3", index=1, text="V")