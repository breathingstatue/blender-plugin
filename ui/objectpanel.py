import bpy
import bmesh
from ..operators import *
from ..props.props_obj import *
from ..rvstruct import *
from bpy.props import (BoolProperty,
                       FloatVectorProperty, 
                       IntProperty
)

class RVIO_PT_RevoltObjectPanel(bpy.types.Panel):
    bl_label = "Revolt Object Properties"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "object"
    bl_options = {"HIDE_HEADER"}

    def draw(self, context):
        layout = self.layout
        obj = context.active_object

        if obj:
            col = layout.column()
            col.operator("object.toggle_environment_map", text="Environment Map On/Off")
            col.operator("object.set_environment_map_color", text="Set EnvMap Color")
    
        # Debug Properties
        box = layout.box()
        box.label(text="Debug Properties:")
        col = box.column(align=True)
        col.prop(context.object, "is_bcube", text="Object is a BigCube")
        col.prop(context.object, "is_cube", text="Object is a Cube")
        col.prop(context.object, "is_bbox", text="Object is a Boundary Box")
        col.prop(context.object, "ignore_ncp", text="Ignore for .ncp")

        # Instance properties
        box = layout.box()
        box.label(text="Instance Properties:")
        col = box.column(align=True)
        col.operator("object.toggle_model_rgb", text="Use Model Color")
        col.operator("object.toggle_fin_hide", text="Hide")
        col.operator("object.toggle_fin_priority", text="Instance Priority")
        col.prop(context.object, "fin_lod_bias", text="LoD Bias", slider=True)
        col.operator("object.reset_fin_lod_bias", text="Reset LoD Bias")
        col.operator("object.toggle_no_mirror", text="No Mirror Mode")
        col.operator("object.toggle_no_lights", text="Not affected by Lights")
        col.operator("object.toggle_no_cam_coll", text="No Camera Collision")
        col.operator("object.toggle_no_obj_coll", text="No Object Collision")

        # Mirror properties
        mirror_box = layout.box()
        mirror_box.label(text="Mirror Properties:")
        mirror_col = mirror_box.column(align=True)
        mirror_col.operator("object.toggle_mirror_plane", text="Is Mirror Plane")

        # Hull properties
        hull_box = layout.box()
        hull_box.label(text="Hull Properties:")
        hull_col = hull_box.column(align=True)
        hull_col.operator("hull.generate")