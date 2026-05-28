"""
Name:    pan_in
Purpose: Imports Re-Volt position node files (.pan)
"""

import os

import bpy
from mathutils import Vector as BlenderVector

from . import rvstruct
from .common import to_blender_coord


COLLECTION_NAME = "POS_NODES"
ROUTE_VISUAL_NAME = "POS_NODE_CONNECTIONS"
NODE_MATERIAL = "Pos Node Yellow"
ROUTE_MATERIAL = "Pos Connected Path Yellow"


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


def _make_node_mesh(name, radius=0.35):
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


def _remove_object_and_data(obj):
    data = obj.data if obj.type in {"MESH", "CURVE"} else None
    is_curve = obj.type == "CURVE"
    bpy.data.objects.remove(obj, do_unlink=True)
    if data and data.users == 0:
        if is_curve:
            bpy.data.curves.remove(data)
        else:
            bpy.data.meshes.remove(data)


def _is_pos_route_visual_candidate(obj, collection):
    if obj.get("is_pos_route_visual"):
        return True
    if obj.name.startswith(ROUTE_VISUAL_NAME):
        return True
    if obj.type not in {"MESH", "CURVE"} or not obj.data:
        return False
    if getattr(obj, "is_pos_node", False) or obj.get("is_pos_node"):
        return False
    if not any(linked_obj == obj for linked_obj in collection.objects):
        return False
    return obj.type == "MESH" and len(obj.data.polygons) == 0 and len(obj.data.edges) > 0


def clear_pos_import_objects():
    collection = ensure_collection()
    for obj in list(bpy.data.objects):
        if (
            getattr(obj, "is_pos_node", False)
            or obj.get("is_pos_node")
            or _is_pos_route_visual_candidate(obj, collection)
        ):
            _remove_object_and_data(obj)


def _set_pos_props(obj, node, index):
    obj.is_pos_node = True
    obj["is_pos_node"] = True
    obj.pos_node_index = int(index)
    obj["pos_node_index"] = int(index)
    obj.pos_node_distance = float(node.distance)
    obj.pos_prev_nodes = [int(c) for c in node.prev[:4]]
    obj.pos_next_nodes = [int(c) for c in node.next[:4]]
    obj["pos_prev_nodes"] = [int(c) for c in node.prev[:4]]
    obj["pos_next_nodes"] = [int(c) for c in node.next[:4]]
    if hasattr(obj, "pos_is_split_route"):
        obj.pos_is_split_route = False
    obj["pos_is_split_route"] = False
    if hasattr(obj, "pos_route_start_index"):
        obj.pos_route_start_index = -1
    obj["pos_route_start_index"] = -1


def create_pos_node_object(node=None, index=0, collection=None, location=None, name=None):
    if collection is None:
        collection = ensure_collection()

    if node is not None:
        location = BlenderVector(to_blender_coord(node.position.data))
    elif location is None:
        location = BlenderVector((0.0, 0.0, 0.0))

    if name is None:
        name = f"POS_{int(index) + 1:03d}"
    name = _unique_name(name)
    mesh = _make_node_mesh(f"{name}_Mesh")
    obj = bpy.data.objects.new(name, mesh)
    obj.location = location
    obj.display_type = "SOLID"
    obj.show_in_front = True
    obj.color = (1.0, 0.82, 0.12, 1.0)
    obj.data.materials.append(_ensure_material(NODE_MATERIAL, (1.0, 0.82, 0.12, 1.0)))
    collection.objects.link(obj)

    if node is None:
        node = rvstruct.PosNode()
    _set_pos_props(obj, node, index)
    return obj


def _pos_objects(scene):
    collection = bpy.data.collections.get(COLLECTION_NAME)
    source = collection.objects if collection else scene.objects
    return sorted(
        [obj for obj in source if getattr(obj, "is_pos_node", False) or obj.get("is_pos_node")],
        key=lambda obj: int(getattr(obj, "pos_node_index", obj.get("pos_node_index", 0))),
    )


def _pos_index(obj):
    return int(getattr(obj, "pos_node_index", obj.get("pos_node_index", 0)))


def _pos_location(obj):
    return obj.matrix_world.translation.copy()


def _connections(obj, attr_name, key_name):
    values = list(getattr(obj, attr_name, obj.get(key_name, [-1, -1, -1, -1])))
    values = [int(v) for v in values[:4]]
    while len(values) < 4:
        values.append(-1)
    return values


def _make_route_mesh(name, verts, edges, material):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([tuple(v) for v in verts], edges, [])
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    obj.location = (0.0, 0.0, 0.0)
    obj["is_pos_route_visual"] = True
    obj.display_type = "SOLID"
    obj.show_in_front = True
    obj.hide_select = True
    obj.color = material.diffuse_color
    obj.data.materials.append(material)
    return obj


def rebuild_pos_route_visuals(scene):
    collection = ensure_collection()
    for obj in list(bpy.data.objects):
        if _is_pos_route_visual_candidate(obj, collection):
            _remove_object_and_data(obj)

    objects = _pos_objects(scene)
    if len(objects) < 2:
        return None

    by_index = {_pos_index(obj): obj for obj in objects}
    verts = []
    edges = []
    seen = set()
    for obj in objects:
        source_index = _pos_index(obj)
        for target_index in _connections(obj, "pos_next_nodes", "pos_next_nodes"):
            if target_index not in by_index:
                continue
            edge_key = tuple(sorted((source_index, target_index)))
            if edge_key in seen:
                continue
            seen.add(edge_key)
            verts.extend([_pos_location(obj), _pos_location(by_index[target_index])])
            edges.append((len(verts) - 2, len(verts) - 1))

    if not edges:
        return None

    visual = _make_route_mesh(
        ROUTE_VISUAL_NAME,
        verts,
        edges,
        _ensure_material(ROUTE_MATERIAL, (1.0, 0.82, 0.12, 1.0)),
    )
    collection.objects.link(visual)
    return visual


def import_file(filepath, scene):
    print(f"Importing position nodes: {filepath}")
    with open(filepath, "rb") as file:
        nodes = rvstruct.PosNodes(file)

    scene.pos_nodes_start_node = int(nodes.start_node)
    scene.pos_nodes_total_dist = float(nodes.total_dist)
    scene["pos_nodes_source_file"] = os.path.basename(filepath)
    scene["pos_nodes_trailing_data_hex"] = nodes.trailing_data.hex(" ").upper()

    clear_pos_import_objects()
    collection = ensure_collection()

    objects = []
    for index, node in enumerate(nodes.nodes):
        objects.append(create_pos_node_object(node=node, index=index, collection=collection))

    try:
        bpy.context.view_layer.update()
    except Exception:
        pass
    rebuild_pos_route_visuals(scene)
    try:
        bpy.context.view_layer.update()
    except Exception:
        pass
    trailing = f" ({len(nodes.trailing_data)} trailing byte(s) ignored)" if nodes.trailing_data else ""
    print(f"Imported {len(objects)} position nodes{trailing}")
    return True
