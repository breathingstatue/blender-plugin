import bpy
import bmesh
from ..common import LOW_FLAG_OPTIONS, HIGH_FLAG_OPTIONS, to_revolt_scale
from ..fob_subtypes import OBJECT_TYPE_NAMES, OBJECT_SUBTYPE_DESCRIPTIONS, OBJECT_SUBTYPE_VALUES
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
        scene = context.scene
        
        #Track Zone properties
        tz_box = layout.box()
        tz_box.label(text="Track Zone Properties")
        tz_col = tz_box.column(align=True)
        if obj and obj.is_track_zone:
            tz_col.prop(obj, "track_zone_id", text="Track Zone ID", slider=True)
            tz_col.operator("object.duplicate_track_zone", text="Duplicate Track Zone", icon="DUPLICATE")

        # Light properties
        if obj and (getattr(obj, "is_light", False) or obj.get("is_light")):
            lbox = layout.box()
            lbox.label(text="Light Properties")
            lcol = lbox.column(align=True)
            lcol.prop(obj, "light_type", text="Type")
            lcol.prop(obj, "light_world_mode", text="World/Objects")
            lcol.prop(obj, "light_rgb", text="RGB")
            lcol.prop(obj, "light_reach", text="Reach")
            lcol.prop(obj, "light_flicker", text="Flicker")
            lcol.prop(obj, "light_flicker_speed", text="Flicker Speed")
            if obj.light_type in {"SPOT", "SPOT_NORMAL"}:
                lcol.prop(obj, "light_cone", text="Cone")
            if obj.light_type == "SQUARE_SHADOW":
                size = (
                    to_revolt_scale(obj.scale.x),
                    to_revolt_scale(obj.scale.y),
                    to_revolt_scale(obj.scale.z),
                )
                lcol.label(text=f"Size (from scale): {size[0]:.1f} {size[1]:.1f} {size[2]:.1f}")
            lcol.operator("object.duplicate_light", text="Duplicate Light", icon="DUPLICATE")

        # FOB Object properties
        if obj.get("is_fob_object"):
            obj_type_id = obj.get("fob_type", -1)
            if obj_type_id not in OBJECT_TYPE_NAMES:
                return  # Unknown type   skip entirely

            obj_type_name = OBJECT_TYPE_NAMES[obj_type_id]
            labels = OBJECT_SUBTYPE_DESCRIPTIONS.get(obj_type_id, [])
            subtype_values = OBJECT_SUBTYPE_VALUES.get(obj_type_id, {})

            fob_box = layout.box()
            fob_box.label(text="FOB Object Properties")
            col = fob_box.column(align=True)

            col.label(text=f"Object Type: {obj_type_name}")
            col.prop(obj, "fob_type", text="Object ID")

            for i in range(4):
                if i not in subtype_values:
                    continue

                allowed = subtype_values[i]
                if not isinstance(allowed, list) or not allowed:
                    continue

                subtype_prop = f"fob_subtype_{i+1}"
                subtype_value = obj.get(subtype_prop, 0)
                label = labels[i] if i < len(labels) and labels[i] else f"Subtype {i+1}"

                row = col.row()
                row.prop(obj, subtype_prop, text=label)

                # String list: display name or invalid
                if all(isinstance(v, str) for v in allowed):
                    if 0 <= subtype_value < len(allowed):
                        row.label(text=f"{allowed[subtype_value]} ({subtype_value})")
                    else:
                        row.label(text=f"(Invalid: {subtype_value})")

                # Integer range: show range and flag invalids
                elif all(isinstance(v, int) for v in allowed):
                    min_val = min(allowed)
                    max_val = max(allowed)
                    if subtype_value < min_val or subtype_value > max_val:
                        row.label(text=f"(Invalid: {subtype_value}) [{min_val}-{max_val}]")
                    else:
                        row.label(text=f"{subtype_value} [{min_val}-{max_val}]")

                # Fallback
                else:
                    row.label(text=str(subtype_value))

            col.operator("object.duplicate_fob", icon="DUPLICATE")

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
            
        # Visibox properties
        if obj and getattr(obj, "is_visibox", False):
            visibox_box = layout.box()
            visibox_box.label(text="Visibox Properties")
            visibox_col = visibox_box.column(align=True)
            visibox_col.prop(obj, "visibox_type", text="Type")
            visibox_col.prop(obj, "visibox_id", text="ID", slider=True)
            visibox_col.operator("object.duplicate_visibox", icon="DUPLICATE", text="Duplicate Visibox")

        # Mirror properties
        mirror_box = layout.box()
        mirror_box.label(text="Mirror Properties:")
        mirror_col = mirror_box.column(align=True)
        mirror_col.prop(obj, "is_mirror_plane", text="Is Mirror Plane")

        # Hull Spheres
        hull_box = layout.box()
        hull_box.label(text="Hull Properties:")
        hull_col = hull_box.column(align=True)
        hull_col.operator("hull.generate", text="Generate Convex Hull")
        hull_box.prop(obj, "is_hull_sphere", text="is Hull Sphere")
        hull_box.prop(obj, "is_hull_convex", text="is Hull Convex")
        
        # Model properties
        model_box = layout.box()
        model_box.label(text="Model Properties:")
        model_col = model_box.column(align=True)
        model_col.operator("object.mark_as_model", text="Mark/Unmark as .m Model")
        model_col.prop(obj, "is_model", text="Is Model (.m)")
        
        # Debug properties
        box = layout.box()
        box.label(text="Debug Properties:")
        col = box.column(align=True)
        col.prop(obj, "is_bcube", text="Object is a BigCube")
        col.prop(obj, "is_cube", text="Object is a Cube")
        col.prop(obj, "is_bbox", text="Object is a Boundary Box")
        col.prop(obj, "ignore_ncp", text="Ignore for .ncp")
        col.operator("object.set_bcube_mesh_indices")
        
        
def get_subtype_label(obj_type, subtype_index, raw_value):
    subtype_dict = OBJECT_SUBTYPE_VALUES.get(obj_type, {}).get(subtype_index)
    if isinstance(subtype_dict, list) and 0 <= raw_value < len(subtype_dict):
        return f"{subtype_dict[raw_value]} ({raw_value})"
    return str(raw_value)
