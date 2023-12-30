import bpy
import bmesh
import os
from ..operators import *

class RVGLAddonPreferences(bpy.types.AddonPreferences):
    bl_idname = __name__.split('.')[0]

    revolt_dir: bpy.props.StringProperty(
        name="RVGL Directory",
        subtype='DIR_PATH',
        default=""  # Set a default value
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "revolt_dir")

class RVIO_PT_RevoltSettingsPanel(bpy.types.Panel):
    bl_label = "RVGL Settings"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "output"
    bl_options = {"HIDE_HEADER"}

    def draw(self, context):
        addon_prefs = get_addon_preferences()
        layout = self.layout

        # Directory selection
        layout.label(text="Select RVGL Directory:")
        box = layout.box()
        box.operator("rvio.select_revolt_dir", text="Browse")
        # Tagging the area for a redraw
        for area in context.screen.areas:
            if area.type == 'PROPERTIES':
                area.tag_redraw()

        # Display current directory
        directory = addon_prefs.revolt_dir
        if directory:
            box.label(text=f"Current Directory: {directory}")
        else:
            box.label(text="No directory selected")
        
        # General import settings
        layout.label(text="Import:")
        layout.operator("rvio.read_car_parameters", text="Read Car Parameters")
        layout.separator()

        # General export settings
        scene = context.scene
        layout.label(text="Export:")
        layout.prop(scene, "triangulate_ngons_enabled")
        layout.prop(scene, "export_without_texture")
        layout.prop(scene, "apply_scale_on_export")
        layout.prop(scene, "apply_rotation_on_export")
        layout.separator()

        # PRM Export settings
        # layout.label("Export PRM (.prm/.m):")
        # layout.separator()

        # World Import settings
        layout.label(text="Import World (.w):")
        layout.prop(props, "w_parent_meshes")
        layout.prop(props, "w_import_bound_boxes")
        if props.w_import_bound_boxes:
            layout.prop(props, "w_bound_box_layers")
        layout.prop(props, "w_import_cubes")
        if props.w_import_cubes:
            layout.prop(props, "w_cube_layers")
        layout.prop(props, "w_import_big_cubes")
        if props.w_import_big_cubes:
            layout.prop(props, "w_big_cube_layers")
        layout.separator()

        # NCP Export settings
        layout.label(text="Export Collision (.ncp):")
        layout.prop(props, "ncp_export_selected")
        layout.prop(props, "ncp_export_collgrid")
        layout.prop(props, "ncp_collgrid_size")

