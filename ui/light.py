import bpy
import bmesh
from ..common import *
from .widgets import *
from .. import tools
from math import pi

from ..props.props_scene import RVSceneProperties

class RVIO_PT_RevoltLightPanel(bpy.types.Panel):
    bl_label = "Light and Shadow"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "object"
    bl_options = {"HIDE_HEADER"}

    def draw_header(self, context):
        self.layout.label(text="Light and Shadow")

    def draw(self, context):
        view = context.space_data
        obj = context.object
        props = context.scene.revolt

        # Initialize dirs with a default value
        dirs = ["", ""]
        
        # Warns if texture mode is not enabled
        widget_texture_mode(self)

        if obj and obj.select_get():
            # Checks if the object has a vertex color layer
            if widget_vertex_color_channel(self, obj):
                pass
            else:
                # Light orientation selection
                box = self.layout.box()
                box.label(text="Shade Object")
                row = box.row()
                row.prop(props.revolt, "light_orientation", text="Orientation")
                if props.light_orientation == "X":
                    dirs = ["Left", "Right"]
                elif props.light_orientation == "Y":
                    dirs = ["Front", "Back"]
                elif props.light_orientation == "Z":
                    dirs = ["Top", "Bottom"]

                # Headings
                row = box.row()
                row.label(text="Direction")
                row.label(text="Light")
                row.label(text="Intensity")
                
                # Ensure dirs has been set
                if dirs[0] and dirs[1]:
                
                    # Settings for the first light
                    row = box.row(align=True)
                    row.label(text=dirs[0])
                    row.prop(props, "light1", text="")
                    row.prop(props, "light_intensity1", text="")
                
                    # Settings for the second light
                    row = box.row(align=True)
                    row.label(text=dirs[1])
                    row.prop(props, "light2", text="")
                    row.prop(props, "light_intensity2", text="")

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
    
dprint