import bpy
import bmesh
import os
from ..operators import RVIO_OT_SelectRevoltDirectory
from ..props.props_scene import RVSceneProperties

class RVIO_PT_RevoltSettingsPanel(bpy.types.Panel):
    bl_label = "RVGL Settings"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "output"
    bl_options = {"HIDE_HEADER"}

    def draw(self, context):
        layout = self.layout
        props = context.scene.revolt
        
        # Directory selection
        layout.label(text="Select RVGL Directory:")
        box = layout.box()
        box.operator("rvio.select_rvgl_dir", text="Browse")
        # Tagging the area for a redraw
        for area in context.screen.areas:
            if area.type == 'PROPERTIES':
                area.tag_redraw()

        # Display current directory
        rvgl_dir = context.scene.rvgl_dir
        directory = rvgl_dir
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
        layout.operator("rvio.toggle_w_parent_meshes", text="w_parent_meshes")
        layout.operator("rvio.toggle_w_import_bound_boxes", text="w_import_bound_boxes")
        if props.w_import_bound_boxes:
            layout.operator("rvio.set_bound_box_collection", text="w_bound_boxes_collections")
        layout.operator("rvio.toggle_w_import_cubes", text="w_import_cubes")
        if props.w_import_cubes:
            layout.operator("rvio.set_cube_collection", text="cubes_collections")
        layout.operator("rvio.toggle_w_import_big_cubes", text="w_import_big_cubes")
        if props.w_import_big_cubes:
            layout.operator("rvio.set_big_cube_collection", text="w_big_cube_collections")
        layout.separator()

        # NCP Export settings
        layout.label(text="Export Collision (.ncp):")
        layout.operator("rvio.toggle_ncp_export_selected", text="ncp_export_selected")
        layout.operator("rvio.toggle_ncp_export_collgrid", text="ncp_export_collgrid")
        layout.operator("rvio.set_ncp_grid_size", text="ncp_collgrid_size")

