import bpy
import bmesh
import os
from ..operators import RVIO_OT_SelectRevoltDirectory

class RVIO_PT_RevoltSettingsPanel(bpy.types.Panel):
    bl_label = "RVGL Settings"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "output"
    bl_options = {"HIDE_HEADER"}

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        # General export settings
        layout.label(text="Export:")
        layout.prop(scene, "export_worldcut", text="Export WorldCut (.w)")
        if scene.export_worldcut:
            layout.prop(scene, "split_size_faces", slider=True)
            layout.label(text="Actual Split Size: {}".format(scene.actual_split_size))
        layout.prop(scene, "triangulate_ngons", text="Triangluate Ngons")
        layout.prop(scene, "use_tex_num", text="Export w/o Texture")
        layout.prop(scene, "apply_scale", text="Apply Scale")
        layout.prop(scene, "apply_rotation", text= "Apply Rotation")
        layout.prop(scene, "apply_translation", text= "Apply Translation")
        layout.separator()

        # PRM Export settings
        layout.label(text="Export Car (.prm):")
        layout.prop(scene, "export_camber", text="Copy Wheel Camber")
        layout.separator()

        # World Import settings
        layout.label(text="Import World (.w):")
        layout.prop(scene, "w_parent_meshes", text="w_parent_meshes")
        layout.prop(scene, "w_import_bound_boxes", text="w_import_bound_boxes")
        layout.prop(scene, "w_import_cubes", text="w_import_cubes")
        layout.prop(scene, "w_import_big_cubes", text="w_import_big_cubes")
        layout.separator()

        # NCP Export settings
        layout.label(text="Export Collision (.ncp):")
        layout.prop(scene, "ncp_export_selected", text="ncp_export_selected")
        layout.prop(scene, "ncp_export_collgrid", text="ncp_export_collgrid")
        layout.prop(scene, "ncp_collgrid_size", text="ncp_collgrid_size")

def update_actual_split_size(self, context):
    self["actual_split_size"] = self.split_size_faces * 2

def get_actual_split_size(self):
    return self.get("actual_split_size", self.split_size_faces * 2)
