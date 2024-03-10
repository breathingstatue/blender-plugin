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
        scene = context.scene
        
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
        layout.label(text="Export:")
        layout.operator("export.triangulate_ngons", text="Triangluate Ngons")
        layout.operator("export.without_texture", text="Export w/o Texture")
        layout.operator("export.apply_scale", text="Apply Scale")
        layout.operator("export.apply_rotation", text= "Apply Rotation")
        layout.separator()

        # PRM Export settings
        # layout.label("Export PRM (.prm/.m):")
        # layout.separator()

        # World Import settings
        layout.label(text="Import World (.w):")
        layout.operator("rvio.toggle_w_parent_meshes", text="w_parent_meshes")
        layout.operator("rvio.toggle_w_import_bound_boxes", text="w_import_bound_boxes")
        layout.operator("rvio.toggle_w_import_cubes", text="w_import_cubes")
        layout.operator("rvio.toggle_w_import_big_cubes", text="w_import_big_cubes")
        layout.separator()

        # NCP Export settings
        layout.label(text="Export Collision (.ncp):")
        layout.operator("rvio.toggle_ncp_export_selected", text="ncp_export_selected")
        layout.operator("rvio.toggle_ncp_export_collgrid", text="ncp_export_collgrid")
        layout.operator("rvio.set_ncp_grid_size", text="ncp_collgrid_size")

