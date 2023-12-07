import bpy
from ..common import *
from .. import operators
from .hull import *

from ..operators import *

from bpy.props import (BoolProperty,
                       FloatVectorProperty, 
                       IntProperty
)

is_instance = bpy.props.BoolProperty(
        name = "Is Instance",
        default = False,
        description = "Object is an instanced mesh"
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
        row = box.row(align=True)
        row.operator("object.toggle_environment_map", text="Use Environment Map", icon='ARROW_LEFTRIGHT')
        row.operator("object.set_environment_map_color", text="Set EnvMap Color", icon='COLOR')
        row.operator("object.toggle_hide", text="Hide", icon='HIDE_ON' if obj.revolt.fin_hide else 'HIDE_OFF')
        row.operator("object.toggle_no_mirror", text="No Mirror")
        row.operator("object.toggle_no_lights", text="No Lights")
        row.operator("object.toggle_no_cam_coll", text="No Camera Collision")
        row.operator("object.toggle_no_obj_coll", text="No Object Collision")
        row.operator("object.set_instance_priority", text="Set Priority")
        row.operator("object.set_lod_bias", text="Unused")

        # Mirror properties
        row = box.row(align=True)
        box.label(text="Mirror Properties:")
        row.operator("object.toggle_mirror_plane", text="Is Mirror Plane")

        # Hull properties
        row = box.row(align=True)
        box.label(text="Hull Properties:")
        row.operator("hull.generate")
        row.operator("object.add_hull_sphere")
        
dprint