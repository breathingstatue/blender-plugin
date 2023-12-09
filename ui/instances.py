import bpy
import bmesh
from ..common import *
from ..props.props_scene import RVSceneProperties
from .. import operators

class RVIO_PT_RevoltInstancesPanel(bpy.types.Panel):
    bl_label = "Instances"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "object"
    bl_options = {"HIDE_HEADER"}

    def draw(self, context):
        view = context.space_data
        obj = context.object
        props = context.scene.revolt
        layout = self.layout

        instance_count = len([obj for obj in context.scene.objects if hasattr(obj, "revolt") 
                              and getattr(obj, "revolt", None) is not None 
                              and getattr(obj.revolt, "is_instance", False)])
        layout.label(text="Instances: {}/1024".format(instance_count))
        layout.operator("helpers.select_by_data")

        col = layout.column(align=True)
        col.operator("object.rename_selected_objects")
        col.operator("helpers.texture_rename")
        col.operator("helpers.select_by_name")

        col = layout.column(align=True)
        col.operator("helpers.set_instance_property")
        col.operator("helpers.rem_instance_property")
        
dprint