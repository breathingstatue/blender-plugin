"""
Name:    fan_out
Purpose: Exports Re-Volt AI node files (.fan)
"""

import bpy
from mathutils import Vector as BlenderVector

from . import rvstruct
from .common import to_revolt_coord


def _get_ai_objects(scene):
    collection = bpy.data.collections.get("AI_NODES")
    source = collection.objects if collection else scene.objects
    return sorted(
        [obj for obj in source if getattr(obj, "is_ai_node", False) or obj.get("is_ai_node")],
        key=lambda obj: int(getattr(obj, "ai_node_index", obj.get("ai_node_index", 0))),
    )


def _vertex_world(obj, index, fallback=(0.0, 0.0, 0.0)):
    if obj.type == "MESH" and obj.data and len(obj.data.vertices) > index:
        return obj.matrix_world @ obj.data.vertices[index].co
    return BlenderVector(fallback)


def _ratio_between(left, right, point, fallback):
    span = right - left
    denom = span.dot(span)
    if denom <= 0.000001:
        return float(fallback)
    return float(max(0.0, min(1.0, (point - left).dot(span) / denom)))


def _connections(obj):
    values = list(getattr(obj, "ai_connections", obj.get("ai_connections", [-1, -1, -1, -1])))
    values = [int(v) for v in values[:4]]
    while len(values) < 4:
        values.append(-1)
    return values


def _node_index(obj, fallback=0):
    return int(getattr(obj, "ai_node_index", obj.get("ai_node_index", fallback)))


def _remap_connection_indices(connections, index_map):
    remapped = []
    for value in connections[:4]:
        value = int(value)
        remapped.append(index_map.get(value, -1) if value >= 0 else -1)
    while len(remapped) < 4:
        remapped.append(-1)
    return remapped


def _remap_header_index(value, index_map):
    value = int(value)
    return index_map.get(value, value) if value >= 0 else value


def _node_from_object(obj):
    node = rvstruct.AiNode()

    left = _vertex_world(obj, 0)
    right = _vertex_world(obj, 1)

    node.left_pos = rvstruct.Vector(data=to_revolt_coord(left))
    node.right_pos = rvstruct.Vector(data=to_revolt_coord(right))
    node.racing_ratio = float(getattr(obj, "ai_racing_ratio", obj.get("ai_racing_ratio", 0.5)))
    node.overtake_ratio = float(getattr(obj, "ai_overtake_ratio", obj.get("ai_overtake_ratio", obj.get("ai_raw_next_racing_ratio", 0.5))))

    node.priority = int(getattr(obj, "ai_priority", obj.get("ai_priority", 0)))
    node.property_type = int(getattr(obj, "ai_property_type", obj.get("ai_property_type", obj.get("ai_flags", 0) & 0xFF)))
    node.start_node = bool(getattr(obj, "ai_start_node", obj.get("ai_start_node", False)))
    raw_flags = int(getattr(obj, "ai_flags", obj.get("ai_flags", 0)))
    left_wall_flags = int(getattr(
        obj,
        "ai_left_wall_flags",
        obj.get("ai_left_wall_flags", 0x03 if getattr(obj, "ai_left_wall", obj.get("ai_left_wall", False)) else 0),
    ))
    right_wall_flags = int(getattr(
        obj,
        "ai_right_wall_flags",
        obj.get("ai_right_wall_flags", 0x03 if getattr(obj, "ai_right_wall", obj.get("ai_right_wall", False)) else 0),
    ))
    if hasattr(obj, "ai_left_wall"):
        left_wall_flags = 0x03 if obj.ai_left_wall else 0
    if hasattr(obj, "ai_right_wall"):
        right_wall_flags = 0x03 if obj.ai_right_wall else 0
    node.left_wall_flags = left_wall_flags
    node.right_wall_flags = right_wall_flags
    node.flags = (
        (raw_flags & ~0xFFFF01FF)
        | (node.property_type & 0xFF)
        | (0x100 if node.start_node else 0)
        | ((left_wall_flags & 0xFF) << 16)
        | ((right_wall_flags & 0xFF) << 24)
    )
    node.green_speed = int(getattr(obj, "ai_green_speed", obj.get("ai_green_speed", 30)))
    node.red_speed = int(getattr(obj, "ai_red_speed", obj.get("ai_red_speed", 30)))
    node.racing_speed = int(getattr(obj, "ai_racing_speed", obj.get("ai_racing_speed", 30)))
    node.center_speed = int(getattr(obj, "ai_center_speed", obj.get("ai_center_speed", 30)))
    node.track_dist = float(getattr(obj, "ai_track_dist", obj.get("ai_track_dist", 0.0)))
    node.connections = _connections(obj)
    return node


def _sync_next_racing_ratio_fields(objects, nodes):
    by_index = {
        _node_index(obj, index): (obj, nodes[index])
        for index, obj in enumerate(objects)
    }
    for obj, node in zip(objects, nodes):
        connections = _connections(obj)
        target_index = connections[2] if connections[2] in by_index else connections[3]
        if target_index in by_index:
            target_obj, _target_node = by_index[target_index]
            node.overtake_ratio = float(getattr(target_obj, "ai_racing_ratio", target_obj.get("ai_racing_ratio", 0.5)))


def export_file(filepath, scene):
    ai = rvstruct.AiNodes()
    ai.has_extended_header = bool(scene.get("ai_nodes_has_extended_header", True))
    ai.node_record_layout = str(scene.get("ai_nodes_record_layout", "track_last"))
    ai.total_dist_location = str(scene.get("ai_nodes_total_dist_location", "header"))
    ai.header_total_dist = float(scene.get("ai_nodes_header_total_dist", 0.0))
    trailing_hex = str(scene.get("ai_nodes_trailing_data_hex", "")).strip()
    if trailing_hex:
        try:
            ai.trailing_data = bytes.fromhex(trailing_hex)
        except ValueError:
            ai.trailing_data = b""

    objects = _get_ai_objects(scene)
    if not objects:
        print("No AI node objects found.")
        return False

    index_map = {_node_index(obj, index): index for index, obj in enumerate(objects)}
    ai.nodes = [_node_from_object(obj) for obj in objects]
    for node in ai.nodes:
        node.connections = _remap_connection_indices(node.connections, index_map)
    ai.num_nodes = len(ai.nodes)
    ai.start_node = _remap_header_index(
        getattr(scene, "ai_nodes_start_node", scene.get("ai_nodes_start_node", 0)),
        index_map,
    )
    ai.end_node = _remap_header_index(
        getattr(scene, "ai_nodes_end_node", scene.get("ai_nodes_end_node", 0)),
        index_map,
    )
    ai.header_flags = int(getattr(scene, "ai_nodes_header_flags", scene.get("ai_nodes_header_flags", 0)))
    ai.start_factor = float(getattr(scene, "ai_nodes_start_factor", scene.get("ai_nodes_start_factor", 0.5)))
    ai.total_dist = float(getattr(scene, "ai_nodes_total_dist", scene.get("ai_nodes_total_dist", 0.0)))

    if ai.total_dist <= 0:
        ai.total_dist = max((node.track_dist for node in ai.nodes), default=0.0)

    with open(filepath, "wb") as file:
        ai.write(file)

    print(f"Exported {len(ai.nodes)} AI node segments to {filepath}")
    return True
