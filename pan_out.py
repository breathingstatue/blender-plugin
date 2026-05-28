"""
Name:    pan_out
Purpose: Exports Re-Volt position node files (.pan)
"""

import bpy

from . import rvstruct
from .common import to_revolt_coord, to_revolt_scale


def _get_pos_objects(scene):
    collection = bpy.data.collections.get("POS_NODES")
    source = collection.objects if collection else scene.objects
    return sorted(
        [obj for obj in source if getattr(obj, "is_pos_node", False) or obj.get("is_pos_node")],
        key=lambda obj: int(getattr(obj, "pos_node_index", obj.get("pos_node_index", 0))),
    )


def _connections(obj, attr_name, key_name):
    values = list(getattr(obj, attr_name, obj.get(key_name, [-1, -1, -1, -1])))
    values = [int(v) for v in values[:4]]
    while len(values) < 4:
        values.append(-1)
    return values


def _pos_index(obj):
    return int(getattr(obj, "pos_node_index", obj.get("pos_node_index", 0)))


def _node_from_object(obj):
    node = rvstruct.PosNode()
    node.position = rvstruct.Vector(data=to_revolt_coord(obj.matrix_world.translation))
    node.distance = float(getattr(obj, "pos_node_distance", obj.get("pos_node_distance", 0.0)))
    node.prev = _connections(obj, "pos_prev_nodes", "pos_prev_nodes")
    node.next = _connections(obj, "pos_next_nodes", "pos_next_nodes")
    return node


def _recalculate_distances(objects, nodes, start_node):
    if not objects:
        return 0.0

    by_index = {_pos_index(obj): obj for obj in objects}
    node_by_index = {_pos_index(obj): node for obj, node in zip(objects, nodes)}
    if start_node not in by_index:
        start_node = _pos_index(objects[-1])

    # Distance is stored as the remaining track length to the start/finish node.
    current_index = start_node
    visited = {current_index}
    reverse_order = [current_index]
    while True:
        current_obj = by_index.get(current_index)
        if current_obj is None:
            break
        prev_candidates = [
            idx for idx in _connections(current_obj, "pos_prev_nodes", "pos_prev_nodes")
            if idx in by_index and idx not in visited
        ]
        if not prev_candidates:
            break
        prev_index = prev_candidates[0]
        reverse_order.append(prev_index)
        visited.add(prev_index)
        current_index = prev_index

    if len(reverse_order) < len(objects):
        for obj in reversed(objects):
            index = _pos_index(obj)
            if index not in visited:
                reverse_order.append(index)
                visited.add(index)

    running = 0.0
    previous_obj = None
    for index in reverse_order:
        obj = by_index.get(index)
        node = node_by_index.get(index)
        if obj is None or node is None:
            continue
        if previous_obj is not None:
            running += to_revolt_scale((previous_obj.matrix_world.translation - obj.matrix_world.translation).length)
        node.distance = float(running)
        previous_obj = obj

    start_obj = by_index.get(start_node)
    if previous_obj is not None and start_obj is not None:
        previous_index = _pos_index(previous_obj)
        if previous_index in _connections(start_obj, "pos_next_nodes", "pos_next_nodes"):
            running += to_revolt_scale((previous_obj.matrix_world.translation - start_obj.matrix_world.translation).length)

    return running


def export_file(filepath, scene):
    pos = rvstruct.PosNodes()

    objects = _get_pos_objects(scene)
    if not objects:
        print("No position node objects found.")
        return False

    pos.nodes = [_node_from_object(obj) for obj in objects]
    pos.num_nodes = len(pos.nodes)
    pos.start_node = int(getattr(scene, "pos_nodes_start_node", scene.get("pos_nodes_start_node", _pos_index(objects[-1]))))
    if pos.start_node not in {_pos_index(obj) for obj in objects}:
        pos.start_node = _pos_index(objects[-1])
    pos.total_dist = _recalculate_distances(objects, pos.nodes, pos.start_node)
    if pos.total_dist <= 0:
        pos.total_dist = float(getattr(scene, "pos_nodes_total_dist", scene.get("pos_nodes_total_dist", 0.0)))

    with open(filepath, "wb") as file:
        pos.write(file)

    print(f"Exported {len(pos.nodes)} position nodes to {filepath}")
    return True
