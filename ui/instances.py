import bpy

class RVIO_PT_RevoltInstancesPanel(bpy.types.Panel):
    bl_label = "Instances"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "object"
    bl_options = {"HIDE_HEADER"}

    def draw(self, context):
        layout = self.layout
        obj = context.object

        if obj:
            instance_count = sum(1 for obj in context.scene.objects if "is_instance" in obj and obj["is_instance"])
            layout.label(text=f"Instances: {instance_count}/1024")

            col = layout.column(align=True)
            col.operator("instances.set_instance_property", text="Mark as Instance")
            col.operator("instances.rem_instance_property", text="Remove Instance Property")
            col.operator("object.use_fin_col", text="Set Model Color")