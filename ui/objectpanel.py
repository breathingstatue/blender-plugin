import bpy
import bmesh
from ..common import LOW_FLAG_OPTIONS, HIGH_FLAG_OPTIONS, to_revolt_scale
from ..fob_subtypes import OBJECT_TYPE_NAMES, OBJECT_SUBTYPE_DESCRIPTIONS, OBJECT_SUBTYPE_VALUES, fob_subtype_range_property_name
from ..tools import get_high_flag_items
from ..operators import *
from ..rvstruct import *


def _truncate_ui_text(text, limit=63):
    text = str(text)
    return text if len(text) <= limit else text[: limit - 1] + "\u2026"


def _is_int_sequence(values):
    return isinstance(values, list) and values and all(isinstance(v, int) for v in values)


def _is_str_sequence(values):
    return isinstance(values, list) and values and all(isinstance(v, str) for v in values)


def _is_contiguous_int_range(values):
    if not _is_int_sequence(values):
        return False
    if len(values) <= 1:
        return True
    sorted_vals = sorted(values)
    return sorted_vals == list(range(sorted_vals[0], sorted_vals[-1] + 1))


def _connection_values(obj, attr_name, key_name):
    values = list(getattr(obj, attr_name, obj.get(key_name, [-1, -1, -1, -1])))
    values = [int(value) for value in values[:4]]
    while len(values) < 4:
        values.append(-1)
    return values


def _node_name_for_index(scene, index, attr_name):
    index = int(index)
    flag_name = "is_ai_node" if attr_name == "ai_node_index" else "is_pos_node"
    for candidate in scene.objects:
        if not bool(getattr(candidate, flag_name, candidate.get(flag_name, False))):
            continue
        if int(getattr(candidate, attr_name, candidate.get(attr_name, -9999))) == index:
            return candidate.name
    return str(index + 1) if index >= 0 else "-"


def _connected_names(scene, indices, attr_name):
    names = [_node_name_for_index(scene, index, attr_name) for index in indices if int(index) >= 0]
    return ", ".join(names) if names else "-"


class RVIO_PT_RevoltObjectPanel(bpy.types.Panel):
    bl_label = "Re-Volt Properties"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "object"
    bl_options = {"HIDE_HEADER"}

    def draw(self, context):
        layout = self.layout
        obj = context.active_object
        scene = context.scene

        if obj and obj.is_track_zone:
            tz_box = layout.box()
            tz_box.label(text="Track Zone Properties")
            tz_col = tz_box.column(align=True)
            tz_col.prop(obj, "track_zone_id", text="Track Zone ID", slider=True)
            tz_col.operator("object.duplicate_track_zone", text="Duplicate Track Zone", icon="DUPLICATE")

        if obj and (getattr(obj, "is_ai_node", False) or obj.get("is_ai_node")):
            ai_box = layout.box()
            ai_box.label(text="AI Node Properties")
            ai_col = ai_box.column(align=True)
            ai_col.prop(obj, "ai_visual_property_enum", text="Type")
            ai_col.prop(obj, "ai_visual_start_node", text="Start Node")
            row = ai_col.row(align=True)
            row.prop(obj, "ai_left_wall", text="Left Node Wall")
            row.prop(obj, "ai_right_wall", text="Right Node Wall")
            ai_col.prop(obj, "ai_lane_width", text="Width")
            ai_col.prop(obj, "ai_racing_ratio", text="Racing Line")
            ai_col.prop(obj, "ai_overtake_ratio", text="Overtake Line")
            connections = _connection_values(obj, "ai_connections", "ai_connections")
            ai_col.label(text=f"From: {_connected_names(scene, connections[:2], 'ai_node_index')}")
            ai_col.label(text=f"To: {_connected_names(scene, connections[2:], 'ai_node_index')}")
            ai_col.prop(obj, "ai_is_secondary_path", text="Additional Route")
            if obj.ai_is_secondary_path:
                helper_name = obj.get("ai_route_helper_name")
                if helper_name:
                    ai_col.label(text=f"Route Name: {_truncate_ui_text(helper_name)}")
                ai_col.prop(obj, "ai_branch_start_index", text="Split From")
                ai_col.prop(obj, "ai_branch_join_index", text="Join To")

            ai_tools = ai_box.column(align=True)
            ai_tools.separator()
            ai_tools.operator("scene.connect_ai_path_to_target", icon="CON_TRACKTO", text="Connect Selected")
            ai_tools.operator("scene.connect_ai_nodes_by_name", icon="LINKED", text="Connect by Name")
            ai_tools.operator("scene.disconnect_ai_path_selected", icon="UNLINKED", text="Disconnect Selected")
            ai_col.operator("object.reverse_ai_nodes", icon='ARROW_LEFTRIGHT', text="Reverse Nodes")
            ai_col.operator("object.toggle_ai_node_visibility", icon="HIDE_OFF")

        if obj and (getattr(obj, "is_pos_node", False) or obj.get("is_pos_node")):
            pos_box = layout.box()
            pos_box.label(text="Pos Node Properties")
            pos_col = pos_box.column(align=True)
            pos_col.operator("scene.connect_pos_path_to_target", icon="CON_TRACKTO", text="Connect Selected")
            if bool(getattr(obj, "pos_is_split_route", obj.get("pos_is_split_route", False))):
                pos_col.label(text=f"Split From: {_node_name_for_index(scene, obj.pos_route_start_index, 'pos_node_index')}")

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

        if obj and (getattr(obj, "is_force_field", False) or obj.get("is_force_field")):
            ff_box = layout.box()
            ff_box.label(text="Force Field Properties")
            ff_col = ff_box.column(align=True)
            ff_col.prop(obj, "force_field_type", text="Type")
            ff_col.prop(obj, "force_field_shape", text="Shape")
            ff_col.prop(obj, "force_field_apply", text="Apply")
            ff_col.prop(obj, "force_field_direction_mode", text="Direction")
            ff_col.prop(obj, "force_field_distribution", text="Distribution")
            if obj.force_field_shape == "SPHERE":
                ff_col.prop(obj, "force_field_radius_start", text="Radius Start")
                ff_col.prop(obj, "force_field_radius_end", text="Radius End")
            if obj.force_field_distribution == "GRADIENT":
                ff_col.prop(obj, "force_field_mag_start", text="Mag Start")
                ff_col.prop(obj, "force_field_mag_end", text="Mag End")
                ff_col.prop(obj, "force_field_damping", text="Damping")
            else:
                ff_col.prop(obj, "force_field_magnitude", text="Magnitude")
                ff_col.prop(obj, "force_field_damping", text="Damping")
            size = (
                to_revolt_scale(obj.scale.x),
                to_revolt_scale(obj.scale.y),
                to_revolt_scale(obj.scale.z),
            )
            ff_col.label(text=f"Size (from scale): {size[0]:.1f} {size[1]:.1f} {size[2]:.1f}")
            ff_col.operator("object.duplicate_force_field", text="Duplicate Force Field", icon="DUPLICATE")

        # FOB Object properties
        if obj and obj.get("is_fob_object"):
            raw_type = obj.get("fob_type", getattr(obj, "fob_type", 0))
            try:
                obj_type_id = int(raw_type)
            except (TypeError, ValueError):
                obj_type_id = 0
            obj_type_name = OBJECT_TYPE_NAMES.get(obj_type_id, f"Unknown({obj_type_id})")

            labels = OBJECT_SUBTYPE_DESCRIPTIONS.get(obj_type_id, [])
            subtype_values = OBJECT_SUBTYPE_VALUES.get(obj_type_id, {})

            fob_box = layout.box()
            fob_box.label(text="FOB Object Properties")
            col = fob_box.column(align=True)

            type_row = col.row(align=True)
            if hasattr(obj, "fob_type_enum"):
                type_row.prop(obj, "fob_type_enum", text="Object Type")
            else:
                type_row.label(text="Object Type")
            col.label(text=f"Object ID: {obj_type_id}")
            col.label(text=f"Type Name: {obj_type_name}")

            for idx in range(4):
                label_text = labels[idx] if idx < len(labels) and labels[idx] else None
                allowed = subtype_values.get(idx)
                prop_name = f"fob_subtype_{idx + 1}"
                enum_attr = f"fob_subtype_enum_{idx + 1}"

                if not label_text and not allowed:
                    continue

                display_label = label_text or f"Subtype {idx + 1}"
                row = col.row(align=True)

                # Named values -> use dropdown
                if _is_str_sequence(allowed):
                    try:
                        row.prop(obj, enum_attr, text=display_label)
                    except (AttributeError, RuntimeError, TypeError, ValueError):
                        row.prop(obj, prop_name, text=display_label)
                    continue

                # Numeric values
                if _is_int_sequence(allowed):
                    min_val = min(allowed)
                    max_val = max(allowed)
                    is_contiguous = _is_contiguous_int_range(allowed)

                    # Small discrete non-range set -> dropdown
                    if len(allowed) <= 16 and not is_contiguous:
                        try:
                            row.prop(obj, enum_attr, text=display_label)
                        except (AttributeError, RuntimeError, TypeError, ValueError):
                            row.prop(obj, prop_name, text=display_label)
                        continue

                    # Continuous range or larger numeric set -> numeric field, with slider when sensible
                    range_prop = fob_subtype_range_property_name(idx + 1, min_val, max_val)
                    if is_contiguous and hasattr(obj, range_prop):
                        row.prop(obj, range_prop, text=display_label, slider=(max_val > min_val))
                    else:
                        row.prop(obj, prop_name, text=display_label, slider=(max_val > min_val))
                    row.label(text=f"{min_val}-{max_val}")
                    continue

                # Fallback
                row.prop(obj, prop_name, text=display_label)

            col.operator("object.duplicate_fob", icon="DUPLICATE")

        if obj and obj.get("is_trigger"):
            tri_box = layout.box()
            tri_box.label(text="Trigger Properties")
            tri_col = tri_box.column(align=True)

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
        if obj and (getattr(obj, "is_visibox", False) or obj.get("is_visibox")):
            visibox_box = layout.box()
            visibox_box.label(text="Visibox Properties")
            visibox_col = visibox_box.column(align=True)
            visibox_col.prop(obj, "visibox_type", text="Type")
            visibox_col.prop(obj, "visibox_id", text="ID", slider=True)

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

        # Debug properties
        box = layout.box()
        box.label(text="Debug Properties:")
        col = box.column(align=True)
        col.prop(obj, "is_bcube", text="Object is a BigCube")
        col.prop(obj, "is_cube", text="Object is a Cube")
        col.prop(obj, "is_bbox", text="Object is a Boundary Box")
        col.prop(obj, "ignore_ncp", text="Ignore for .ncp")
        col.operator("object.set_bcube_mesh_indices")
