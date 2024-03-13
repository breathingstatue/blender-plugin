import bpy
import bmesh
from ..operators import ButtonHullGenerate, ButtonHullSphere
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