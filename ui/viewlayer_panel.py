import bpy

def _visibility_objects(context, collection_name=None, predicate=None):
    collection = bpy.data.collections.get(collection_name) if collection_name else None
    source = collection.objects if collection else context.scene.objects
    if predicate is None:
        return list(source)
    return [obj for obj in source if predicate(obj)]


def _visibility_icon(objects):
    return "HIDE_ON" if objects and all(obj.hide_get() for obj in objects) else "HIDE_OFF"


class RVIO_PT_RevoltViewLayerPanel(bpy.types.Panel):
    """Re-Volt Tools in View Layer Tab"""
    bl_label = "View Material"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "view_layer"
    bl_options = {"HIDE_HEADER"}

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        box = layout.box()
        box.label(text="Texture / Material")

        col = box.column(align=True)
        # 👇 No object/mesh used here – purely scene-level
        col.prop(scene, "material_choice")

        row = col.row(align=True)
        row.operator("object.assign_materials_auto", text="Set to All")

        col = box.column(align=True)
        col.operator("object.assign_texture", text="Car Skin")

        box = layout.box()
        box.label(text="Viewport Visibility")
        col = box.column(align=True)
        track_zones = _visibility_objects(context, "TRACK_ZONES", lambda obj: obj.get("is_track_zone"))
        ai_nodes = _visibility_objects(
            context,
            "AI_NODES",
            lambda obj: (
                getattr(obj, "is_ai_node", False)
                or obj.get("is_ai_node")
                or obj.get("is_ai_route_visual")
                or obj.get("is_ai_node_handle")
            ),
        )
        pos_nodes = _visibility_objects(
            context,
            "POS_NODES",
            lambda obj: (
                getattr(obj, "is_pos_node", False)
                or obj.get("is_pos_node")
                or obj.get("is_pos_route_visual")
            ),
        )
        instance_ncp = _visibility_objects(
            context,
            "INSTANCE_NCP",
            lambda obj: obj.get("is_ncp_collision") and obj.get("fin_instance_collision_source"),
        )
        fob_objects = _visibility_objects(context, predicate=lambda obj: obj.get("is_fob_object"))
        force_fields = _visibility_objects(context, predicate=lambda obj: obj.get("is_force_field"))
        lights = _visibility_objects(
            context,
            predicate=lambda obj: getattr(obj, "is_light", False) or obj.get("is_light", False),
        )
        triggers = _visibility_objects(context, "TRIGGERS")
        visiboxes = _visibility_objects(context, predicate=lambda obj: obj.get("is_visibox"))

        col.operator("scene.zone_hide", icon=_visibility_icon(track_zones), text="Track Zones")
        col.operator("object.toggle_ai_node_visibility", icon=_visibility_icon(ai_nodes), text="AI Nodes")
        col.operator("object.toggle_pos_node_visibility", icon=_visibility_icon(pos_nodes), text="Pos Nodes")
        col.operator("object.toggle_instance_ncp_visibility", icon=_visibility_icon(instance_ncp), text="Instance NCP")
        col.operator("object.toggle_fob_visibility", icon=_visibility_icon(fob_objects), text="FOB Objects")
        col.operator("object.toggle_force_field_visibility", icon=_visibility_icon(force_fields), text="Force Fields")
        col.operator("object.toggle_light_visibility", icon=_visibility_icon(lights), text="Lights")
        col.operator("scene.trigger_hide", icon=_visibility_icon(triggers), text="Triggers")
        col.operator("object.toggle_visibox_visibility", icon=_visibility_icon(visiboxes), text="Visiboxes")
