import bpy

class RVIO_PT_RevoltViewLayerPanel(bpy.types.Panel):
    """Re-Volt Tools in View Layer Tab"""
    bl_label = "View Material"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "view_layer"
    bl_options = {"HIDE_HEADER"}

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        box = layout.box()
        box.label(text="Texture / Material")

        col = box.column(align=True)
        # 👇 No object/mesh used here – purely scene-level
        col.prop(scene, "material_choice")

        row = col.row(align=True)
        row.operator("object.assign_materials_auto", text="Set to All")

        col = box.column(align=True)
        col.operator("object.assign_texture", text="Car Skin")