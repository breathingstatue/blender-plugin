import bpy
from ..common import *
from .. import tools

from ..tools import generate_chull

class RVIO_PT_RevoltHullPanel(bpy.types.Panel):
    bl_label = "Hulls"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "object"
    bl_options = {"HIDE_HEADER"}

    # @classmethod
    # def poll(self, context):
    #     return context.object and len(context.selected_objects) >= 1 and context.object.type == "MESH"

    def draw_header(self, context):
        self.layout.label(text="Hulls")

    def draw(self, context):
        view = context.space_data
        obj = context.object
        props = context.scene.revolt
        layout = self.layout

        layout.operator("hull.generate", icon="SPHERE")
        layout.operator("object.add_hull_sphere", icon="MATSPHERE", text="Create Hull Sphere")

    
class ButtonHullGenerate(bpy.types.Operator):
    bl_idname = "hull.generate"
    bl_label = "Generate Convex Hull"
    bl_description = "Generates a convex hull from the selected object"

    @classmethod
    def poll(cls, context):
        return context.object is not None and context.object.type == 'MESH'

    def execute(self, context):
        try:
            tools.generate_chull(context)
        except Exception as e:
            self.report({'ERROR'}, f"Failed to generate convex hull: {e}")
            return {'CANCELLED'}

        return {'FINISHED'}


class OBJECT_OT_add_revolt_hull_sphere(bpy.types.Operator):
    bl_idname = "object.add_hull_sphere"
    bl_label = "Hull Sphere"
    bl_options = {'UNDO'}
    
    def execute(self, context):
        from ..hul_in import create_sphere
        from ..common import to_revolt_scale

        # Create the sphere
        obj = create_sphere(context.scene, (0, 0, 0), to_revolt_scale(0.1), "Hull Sphere")
        
        # Set the object location to the cursor's location
        obj.location = bpy.context.scene.cursor.location

        # Select the object and make it the active object
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj

        return {'FINISHED'}
    
dprint