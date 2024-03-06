import bpy
import bmesh
from ..operators import *
from ..props.props_obj import *
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
    bl_options = {"HIDE_HEADER"}

    def draw(self, context):
        layout = self.layout
        obj = context.active_object

        if obj:
            col = layout.column()
            col.operator("object.toggle_environment_map", text="Environment Map On/Off")
            col.operator("object.set_environment_map_color", text="Set EnvMap Color")
    
        # Ignore NCP
        layout.operator("object.toggle_ignore_ncp", text="Toggle Ignore Collision (.ncp)")

        # Debug properties
        if obj.revolt.is_bcube:
            box = layout.box()
            box.label(text="BigCube Properties:")
            col = box.column()
            col.operator("object.set_bcube_mesh_indices", text="Set Mesh Indices")
        
        # Instance properties
        box = layout.box()
        box.label(text="Instance Properties:")
        col = box.column(align=True)
        col.operator("object.toggle_no_mirror", text="Toggle No Mirror")
        col.operator("object.toggle_no_lights", text="Toggle No Lights")
        col.operator("object.toggle_no_cam_coll", text="Toggle No Camera Collision")
        col.operator("object.toggle_no_obj_coll", text="Toggle No Object Collision")

        # Mirror properties
        box.label(text="Mirror Properties:")
        col = box.column(align=True)
        col.operator("object.toggle_mirror_plane", text="Is Mirror Plane")

        # Hull properties
        box.label(text="Hull Properties:")
        col = box.column(align=True)
        col.operator("hull.generate")
        col.operator("object.add_hull_sphere")