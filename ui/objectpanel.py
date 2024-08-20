import bpy
import bmesh
from ..common import LOW_FLAG_OPTIONS, HIGH_FLAG_OPTIONS
from ..tools import get_high_flag_items
from ..operators import *
from ..rvstruct import *

class RVIO_PT_RevoltObjectPanel(bpy.types.Panel):
    bl_label = "Revolt Object Properties"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "object"
    bl_options = {"HIDE_HEADER"}

    def draw(self, context):
        layout = self.layout
        obj = context.active_object
        
        #Track Zone properties
        tz_box = layout.box()
        tz_box.label(text="Track Zone Properties")
        tz_col = tz_box.column(align=True)
        tz_col.prop(obj, "is_track_zone", text="Is Track Zone")
        if obj and obj.is_track_zone:
            tz_col.prop(obj, "track_zone_id", text="Track Zone ID", slider=True)
            
        #Trigger properties
        tri_box = layout.box()
        tri_box.label(text="Trigger Properties")
        tri_col = tri_box.column(align=True)
        if obj and obj.get("is_trigger"):

            # Draw Trigger Type
            tri_col.prop(obj, "trigger_type_enum", text="Type")

            # Get the trigger type
            trigger_type = int(obj.trigger_type_enum)

            # Get the appropriate flag options based on the trigger type
            low_flag_data = LOW_FLAG_OPTIONS.get(trigger_type)
            high_flag_data = HIGH_FLAG_OPTIONS.get(trigger_type)

            # If Trigger Type 2 or 5, use EnumProperty for selector
            if trigger_type in {2, 5}:
                tri_col.prop(obj, "low_flag_enum", text=low_flag_data["name"])
            else:
                tri_col.prop(obj, "flag_low", text=low_flag_data["name"] if low_flag_data else "Low Flag")

            # Display high flag only if it applies to this trigger type
            if high_flag_data:
                tri_col.prop(obj, "flag_high", text=high_flag_data["name"])
            else:
                tri_col.label(text="High Flag: N/A")
            
            tri_col.operator("object.duplicate_trigger")
            tri_col.operator("object.copy_trigger", text="Copy Trigger Values")
            tri_col.operator("object.paste_trigger", text="Paste Trigger Values")

        # Mirror properties
        mirror_box = layout.box()
        mirror_box.label(text="Mirror Properties:")
        mirror_col = mirror_box.column(align=True)
        mirror_col.prop(obj, "is_mirror_plane", text="Is Mirror Plane")
        mirror_col.prop(obj, "mirror_strength", text="Mirror Strength")

        # Hull properties
        hull_box = layout.box()
        hull_box.label(text="Hull Properties:")
        hull_col = hull_box.column(align=True)
        hull_col.operator("hull.generate")
        
        # Debug properties
        box = layout.box()
        box.label(text="Debug Properties:")
        col = box.column(align=True)
        col.prop(obj, "is_bcube", text="Object is a BigCube")
        col.prop(obj, "is_cube", text="Object is a Cube")
        col.prop(obj, "is_bbox", text="Object is a Boundary Box")
        col.prop(obj, "ignore_ncp", text="Ignore for .ncp")
        col.operator("object.set_bcube_mesh_indices")