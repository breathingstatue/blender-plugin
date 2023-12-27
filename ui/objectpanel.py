import bpy
import bmesh
from ..common import *
from ..operators import *
from .hull import *
from ..props.props_obj import RVObjectProperties
from ..rvstruct import *

from bpy.props import (BoolProperty,
                       FloatVectorProperty, 
                       IntProperty
)

class RVIO_PT_RevoltObjectPanel(bpy.types.Panel):
    bl_label = "Revolt Object Properties"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "object"

    def draw(self, context):
        layout = self.layout
        obj = context.object
        objprops = obj.revolt
        scene = context.scene


        if obj:
            col = layout.column()
            col.prop(obj, "is_instance", text="Is Instance")

        if obj and "revolt" in obj:
            col = layout.column()
            col.operator("object.toggle_environment_map", text="Toggle EnvMap", icon="MATERIAL_DATA")
        
        # Display the current color from EnvMapColorPickerProperties
        if hasattr(scene, 'envmap_color_picker'):
            layout.prop(scene.envmap_color_picker, "envmap_color", text="EnvMap Color")

        # Button to set environment map color
        col = layout.column()
        col.operator("object.set_environment_map_color", text="Set EnvMap Color")

        # Ignore NCP
        layout.operator("object.toggle_ignore_ncp", text="Toggle Ignore Collision (.ncp)")

        # Debug properties
        if objprops.is_bcube:
            box = layout.box()
            box.label(text="BigCube Properties:")
            row = box.row()
            row.operator("object.set_bcube_mesh_indices", text="Set Mesh Indices")
        
        # Instance properties
        box = layout.box()
        box.label(text="Instance Properties:")
        row = box.row(align=True)
        row.operator("object.pick_instance_color", text="Pick Color")
        row.operator("object.set_model_color", text="Set Colour", icon='COLOR')
        col = box.column(align=True)
        col.operator("object.toggle_no_mirror", text="Toggle No Mirror")
        col.operator("object.toggle_no_lights", text="Toggle No Lights")
        col.operator("object.toggle_no_cam_coll", text="Toggle No Camera Collision")
        col.operator("object.toggle_no_obj_coll", text="Toggle No Object Collision")
        col.operator("object.set_instance_priority", text="Set Instance Priority")
        col.operator("object.set_lod_bias", text="Set LOD Bias")

        # Mirror properties
        box.label(text="Mirror Properties:")
        row = box.row(align=True)
        row.operator("object.toggle_mirror_plane", text="Is Mirror Plane")

        # Hull properties
        box.label(text="Hull Properties:")
        row = box.row(align=True)
        row.operator("hull.generate")
        row.operator("object.add_hull_sphere")
        
dprint