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

        # Instance properties
        box = layout.box()
        box.label(text="Instance Properties:")
        col = box.column(align=True)
        if obj:
            instance_count = sum(1 for obj in context.scene.objects if "is_instance" in obj and obj["is_instance"])
            col.label(text=f"Instances: {instance_count}/1024")
            col.operator("instances.set_instance_property", text="Mark as Instance")
            col.operator("instances.rem_instance_property", text="Remove Instance Property")
        if getattr(obj, "is_instance", False):
            col.operator("object.use_fin_col", text="Set Model Color")
            col.prop(obj, "fin_env", text="EnvMap")
            col.operator("object.fin_envmap_color", text="EnvMap Color")
            col.prop(obj, "fin_model_rgb", text="Use Model Color")
            col.prop(obj, "fin_hide", text="Hide")
            col.prop(obj, "fin_priority", text="Fin Priority", slider=True)
            col.prop(obj, "fin_lod_bias", text="LoD Bias", slider=True)
            col.prop(obj, "fin_no_mirror", text="No Mirror Mode")
            col.prop(obj, "fin_no_lights", text="Not affected by Lights")
            col.prop(obj, "fin_no_cam_coll", text="No Camera Collision")
            col.prop(obj, "fin_no_obj_coll", text="No Object Collision")
        else:
            pass