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

        # Light orientation selection
        box = layout.box()
        box.label(text="Shade Object")

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

class ButtonBakeLightToVertex(bpy.types.Operator):
    bl_idname = "lighttools.bakevertex"
    bl_label = "Bake light"
    bl_description = "Bakes the light to the active vertex color layer"

    def bake_vertex(self, context):
        # Accessing props within the method
        props = context.scene.revolt

        # Set scene to render to vertex color
        rd = context.scene.render
        rd.use_bake_to_vertex_color = True
        rd.use_textures = False

        shade_obj = context.object

        if props.light1 != "None":
            # Creates new lamp datablock
            lamp_data1 = bpy.data.lights.new(
                name="ShadeLight1",
                type=props.light1
            )
            # Creates new object with our lamp datablock
            lamp_object1 = bpy.data.objects.new(
                name="ShadeLight1",
                object_data=lamp_data1
            )
            lamp_object1.data.energy = props.light_intensity1
            # Links lamp object to the scene so it'll appear in this scene
            bpy.context.collection.objects.link(lamp_object1)

            # Rotates light
            if props.light_orientation == "X":
                lamp_object1.location = (-1.0, 0, 0)
                lamp_object1.rotation_euler = (0, -pi/2, 0)
            elif props.light_orientation == "Y":
                lamp_object1.location = (0, 1.0, 0)
                lamp_object1.rotation_euler = (-pi/2, 0, 0)
            elif props.light_orientation == "Z":
                lamp_object1.location = (0, 0, 1.0)

        if props.light2 != "None":
            lamp_data2 = bpy.data.lights.new(
                name="ShadeLight2",
                type=props.light2
            )
            lamp_object2 = bpy.data.objects.new(
                name="ShadeLight2",
                object_data=lamp_data2
            )
            lamp_object2.data.energy = props.light_intensity2
            bpy.context.collection.objects.link(lamp_object2)

            # rotate light
            if props.light_orientation == "X":
                lamp_object2.location = (1.0, 0, 0)
                lamp_object2.rotation_euler = (0, pi/2, 0)
            elif props.light_orientation == "Y":
                lamp_object2.location = (0, -1.0, 0)
                lamp_object2.rotation_euler = (pi/2, 0, 0)
            elif props.light_orientation == "Z":
                lamp_object2.location = (0, 0, -1.0)
                lamp_object2.rotation_euler = (pi, 0, 0)

        # bake the image
        bpy.ops.object.bake_image()

        # select lights and delete them
        shade_obj.select_set(False)
        if props.light1 != "None":
            lamp_object1.select_set(True)
        if props.light2 != "None":
            lamp_object2.select_set(True)
        bpy.ops.object.delete()

        # Select the object again
        bpy.context.view_layer.objects.active = shade_obj
        shade_obj.select_set(True)

    def execute(self, context):
        self.bake_vertex(context)
        return {"FINISHED"}