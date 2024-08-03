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
            instance_count = sum(1 for obj in context.scene.objects if obj.get("is_instance", False))
            col.label(text=f"Instances: {instance_count}/1024")
            col.operator("instances.set_instance_property", text="Mark as Instance")
            col.operator("instances.rem_instance_property", text="Remove Instance Property")
        if obj and getattr(obj, "is_instance", False):
            col.prop(obj, "fin_env", text="EnvMap")
            if obj.mode == 'EDIT':
                if getattr(obj, "fin_env", False):
                    try:
                        col.prop(obj, "fin_envcol", text="Fin EnvMap Color")
                    except SystemError as e:
                        col.label(text="Unable to access EnvMap Color in current mode.")
            else:
                col.label(text="Switch to Edit Mode for EnvMap Color.")
            col.prop(obj, "fin_model_rgb", text="Use Model Color")
            if obj.mode == 'EDIT':
                if getattr(obj, "fin_model_rgb", False):
                    try:
                        col.prop(obj, "fin_col", text="RGB Model Color")
                    except SystemError as e:
                        col.label(text="Unable to access Model Color in current mode.")
            else:
                col.label(text="Switch to Edit Mode for Model Color.")
            col.prop(obj, "fin_hide", text="Hide")
            col.prop(obj, "fin_priority", text="Fin Priority", slider=True)
            col.prop(obj, "fin_lod_bias", text="LoD Bias", slider=True)
            col.prop(obj, "fin_no_mirror", text="No Mirror Mode")
            col.prop(obj, "fin_no_lights", text="Not affected by Lights")
            col.prop(obj, "fin_no_cam_coll", text="No Camera Collision")
            col.prop(obj, "fin_no_obj_coll", text="No Object Collision")
        else:
            pass