import bpy
import bmesh
from ..operators import *

class RVIO_PT_RevoltInstancesPanel(bpy.types.Panel):
    bl_label = "Instances"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "object"
    bl_options = {"HIDE_HEADER"}

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        # Count only objects with 'is_instance' set to True
        instance_count = sum(1 for obj in scene.objects if getattr(obj, "is_instance", False))

        layout.label(text=f"Instances: {instance_count}/1024")

        col = layout.column(align=True)
        col.operator("instances.set_instance_property")
        col.operator("instances.rem_instance_property")