import bpy
import bmesh
from math import pi

class RVIO_PT_RevoltLightPanel(bpy.types.Panel):
    bl_label = "Light and Shadow"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "world"
    bl_options = {"HIDE_HEADER"}
    
    @staticmethod
    def warn_texture_mode(layout):
        shading_type = None
        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':
                shading_type = area.spaces.active.shading.type
                break

        if shading_type and shading_type not in {'MATERIAL', 'RENDERED'}:
            layout.label(text="Tip: Change Shading Mode.", icon='INFO')

    def draw(self, context):
        obj = context.object
        scene = context.scene
        layout = self.layout

        self.warn_texture_mode(layout)
        box = layout.box()
        box.label(text="AUTO SHADING")
        col = box.column(align=True)
        col.operator("object.bake_vertex_batch", text="Bake Light to Vertex Colors")
        col.operator("object.batch_bake_vertex_to_env", text="Batch Bake Light to .fin Env")
        col.operator("object.bake_vertex_to_rgbmodelcolor", text="Bake Light to RGB Model")
        col.prop(scene, "car_shader_color")
        col.operator("object.car_auto_shader", icon='SHADING_RENDERED')

        box = layout.box()
        box.label(text="CAR SHADOW")
        col = box.column(align=True)
        col.prop(scene, "shadow_quality")
        col.prop(scene, "shadow_resolution")
        col.prop(scene, "shadow_strength")
        col.operator("lighttools.bake_shadow")
        col.prop(scene, "shadow_table")

