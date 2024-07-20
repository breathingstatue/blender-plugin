import bpy
import bmesh
from ..operators import *
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

        # Instance properties
        box = layout.box()
        box.label(text="Instance Properties:")
        col = box.column(align=True)
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

        # Mirror properties
        mirror_box = layout.box()
        mirror_box.label(text="Mirror Properties:")
        mirror_col = mirror_box.column(align=True)
        mirror_col.prop(obj, "is_mirror_plane", text="Is Mirror Plane")

        # Hull properties
        hull_box = layout.box()
        hull_box.label(text="Hull Properties:")
        hull_col = hull_box.column(align=True)
        hull_col.operator("hull.generate")
        
        # Debug properties
        box = layout.box()
        box.label(text="Debug Properties:")
        col = box.column(align=True)
        col.prop(obj, "is_bcube", text="Object is a BigCube")
        col.prop(obj, "is_cube", text="Object is a Cube")
        col.prop(obj, "is_bbox", text="Object is a Boundary Box")
        col.prop(obj, "ignore_ncp", text="Ignore for .ncp")
        col.operator("object.set_bcube_mesh_indices")