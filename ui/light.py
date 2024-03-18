import bpy
import bmesh
from math import pi

class RVIO_PT_RevoltLightPanel(bpy.types.Panel):
    bl_label = "Light and Shadow"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "object"
    
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
        col = box.column(align=True)
        col.prop(scene, "shadow_quality")
        col.prop(scene, "shadow_resolution")
        col.prop(scene, "shadow_softness")
        layout.operator("lighttools.bake_shadow")
        layout.prop(scene, "shadow_table")

        # Light orientation selection
        box = layout.box()
        box.label(text="Light Sources")

        # Find the first two lights in the scene
        lights = [o for o in scene.objects if o.type == 'LIGHT']
        light1 = lights[0] if len(lights) > 0 else None
        light2 = lights[1] if len(lights) > 1 else None

        # UI for the first light
        if light1:
            box.label(text=f"Light 1: {light1.name}")
            row = box.row()
            row.label(text="Orientation X")
            row.prop(light1, "rotation_euler", index=0, text="")
            row = box.row()
            row.label(text="Orientation Y")
            row.prop(light1, "rotation_euler", index=1, text="")
            row = box.row()
            row.label(text="Orientation Z")
            row.prop(light1, "rotation_euler", index=2, text="")
            row = box.row()
            row.label(text="Intensity")
            row.prop(light1.data, "energy", text="")

        # UI for the second light
        if light2:
            box.label(text=f"Light 2: {light2.name}")
            row = box.row()
            row.label(text="Orientation X")
            row.prop(light2, "rotation_euler", index=0, text="")
            row = box.row()
            row.label(text="Orientation Y")
            row.prop(light2, "rotation_euler", index=1, text="")
            row = box.row()
            row.label(text="Orientation Z")
            row.prop(light2, "rotation_euler", index=2, text="")
            row = box.row()
            row.label(text="Intensity")
            row.prop(light2.data, "energy", text="")