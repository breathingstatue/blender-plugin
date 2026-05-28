"""
Name:    fan_in
Purpose: Imports Re-Volt AI node files (.fan)
"""

import os

import bpy
from mathutils import Vector as BlenderVector

from . import rvstruct
from .common import to_blender_coord


COLLECTION_NAME = "AI_NODES"
ROUTE_VISUAL_NAME = "AI_NODE_CONNECTIONS"
PREFERRED_VISUAL_NAME = "AI_NODE_OVERTAKE_CONNECTIONS"
LEFT_WALL_VISUAL_NAME = "AI_NODE_GREEN_WALLS"
RIGHT_WALL_VISUAL_NAME = "AI_NODE_PURPLE_WALLS"
LEFT_HANDLE_MATERIAL = "AI Node Left Green"
RIGHT_HANDLE_MATERIAL = "AI Node Right Purple"
ROUTE_MATERIAL = "AI Connected Path Purple"
PREFERRED_MATERIAL = "AI Overtake Line White"
LEFT_WALL_MATERIAL = "AI Green Node Walls"
RIGHT_WALL_MATERIAL = "AI Purple Node Walls"


def ensure_collection(name=COLLECTION_NAME):
    if name not in bpy.data.collections:
        collection = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(collection)
    return bpy.data.collections[name]


def _unique_name(base):
    if base not in bpy.data.objects and base not in bpy.data.meshes:
        return base

    index = 1
    while f"{base}.{index:03d}" in bpy.data.objects or f"{base}.{index:03d}" in bpy.data.meshes:
        index += 1
    return f"{base}.{index:03d}"


def _ensure_material(name, color):
    material = bpy.data.materials.get(name)
    if material is None:
        material = bpy.data.materials.new(name)
    material.diffuse_color = color
    material.use_nodes = True
    principled = material.node_tree.nodes.get("Principled BSDF")
    if principled:
        if "Base Color" in principled.inputs:
            principled.inputs["Base Color"].default_value = color
        if "Alpha" in principled.inputs:
            principled.inputs["Alpha"].default_value = color[3]
        if "Roughness" in principled.inputs:
            principled.inputs["Roughness"].default_value = 0.55
    return material


def _make_handle_mesh(name, radius):
    verts = [
        (0.0, 0.0, radius),
        (0.0, 0.0, -radius),
        (-radius, 0.0, 0.0),
        (radius, 0.0, 0.0),
        (0.0, -radius, 0.0),
        (0.0, radius, 0.0),
    ]
    faces = [
        (0, 3, 5), (0, 5, 2), (0, 2, 4), (0, 4, 3),
        (1, 5, 3), (1, 2, 5), (1, 4, 2), (1, 3, 4),
    ]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    return mesh


def _segment_point(left, right, ratio):
    return left.lerp(right, float(ratio))


def _display_ratio(ratio):
    ratio = float(ratio)
    if ratio < 0.0 or ratio > 1.0:
        return 0.5
    return ratio


def _import_ratio(ratio):
    try:
        ratio = float(ratio)
    except (TypeError, ValueError):
        return 0.5, None
    if ratio < 0.0 or ratio > 1.0:
        return 0.5, ratio
    return ratio, None


def _has_preferred_ratio(obj):
    ratio = _display_ratio(getattr(obj, "ai_overtake_ratio", obj.get("ai_overtake_ratio", 0.5)))
    return abs(ratio - 0.5) > 0.0001


def _remove_object_and_mesh(obj):
    data = obj.data if obj.type in {"MESH", "CURVE"} else None
    is_curve = obj.type == "CURVE"
    bpy.data.objects.remove(obj, do_unlink=True)
    if data and data.users == 0:
        if is_curve:
            bpy.data.curves.remove(data)
        else:
            bpy.data.meshes.remove(data)


def _remove_ai_node_handles(obj):
    for child in list(obj.children):
        if child.get("is_ai_node_handle"):
            _remove_object_and_mesh(child)


def _is_ai_route_visual_candidate(obj, collection):
    if obj.get("is_ai_route_visual"):
        return True
    if (
        obj.name.startswith(ROUTE_VISUAL_NAME)
        or obj.name.startswith(PREFERRED_VISUAL_NAME)
        or obj.name.startswith(LEFT_WALL_VISUAL_NAME)
        or obj.name.startswith(RIGHT_WALL_VISUAL_NAME)
    ):
        return True
    if obj.type not in {"MESH", "CURVE"} or not obj.data:
        return False
    if getattr(obj, "is_ai_node", False) or obj.get("is_ai_node"):
        return False
    if not any(linked_obj == obj for linked_obj in collection.objects):
        return False
    return obj.type == "MESH" and len(obj.data.polygons) == 0 and len(obj.data.edges) > 0


def clear_ai_import_objects():
    collection = ensure_collection()
    for obj in list(bpy.data.objects):
        if (
            getattr(obj, "is_ai_node", False)
            or obj.get("is_ai_node")
            or obj.get("is_ai_node_handle")
            or _is_ai_route_visual_candidate(obj, collection)
        ):
            _remove_object_and_mesh(obj)


def update_ai_node_handles(obj, collection=None):
    if obj.type != "MESH" or not obj.data or len(obj.data.vertices) < 2:
        return
    if collection is None:
        collection = ensure_collection()

    _remove_ai_node_handles(obj)

    left = obj.data.vertices[0].co.copy()
    right = obj.data.vertices[1].co.copy()
    width = max(0.01, float((right - left).length))
    radius = max(0.18, min(0.55, width * 0.08))

    handle_specs = (
        ("L", left, _ensure_material(LEFT_HANDLE_MATERIAL, (0.0, 0.9, 0.18, 1.0))),
        ("R", right, _ensure_material(RIGHT_HANDLE_MATERIAL, (0.55, 0.12, 0.95, 1.0))),
    )
    for suffix, location, material in handle_specs:
        handle_name = _unique_name(f"{obj.name}_{suffix}_Handle")
        handle_mesh = _make_handle_mesh(f"{handle_name}_Mesh", radius)
        handle = bpy.data.objects.new(handle_name, handle_mesh)
        handle.parent = obj
        handle.location = location
        handle.display_type = "SOLID"
        handle.show_in_front = True
        handle.hide_select = True
        handle["is_ai_node_handle"] = True
        handle["ai_handle_parent"] = obj.name
        handle.data.materials.append(material)
        collection.objects.link(handle)


def _set_ai_props(obj, node, index):
    obj.is_ai_node = True
    obj["is_ai_node"] = True
    obj.ai_node_index = int(index)
    obj["ai_node_index"] = int(index)
    obj["ai_file_index"] = int(index)
    obj["ai_display_index"] = int(index)

    obj.ai_priority = int(node.priority)
    obj.ai_property_type = int(node.property_type)
    obj.ai_start_node = bool(node.start_node)
    obj.ai_flags = int(node.flags)
    obj.ai_left_wall = bool(node.left_wall_flags)
    obj.ai_right_wall = bool(node.right_wall_flags)
    obj.ai_left_wall_flags = int(node.left_wall_flags)
    obj.ai_right_wall_flags = int(node.right_wall_flags)
    obj["ai_left_wall"] = bool(node.left_wall_flags)
    obj["ai_right_wall"] = bool(node.right_wall_flags)
    obj["ai_left_wall_flags"] = int(node.left_wall_flags)
    obj["ai_right_wall_flags"] = int(node.right_wall_flags)
    obj.ai_green_speed = int(node.green_speed)
    obj.ai_red_speed = int(node.red_speed)
    obj.ai_racing_speed = int(node.racing_speed)
    obj.ai_center_speed = int(node.center_speed)
    racing_ratio, raw_racing_ratio = _import_ratio(node.racing_ratio)
    obj.ai_racing_ratio = racing_ratio
    overtake_ratio, raw_overtake_ratio = _import_ratio(node.overtake_ratio)
    obj.ai_overtake_ratio = overtake_ratio
    if raw_overtake_ratio is not None:
        obj["ai_raw_overtake_ratio"] = raw_overtake_ratio
    if raw_racing_ratio is not None:
        obj["ai_raw_racing_ratio"] = raw_racing_ratio
    obj["ai_raw_next_racing_ratio"] = float(node.overtake_ratio)
    obj.ai_track_dist = float(node.track_dist)
    obj.ai_connections = [int(c) for c in node.connections[:4]]
    obj["ai_connections"] = [int(c) for c in node.connections[:4]]
    raw_record = getattr(node, "raw_record", b"")
    if raw_record:
        obj["ai_raw_record_hex"] = raw_record.hex(" ").upper()


def create_ai_node_object(node=None, index=0, collection=None, location=None, width=None, name=None):
    if collection is None:
        collection = ensure_collection()

    if node is None:
        node = rvstruct.AiNode()
        center = BlenderVector(location or (0.0, 0.0, 0.0))
        half_width = max(0.01, float(width or 2.0) * 0.5)
        left = center + BlenderVector((-half_width, 0.0, 0.0))
        right = center + BlenderVector((half_width, 0.0, 0.0))
    else:
        left = BlenderVector(to_blender_coord(node.left_pos.data))
        right = BlenderVector(to_blender_coord(node.right_pos.data))
        center = (left + right) * 0.5

    racing = _segment_point(left, right, _display_ratio(node.racing_ratio))
    overtake = _segment_point(left, right, _display_ratio(node.overtake_ratio))
    local_points = [left - center, right - center, racing - center, overtake - center]

    name = _unique_name(name or f"AI_{index + 1:03d}")
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(
        [tuple(point) for point in local_points],
        [(0, 1), (0, 2), (2, 1), (0, 3), (3, 1)],
        [],
    )
    mesh.update()

    obj = bpy.data.objects.new(name, mesh)
    obj.location = center
    obj.display_type = "WIRE"
    obj.show_in_front = True
    obj.show_name = True
    obj["_ai_suppress_geometry_update"] = True
    try:
        _set_ai_props(obj, node, index)
        obj["ai_lane_width"] = float((right - left).length)
        if hasattr(obj, "ai_lane_width"):
            obj.ai_lane_width = obj["ai_lane_width"]
    finally:
        obj["_ai_suppress_geometry_update"] = False

    collection.objects.link(obj)
    update_ai_node_handles(obj, collection)
    return obj


def _get_ai_objects(scene):
    return sorted(
        [obj for obj in scene.objects if getattr(obj, "is_ai_node", False) or obj.get("is_ai_node")],
        key=lambda obj: int(getattr(obj, "ai_node_index", obj.get("ai_node_index", 0))),
    )


def _node_index(obj):
    return int(getattr(obj, "ai_node_index", obj.get("ai_node_index", 0)))


def _node_connections(obj):
    values = list(getattr(obj, "ai_connections", obj.get("ai_connections", [-1, -1, -1, -1])))
    values = [int(value) for value in values[:4]]
    while len(values) < 4:
        values.append(-1)
    return values


def _valid_index(index, by_index):
    return index in by_index and index >= 0


def _normal_neighbors(obj, by_index):
    connections = _node_connections(obj)
    return [idx for idx in (connections[0], connections[2]) if _valid_index(idx, by_index)]


def _has_alt_connection(obj):
    connections = _node_connections(obj)
    return connections[1] >= 0 or connections[3] >= 0


def _has_alt_link(obj, target_index):
    connections = _node_connections(obj)
    return connections[1] == target_index or connections[3] == target_index


def _branch_display_number(obj):
    name = obj.name
    if name.upper().startswith("AI_"):
        parts = name[3:].split("_", 1)
        if parts and parts[0].isdigit():
            return int(parts[0])
    return _node_index(obj) + 1


def _rename_ai_object(obj, name):
    obj.name = name
    if obj.data:
        obj.data.name = f"{name}_Mesh"


def _valid_connection_target(index, by_index):
    return index in by_index and index >= 0


def _route_start_index(objects, header_start_index=0):
    by_index = {_node_index(obj): obj for obj in objects}
    for obj in objects:
        if bool(getattr(obj, "ai_start_node", obj.get("ai_start_node", False))):
            return _node_index(obj)

    if _valid_connection_target(int(header_start_index), by_index):
        return int(header_start_index)

    for obj in objects:
        connections = _node_connections(obj)
        if not _valid_connection_target(connections[0], by_index) and not _valid_connection_target(connections[1], by_index):
            return _node_index(obj)

    return min(by_index, default=0)


def _next_route_index(current_index, previous_index, by_index):
    current = by_index.get(current_index)
    if current is None:
        return -1

    connections = _node_connections(current)
    for target in (connections[2], connections[3], connections[0], connections[1]):
        if target == previous_index:
            continue
        if _valid_connection_target(target, by_index):
            return target
    return -1


def _connection_route_order(objects, header_start_index=0):
    by_index = {_node_index(obj): obj for obj in objects}
    if not by_index:
        return []

    start_index = _route_start_index(objects, header_start_index)
    ordered = []
    visited = set()
    previous = -1
    current = start_index

    while _valid_connection_target(current, by_index) and current not in visited:
        ordered.append(current)
        visited.add(current)
        next_index = _next_route_index(current, previous, by_index)
        previous, current = current, next_index

    for index in sorted(by_index):
        if index not in visited:
            ordered.append(index)
    return ordered


def assign_import_display_names(objects, header_start_index=0):
    """
    Name AI nodes by the likely in-game MAKEITGOOD path order.

    Important:
    - ai_node_index remains the raw .fan index.
    - connections remain raw indices.
    - only Blender display names / display metadata change.
    """

    by_index = {_node_index(obj): obj for obj in objects}
    if not by_index:
        return

    all_track_dist_zero = all(
        abs(float(getattr(obj, "ai_track_dist", obj.get("ai_track_dist", 0.0)))) <= 0.000001
        for obj in objects
    )

    if all_track_dist_zero:
        ordered_indices = sorted(by_index)
    else:
        ordered_indices = None

    if ordered_indices is None:
        def conn(obj):
            return _node_connections(obj)

        # Prefer the node with no slot-0 previous connection.
        # In files like smashride.fan this is the visible chain start/end used by MIG.
        start_candidates = [
            obj for obj in objects
            if conn(obj)[0] < 0 and conn(obj)[2] in by_index
        ]

        if start_candidates:
            start = min(start_candidates, key=_node_index)
            ordered_indices = []
            visited = set()
            current = _node_index(start)

            while current in by_index and current not in visited:
                ordered_indices.append(current)
                visited.add(current)

                next_index = conn(by_index[current])[2]
                if next_index not in by_index:
                    break
                current = next_index

            # If this only found a tiny chain, fall back to old route logic.
            if len(ordered_indices) < max(2, len(objects) // 2):
                ordered_indices = _connection_route_order(objects, header_start_index)
        else:
            ordered_indices = _connection_route_order(objects, header_start_index)

    # Add missed nodes safely.
    seen = set(ordered_indices)
    for index in sorted(by_index):
        if index not in seen:
            ordered_indices.append(index)
            seen.add(index)

    # Temporary names avoid Blender name collisions.
    for obj in objects:
        raw_index = _node_index(obj)
        obj.name = f"AI_RAW_{raw_index:03d}"
        if obj.data:
            obj.data.name = f"{obj.name}_Mesh"

    # Final visible order.
    for display_index, raw_index in enumerate(ordered_indices):
        obj = by_index.get(raw_index)
        if obj is None:
            continue

        obj["ai_display_index"] = display_index
        obj["ai_file_index"] = raw_index
        obj["ai_route_guess_index"] = display_index

        obj.name = f"AI_{display_index + 1:03d}"
        if obj.data:
            obj.data.name = f"{obj.name}_Mesh"

def assign_import_property_sources(objects):
    by_index = {_node_index(obj): obj for obj in objects}
    all_track_dist_zero = bool(by_index) and all(
        abs(float(getattr(obj, "ai_track_dist", obj.get("ai_track_dist", 0.0)))) <= 0.000001
        for obj in objects
    )
    if all_track_dist_zero:
        ordered = sorted(by_index)
        previous_by_index = {index: ordered[(pos - 1) % len(ordered)] for pos, index in enumerate(ordered)}
        for obj in objects:
            own_index = _node_index(obj)
            obj["ai_property_source_index"] = previous_by_index.get(own_index, own_index)
            obj["ai_property_source_reason"] = "zero-distance previous raw"
        return

    for obj in objects:
        own_index = _node_index(obj)
        obj["ai_property_source_index"] = own_index
        obj["ai_property_source_reason"] = "raw/self"


def _trace_branch(start_index, first_index, by_index):
    if not _valid_index(start_index, by_index) or not _valid_index(first_index, by_index):
        return [], -1

    branch = []
    previous = start_index
    current = first_index
    visited = {start_index}

    while _valid_index(current, by_index) and current not in visited:
        current_obj = by_index[current]
        if current != first_index and _has_alt_connection(current_obj):
            return branch, current

        branch.append(current)
        visited.add(current)

        candidates = [idx for idx in _normal_neighbors(current_obj, by_index) if idx != previous]
        if not candidates:
            return branch, -1

        preferred = [
            idx for idx in candidates
            if not _has_alt_link(by_index[idx], current) and not _has_alt_link(current_obj, idx)
        ]
        next_index = preferred[0] if preferred else candidates[0]
        if not _valid_index(next_index, by_index):
            return branch, -1
        if next_index in visited:
            return branch, next_index
        if next_index != first_index and _has_alt_connection(by_index[next_index]):
            return branch, next_index

        previous, current = current, next_index

    return branch, current if current in by_index else -1


def apply_import_branch_metadata(objects):
    by_index = {_node_index(obj): obj for obj in objects}
    if not by_index:
        return

    for obj in objects:
        if hasattr(obj, "ai_is_secondary_path"):
            obj.ai_is_secondary_path = False
        obj["ai_is_secondary_path"] = False
        if hasattr(obj, "ai_branch_start_index"):
            obj.ai_branch_start_index = -1
        obj["ai_branch_start_index"] = -1
        if hasattr(obj, "ai_branch_join_index"):
            obj.ai_branch_join_index = -1
        obj["ai_branch_join_index"] = -1

    branches = []
    for obj in objects:
        source_index = _node_index(obj)
        connections = _node_connections(obj)

        # Slot 3 is the clearest branch/additional-route hint in files exported
        # from the editor. In-game loop closures can also use slot 3 to point
        # back to the start node, which should not create a secondary path.
        target_index = connections[3]
        normal_target_index = connections[2]
        if _valid_index(target_index, by_index) and _valid_index(normal_target_index, by_index):
            if target_index == normal_target_index:
                continue
            source_is_start = bool(getattr(obj, "ai_start_node", obj.get("ai_start_node", False)))
            target_obj = by_index[target_index]
            target_is_start = bool(getattr(target_obj, "ai_start_node", target_obj.get("ai_start_node", False)))
            if target_is_start and not source_is_start:
                continue
            target_connections = _node_connections(target_obj)
            if _node_index(obj) not in {target_connections[0], target_connections[1]}:
                continue
            start_index, first_index = source_index, target_index
            branch_nodes, join_index = _trace_branch(start_index, first_index, by_index)
            if branch_nodes:
                branches.append((start_index, branch_nodes, join_index))

    marked = set()
    counters = {}
    for start_index, branch_nodes, join_index in branches:
        if not _valid_index(start_index, by_index):
            continue
        start_obj = by_index[start_index]
        display_number = _branch_display_number(start_obj)
        counters.setdefault(start_index, 0)

        for branch_index in branch_nodes:
            if branch_index in marked or not _valid_index(branch_index, by_index):
                continue
            branch_obj = by_index[branch_index]
            if branch_obj == start_obj:
                continue

            counters[start_index] += 1
            marked.add(branch_index)
            if hasattr(branch_obj, "ai_is_secondary_path"):
                branch_obj.ai_is_secondary_path = True
            branch_obj["ai_is_secondary_path"] = True
            if hasattr(branch_obj, "ai_branch_start_index"):
                branch_obj.ai_branch_start_index = start_index
            branch_obj["ai_branch_start_index"] = start_index
            if hasattr(branch_obj, "ai_branch_join_index"):
                branch_obj.ai_branch_join_index = join_index
            branch_obj["ai_branch_join_index"] = join_index
            branch_obj["ai_route_helper_name"] = f"AI_{display_number:03d}_{counters[start_index]:03d}"


def refresh_ai_node_helper_geometry(objects):
    collection = ensure_collection()
    for obj in objects:
        if obj.type != "MESH" or not obj.data or len(obj.data.vertices) < 2:
            continue

        left = obj.data.vertices[0].co
        right = obj.data.vertices[1].co

        if len(obj.data.vertices) >= 4:
            racing_ratio = _display_ratio(getattr(obj, "ai_racing_ratio", obj.get("ai_racing_ratio", 0.5)))
            preferred_ratio = _display_ratio(getattr(obj, "ai_overtake_ratio", obj.get("ai_overtake_ratio", 0.5)))
            obj.data.vertices[2].co = left.lerp(right, racing_ratio)
            obj.data.vertices[3].co = left.lerp(right, preferred_ratio)

        obj.data.update()
        obj["ai_lane_width"] = float((right - left).length)
        update_ai_node_handles(obj, collection)


def _make_route_curve(visual_name, verts, edges, material, bevel_depth=0.07):
    curve = bpy.data.curves.new(f"{visual_name}_Curve", "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 1
    curve.bevel_depth = bevel_depth
    curve.bevel_resolution = 3
    curve.fill_mode = "FULL"
    curve.materials.append(material)

    for edge in sorted(edges):
        start_index, end_index = edge
        if start_index >= len(verts) or end_index >= len(verts):
            continue
        spline = curve.splines.new("POLY")
        spline.points.add(1)
        start = verts[start_index]
        end = verts[end_index]
        spline.points[0].co = (start[0], start[1], start[2], 1.0)
        spline.points[1].co = (end[0], end[1], end[2], 1.0)

    return curve


def rebuild_ai_route_visuals(scene):
    collection = ensure_collection()

    for old in list(bpy.data.objects):
        if _is_ai_route_visual_candidate(old, collection):
            _remove_object_and_mesh(old)

    nodes = _get_ai_objects(scene)
    if not nodes:
        return None

    by_index = {
        int(getattr(obj, "ai_node_index", obj.get("ai_node_index", 0))): obj
        for obj in nodes
    }

    verts = []
    race_slot = {}
    overtake_slot = {}
    left_slot = {}
    right_slot = {}

    for obj in nodes:
        idx = int(getattr(obj, "ai_node_index", obj.get("ai_node_index", 0)))
        if obj.type != "MESH" or len(obj.data.vertices) < 4:
            continue
        left_slot[idx] = len(verts)
        verts.append(tuple(obj.matrix_world @ obj.data.vertices[0].co))
        right_slot[idx] = len(verts)
        verts.append(tuple(obj.matrix_world @ obj.data.vertices[1].co))
        race_slot[idx] = len(verts)
        verts.append(tuple(obj.matrix_world @ obj.data.vertices[2].co))
        overtake_slot[idx] = len(verts)
        verts.append(tuple(obj.matrix_world @ obj.data.vertices[3].co))

    racing_edges = set()
    preferred_edges = set()
    left_wall_edges = set()
    right_wall_edges = set()
    for obj in nodes:
        idx = int(getattr(obj, "ai_node_index", obj.get("ai_node_index", 0)))
        if idx not in race_slot:
            continue

        connections = list(getattr(obj, "ai_connections", obj.get("ai_connections", [-1, -1, -1, -1])))
        for slot, target in enumerate(connections[:4]):
            if target not in by_index or target not in race_slot:
                continue
            if slot == 2:
                racing_edges.add(tuple(sorted((race_slot[idx], race_slot[target]))))
                if _has_preferred_ratio(obj):
                    preferred_edges.add(tuple(sorted((overtake_slot[idx], overtake_slot[target]))))
            elif slot == 0:
                target_connections = list(getattr(by_index[target], "ai_connections", by_index[target].get("ai_connections", [-1, -1, -1, -1])))
                if len(target_connections) > 2 and target_connections[2] == idx:
                    racing_edges.add(tuple(sorted((race_slot[idx], race_slot[target]))))
            elif slot == 3:
                racing_edges.add(tuple(sorted((race_slot[idx], race_slot[target]))))

        wall_targets = [
            target for target in (connections[2], connections[3])
            if target in by_index and target in left_slot and target != idx
        ]
        if bool(getattr(obj, "ai_left_wall", obj.get("ai_left_wall", False))):
            for target in wall_targets:
                left_wall_edges.add(tuple(sorted((left_slot[idx], left_slot[target]))))
        if bool(getattr(obj, "ai_right_wall", obj.get("ai_right_wall", False))):
            for target in wall_targets:
                right_wall_edges.add(tuple(sorted((right_slot[idx], right_slot[target]))))

    created = None
    for visual_name, edges, color, material, bevel_depth in (
        (
            ROUTE_VISUAL_NAME,
            racing_edges,
            (0.55, 0.12, 0.95, 1.0),
            _ensure_material(ROUTE_MATERIAL, (0.55, 0.12, 0.95, 1.0)),
            0.07,
        ),
        (
            PREFERRED_VISUAL_NAME,
            preferred_edges,
            (1.0, 1.0, 1.0, 1.0),
            _ensure_material(PREFERRED_MATERIAL, (1.0, 1.0, 1.0, 1.0)),
            0.07,
        ),
        (
            LEFT_WALL_VISUAL_NAME,
            left_wall_edges,
            (0.0, 0.95, 0.25, 1.0),
            _ensure_material(LEFT_WALL_MATERIAL, (0.0, 0.95, 0.25, 1.0)),
            0.13,
        ),
        (
            RIGHT_WALL_VISUAL_NAME,
            right_wall_edges,
            (0.85, 0.25, 1.0, 1.0),
            _ensure_material(RIGHT_WALL_MATERIAL, (0.85, 0.25, 1.0, 1.0)),
            0.13,
        ),
    ):
        curve = _make_route_curve(visual_name, verts, edges, material, bevel_depth)
        obj = bpy.data.objects.new(visual_name, curve)
        obj.location = (0.0, 0.0, 0.0)
        obj["is_ai_route_visual"] = True
        obj.display_type = "SOLID"
        obj.show_in_front = True
        obj.hide_select = False
        obj.color = color
        collection.objects.link(obj)
        if created is None:
            created = obj
    return created


def import_file(filepath, scene):
    print(f"Importing AI nodes: {filepath}")
    with open(filepath, "rb") as file:
        nodes = rvstruct.AiNodes(file)

    scene.ai_nodes_start_node = int(nodes.start_node)
    scene.ai_nodes_end_node = int(nodes.end_node)
    scene.ai_nodes_start_enabled = bool(nodes.end_node & 0x0001)
    scene.ai_nodes_header_flags = int(nodes.header_flags)
    scene.ai_nodes_start_factor = float(nodes.start_factor)
    scene.ai_nodes_total_dist = float(nodes.total_dist)
    scene["ai_nodes_source_file"] = os.path.basename(filepath)
    scene["ai_nodes_has_extended_header"] = bool(getattr(nodes, "has_extended_header", True))
    scene["ai_nodes_record_layout"] = str(getattr(nodes, "node_record_layout", "track_last"))
    scene["ai_nodes_total_dist_location"] = getattr(nodes, "total_dist_location", "header")
    scene["ai_nodes_header_total_dist"] = float(getattr(nodes, "header_total_dist", nodes.total_dist))
    scene["ai_nodes_trailing_data_hex"] = getattr(nodes, "trailing_data", b"").hex(" ").upper()

    clear_ai_import_objects()
    collection = ensure_collection()

    objects = []
    for index, node in enumerate(nodes.nodes):
        objects.append(create_ai_node_object(node=node, index=index, collection=collection))

    assign_import_display_names(objects, nodes.start_node)
    assign_import_property_sources(objects)
    apply_import_branch_metadata(objects)
    refresh_ai_node_helper_geometry(objects)
    try:
        bpy.context.view_layer.update()
    except Exception:
        pass
    rebuild_ai_route_visuals(scene)
    try:
        bpy.context.view_layer.update()
    except Exception:
        pass
    print(f"Imported {len(nodes.nodes)} AI node segments")
    return True
