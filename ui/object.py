import bpy
from ..common import *

class RevoltObjectPanel(bpy.types.Panel):
    bl_label = "Re-Volt Object Properties"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "object"


    def draw(self, context):
        layout = self.layout
        obj = context.object
        objprops = obj.revolt

        layout.label(text="Re-Volt Properties")

        # NCP properties
        box = layout.box()
        box.label(text="NCP Properties:")
        row = box.row()
        row.prop(objprops, "ignore_ncp")

        # Debug properties
        if objprops.is_bcube:
            box = layout.box()
            box.label(text="BigCube Properties:")
            row = box.row()
            row.prop(objprops, "bcube_mesh_indices")
        
        # Instance properties
        box = layout.box()
        box.label(text="Instance Properties:")
        box.prop(objprops, "is_instance")

        if objprops.is_instance:
            row = box.row(align=True)
            row.prop(context.object.revolt, "fin_model_rgb", text="Model Color")
            row.prop(context.object.revolt, "fin_col", text="")
            row = box.row(align=True)
            row.prop(context.object.revolt, "fin_env", text="EnvColor")
            row.prop(context.object.revolt, "fin_envcol", text="")
            box.prop(context.object.revolt, "fin_hide")
            box.prop(context.object.revolt, "fin_no_mirror")
            box.prop(context.object.revolt, "fin_no_lights")
            box.prop(context.object.revolt, "fin_no_cam_coll")
            box.prop(context.object.revolt, "fin_no_obj_coll")
            box.prop(context.object.revolt, "fin_priority")
            box.prop(context.object.revolt, "fin_lod_bias")

        # Mirror properties
        box = layout.box()
        box.label(text="Mirror Properties:")
        box.prop(objprops, "is_mirror_plane")

        # InstanceHull properties
        box = layout.box()
        box.label(text="Hull Properties:")
        box.prop(objprops, "is_hull_convex")
        box.prop(objprops, "is_hull_sphere")
        
dprint