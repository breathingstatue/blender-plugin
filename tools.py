"""
Name:    tools
Purpose: Provides functions for operators

Description:
Some functions that are called by operators 
(e.g. the light panel, helpers, etc.).
"""

import bpy
import bmesh
import mathutils
from bpy.app.handlers import persistent
from mathutils import Vector
from . import common, fan_in, pan_in
from .common import create_material, COL_HULL, int_to_texture, texture_to_int, TRIGGER_TYPES, LOW_FLAG_OPTIONS, HIGH_FLAG_OPTIONS
from .common import apply_fob_range_scale
from .fob_subtypes import OBJECT_TYPE_NAMES, OBJECT_SUBTYPE_VALUES
import importlib

if "common" in locals():
    importlib.reload(common)


_fob_subtype_enum_guard = set()
_fob_subtype_int_guard = set()
_FOB_TYPE_UNKNOWN = -1
_fob_type_enum_items_cache = None

AI_NODE_PROPERTY_ITEMS = [
    ('0', "Racing Line", "AI follows the main racing line"),
    ('1', "Pickup Route", "AI pickup route"),
    ('2', "Stairs", "AI stairs route"),
    ('3', "Bumpy", "AI bumpy route"),
    ('4', "25mph Slow Down", "AI slows down to 25mph"),
    ('5', "Soft Suspension", "AI soft suspension route"),
    ('6', "Jump Wall", "AI jump wall route"),
    ('7', "Title Screen Slow Down", "AI title screen slow down route"),
    ('8', "Turbo Line", "AI turbo line"),
    ('9', "Long Pickup Route", "AI long pickup route"),
    ('10', "Short Cut", "AI shortcut route"),
    ('11', "Long Cut", "AI long cut route"),
    ('12', "Barrel Block", "AI barrel block route"),
    ('13', "Off Throttle", "AI off throttle route"),
    ('14', "Petrol Throttle", "AI petrol throttle route"),
    ('15', "Wilderness", "AI wilderness route"),
    ('16', "15mph Slow Down", "AI slows down to 15mph"),
    ('17', "20mph Slow Down", "AI slows down to 20mph"),
    ('18', "30mph Slow Down", "AI slows down to 30mph"),
]


def _get_ai_property_enum(self):
    return int(self.get("ai_property_type", getattr(self, "ai_property_type", 0)))


def _set_ai_property_enum(self, value):
    raw = int(value)
    self["ai_property_type"] = raw
    if getattr(self, "ai_property_type", None) != raw:
        self.ai_property_type = raw
    current_flags = int(self.get("ai_flags", getattr(self, "ai_flags", 0)))
    self["ai_flags"] = (current_flags & ~0xFF) | (raw & 0xFF)
    if getattr(self, "ai_flags", None) != self["ai_flags"]:
        self.ai_flags = self["ai_flags"]


def _is_ai_node_object(obj):
    return bool(obj and (getattr(obj, "is_ai_node", False) or obj.get("is_ai_node")))


def _is_pos_node_object(obj):
    return bool(obj and (getattr(obj, "is_pos_node", False) or obj.get("is_pos_node")))


def _ai_node_index_value(obj, fallback=0):
    return int(getattr(obj, "ai_node_index", obj.get("ai_node_index", fallback)))


def _ai_property_source_object(obj):
    if not _is_ai_node_object(obj):
        return obj

    own_index = _ai_node_index_value(obj)
    source_index = int(obj.get("ai_property_source_index", own_index))
    if source_index == own_index:
        return obj

    scene = bpy.context.scene
    if scene:
        for candidate in scene.objects:
            if not _is_ai_node_object(candidate):
                continue
            if _ai_node_index_value(candidate, -1) == source_index:
                return candidate
    return obj


def _get_ai_visual_property_enum(self):
    source = _ai_property_source_object(self)
    return int(source.get("ai_property_type", getattr(source, "ai_property_type", 0)))


def _set_ai_visual_property_enum(self, value):
    source = _ai_property_source_object(self)
    _set_ai_property_enum(source, value)


def _get_ai_visual_start_node(self):
    source = _ai_property_source_object(self)
    return bool(source.get("ai_start_node", getattr(source, "ai_start_node", False)))


def _set_ai_visual_start_node(self, value):
    source = _ai_property_source_object(self)
    source.ai_start_node = bool(value)
    source["ai_start_node"] = bool(value)
    _update_ai_start_node(source, bpy.context)


_ai_node_update_guard = set()


def _ai_node_items(self, context):
    scene = context.scene if context else bpy.context.scene
    nodes = []
    if scene:
        nodes = sorted(
            [
                obj for obj in scene.objects
                if getattr(obj, "is_ai_node", False) or obj.get("is_ai_node")
            ],
            key=lambda obj: (int(getattr(obj, "ai_node_index", obj.get("ai_node_index", 0))), obj.name),
        )
    if not nodes:
        return [("-1", "None", "No AI nodes in the scene")]
    return [
        (
            str(int(getattr(obj, "ai_node_index", obj.get("ai_node_index", index)))),
            obj.name,
            f"Connect to {obj.name}",
        )
        for index, obj in enumerate(nodes)
    ]


def _refresh_ai_route_visuals(context):
    if not context or not getattr(context, "scene", None):
        return
    try:
        fan_in.rebuild_ai_route_visuals(context.scene)
    except Exception:
        pass


def _clamp_ai_ratio(value):
    return max(0.0, min(1.0, float(value)))


def _update_ai_node_route_vertices(obj):
    if not obj or obj.type != "MESH" or not obj.data or len(obj.data.vertices) < 4:
        return

    left = obj.data.vertices[0].co
    right = obj.data.vertices[1].co
    racing_ratio = _clamp_ai_ratio(obj.get("ai_racing_ratio", getattr(obj, "ai_racing_ratio", 0.5)))
    preferred_ratio = _clamp_ai_ratio(obj.get("ai_overtake_ratio", getattr(obj, "ai_overtake_ratio", 0.5)))
    obj.data.vertices[2].co = left.lerp(right, racing_ratio)
    obj.data.vertices[3].co = left.lerp(right, preferred_ratio)
    obj.data.update()


def _update_ai_node_ratios(self, context):
    if self.get("_ai_suppress_geometry_update"):
        return
    key = self.name
    if key in _ai_node_update_guard:
        return
    _ai_node_update_guard.add(key)
    try:
        _update_ai_node_route_vertices(self)
        _refresh_ai_route_visuals(context)
    finally:
        _ai_node_update_guard.discard(key)


def _update_ai_node_width(self, context):
    if self.get("_ai_suppress_geometry_update"):
        return
    key = self.name
    if key in _ai_node_update_guard:
        return
    _ai_node_update_guard.add(key)
    try:
        if self.type == "MESH" and self.data and len(self.data.vertices) >= 2:
            left = self.data.vertices[0].co.copy()
            right = self.data.vertices[1].co.copy()
            center = (left + right) * 0.5
            direction = right - left
            if direction.length <= 0.000001:
                direction = mathutils.Vector((1.0, 0.0, 0.0))
            else:
                direction.normalize()
            half_width = max(0.01, float(getattr(self, "ai_lane_width", self.get("ai_lane_width", 2.0)))) * 0.5
            self.data.vertices[0].co = center - direction * half_width
            self.data.vertices[1].co = center + direction * half_width
            _update_ai_node_route_vertices(self)
            fan_in.update_ai_node_handles(self)
            self.data.update()
        _refresh_ai_route_visuals(context)
    finally:
        _ai_node_update_guard.discard(key)


def _update_ai_flags_from_parts(self, context):
    raw_type = int(self.get("ai_property_type", getattr(self, "ai_property_type", 0))) & 0xFF
    start_bit = 0x100 if bool(self.get("ai_start_node", getattr(self, "ai_start_node", False))) else 0
    current_flags = int(self.get("ai_flags", getattr(self, "ai_flags", 0)))
    self["ai_flags"] = (current_flags & ~0x1FF) | raw_type | start_bit
    if getattr(self, "ai_flags", None) != self["ai_flags"]:
        self.ai_flags = self["ai_flags"]


def _update_ai_wall_flags(self, context):
    left_flags = 0x03 if bool(self.get("ai_left_wall", getattr(self, "ai_left_wall", False))) else 0
    right_flags = 0x03 if bool(self.get("ai_right_wall", getattr(self, "ai_right_wall", False))) else 0
    current_flags = int(self.get("ai_flags", getattr(self, "ai_flags", 0)))
    self["ai_left_wall_flags"] = left_flags
    self["ai_right_wall_flags"] = right_flags
    self["ai_flags"] = (
        (current_flags & ~0xFFFF0000)
        | ((left_flags & 0xFF) << 16)
        | ((right_flags & 0xFF) << 24)
    )
    if getattr(self, "ai_left_wall_flags", None) != left_flags:
        self.ai_left_wall_flags = left_flags
    if getattr(self, "ai_right_wall_flags", None) != right_flags:
        self.ai_right_wall_flags = right_flags
    if getattr(self, "ai_flags", None) != self["ai_flags"]:
        self.ai_flags = self["ai_flags"]

    if self.get("_ai_suppress_geometry_update"):
        return
    _refresh_ai_route_visuals(context)


def _update_ai_start_node(self, context):
    _update_ai_flags_from_parts(self, context)
    if not bool(self.get("ai_start_node", getattr(self, "ai_start_node", False))):
        return

    scene = context.scene if context else bpy.context.scene
    if not scene:
        return

    start_index = _ai_node_index_value(self)
    scene.ai_nodes_start_node = start_index
    scene["ai_nodes_start_node"] = start_index
    for obj in scene.objects:
        if obj == self:
            continue
        if not (getattr(obj, "is_ai_node", False) or obj.get("is_ai_node")):
            continue
        if not bool(getattr(obj, "ai_start_node", obj.get("ai_start_node", False))):
            continue
        obj["ai_start_node"] = False
        obj.ai_start_node = False
        current_flags = int(obj.get("ai_flags", getattr(obj, "ai_flags", 0)))
        obj["ai_flags"] = current_flags & ~0x100
        obj.ai_flags = obj["ai_flags"]
    _refresh_ai_route_visuals(context)


def _set_fob_subtype_int(obj, index, value):
    int_name = f"fob_subtype_{index}"
    obj[int_name] = int(value)
    if index not in _fob_subtype_int_guard:
        _fob_subtype_int_guard.add(index)
        try:
            setattr(obj, int_name, value)
        finally:
            _fob_subtype_int_guard.discard(index)
    else:
        setattr(obj, int_name, value)


def _set_fob_subtype_enum(obj, index, value):
    enum_name = f"fob_subtype_enum_{index}"
    if hasattr(obj, enum_name):
        if index not in _fob_subtype_enum_guard:
            _fob_subtype_enum_guard.add(index)
            try:
                setattr(obj, enum_name, value)
            finally:
                _fob_subtype_enum_guard.discard(index)
        else:
            setattr(obj, enum_name, value)




def _safe_fob_type_name_for_object_name(obj_id):
    name = OBJECT_TYPE_NAMES.get(int(obj_id), f"Unknown_{int(obj_id)}")
    return "_".join(name.replace("/", "_").split())


def _unique_fob_object_name(base_name, current_obj=None):
    existing = {obj.name for obj in bpy.data.objects if obj != current_obj}
    if base_name not in existing:
        return base_name
    index = 1
    while f"{base_name}_{index}" in existing:
        index += 1
    return f"{base_name}_{index}"


def rename_fob_object_with_type(obj):
    if not obj or not (getattr(obj, "is_fob_object", False) or obj.get("is_fob_object")):
        return
    try:
        creation_index = int(obj.get("fob_creation_index", getattr(obj, "fob_creation_index", 0)))
        obj_id = int(obj.get("fob_type", getattr(obj, "fob_type", 0)))
    except (TypeError, ValueError):
        return
    base_name = f"FOB_{creation_index:03d}_{obj_id:03d}_{_safe_fob_type_name_for_object_name(obj_id)}"
    obj.name = _unique_fob_object_name(base_name, obj)


def _fob_type_enum_items(self, context):
    global _fob_type_enum_items_cache
    if _fob_type_enum_items_cache is None:
        _fob_type_enum_items_cache = [
            (str(obj_id), OBJECT_TYPE_NAMES[obj_id], "", 0, obj_id)
            for obj_id in sorted(OBJECT_TYPE_NAMES.keys())
        ]
    return _fob_type_enum_items_cache


def _get_fob_type_enum(self):
    try:
        value = int(self.get("fob_type", getattr(self, "fob_type", _FOB_TYPE_UNKNOWN)))
    except (TypeError, ValueError):
        return _FOB_TYPE_UNKNOWN
    return value if value in OBJECT_TYPE_NAMES else _FOB_TYPE_UNKNOWN


def _set_fob_type_enum(self, value):
    try:
        value = int(value)
    except (TypeError, ValueError):
        return

    prev_type = self.get("fob_type", None)
    if prev_type is None:
        try:
            prev_type = int(getattr(self, "fob_type", value))
        except (TypeError, ValueError):
            prev_type = None
    else:
        try:
            prev_type = int(prev_type)
        except (TypeError, ValueError):
            prev_type = None

    if self.get("fob_type", None) != value:
        self["fob_type"] = value
    if getattr(self, "fob_type", None) != value:
        self.fob_type = value

    if prev_type != value:
        _reset_fob_subtypes(self, value)
        apply_fob_range_scale(self)
        rename_fob_object_with_type(self)


def _reset_fob_subtypes(obj, obj_type):
    for idx in range(1, 5):
        _set_fob_subtype_int(obj, idx, 0)
        if hasattr(type(obj), f"fob_subtype_enum_{idx}"):
            _set_fob_subtype_enum(obj, idx, "0")


def _get_fob_object_type(obj):
    try:
        return int(obj.get("fob_type", getattr(obj, "fob_type", -1)))
    except (TypeError, ValueError):
        return -1


def _clamp_fob_subtype_value(obj, index, value):
    obj_type = _get_fob_object_type(obj)
    values = OBJECT_SUBTYPE_VALUES.get(obj_type, {}).get(index - 1)

    try:
        value = int(value)
    except (TypeError, ValueError):
        value = 0

    if not isinstance(values, list) or not values:
        return value

    if all(isinstance(v, str) for v in values):
        return min(max(value, 0), len(values) - 1)

    if all(isinstance(v, int) for v in values):
        if value in values:
            return value

        min_value = min(values)
        max_value = max(values)
        sorted_values = sorted(values)
        is_contiguous = sorted_values == list(range(min_value, max_value + 1))
        if is_contiguous:
            return min(max(value, min_value), max_value)

        return min(sorted_values, key=lambda allowed: (abs(allowed - value), allowed))

    return value


def _is_contiguous_int_values(values):
    if not isinstance(values, list) or not values or not all(isinstance(v, int) for v in values):
        return False
    sorted_values = sorted(values)
    return sorted_values == list(range(sorted_values[0], sorted_values[-1] + 1))


def _iter_fob_subtype_range_props():
    ranges = set()
    for subtype_values in OBJECT_SUBTYPE_VALUES.values():
        for subtype_index, values in subtype_values.items():
            if _is_contiguous_int_values(values):
                ranges.add((subtype_index + 1, min(values), max(values)))
    return sorted(ranges)


def _make_fob_subtype_range_get(index):
    def getter(self):
        value = self.get(f"fob_subtype_{index}", getattr(self, f"fob_subtype_{index}", 0))
        return _clamp_fob_subtype_value(self, index, value)
    return getter


def _make_fob_subtype_range_set(index):
    def setter(self, value):
        value = _clamp_fob_subtype_value(self, index, value)
        _set_fob_subtype_int(self, index, value)
        if hasattr(type(self), f"fob_subtype_enum_{index}"):
            _set_fob_subtype_enum(self, index, str(value))
        apply_fob_range_scale(self)
    return setter


def _make_fob_subtype_int_update(index):
    def updater(self, context):
        if index in _fob_subtype_int_guard:
            return
        enum_attr = f"fob_subtype_enum_{index}"
        if not hasattr(type(self), enum_attr):
            return
        try:
            value = int(getattr(self, f"fob_subtype_{index}", 0))
        except (TypeError, ValueError):
            value = 0
        value = _clamp_fob_subtype_value(self, index, value)
        if getattr(self, f"fob_subtype_{index}", None) != value:
            _set_fob_subtype_int(self, index, value)
        _set_fob_subtype_enum(self, index, str(value))
        apply_fob_range_scale(self)
    return updater


def _make_fob_subtype_enum_items(index):
    def items(self, context):
        obj_type = _get_fob_object_type(self)

        values = OBJECT_SUBTYPE_VALUES.get(obj_type, {}).get(index - 1)

        try:
            current_raw = self.get(f"fob_subtype_{index}", getattr(self, f"fob_subtype_{index}", 0))
            current_value = str(_clamp_fob_subtype_value(self, index, current_raw))
        except (TypeError, ValueError):
            current_value = "0"

        if isinstance(values, list) and values:
            if all(isinstance(v, str) for v in values):
                enum_items = [(str(i), name, "") for i, name in enumerate(values)]
                if current_value not in {identifier for identifier, _, _ in enum_items}:
                    enum_items.append((current_value, f"Unknown ({current_value})", "Value not present in subtype list"))
                return enum_items

            if all(isinstance(v, int) for v in values):
                sorted_vals = sorted(values)
                is_contiguous = sorted_vals == list(range(sorted_vals[0], sorted_vals[-1] + 1))
                if len(values) <= 16 and not is_contiguous:
                    enum_items = [(str(v), str(v), "") for v in values]
                    if current_value not in {identifier for identifier, _, _ in enum_items}:
                        enum_items.append((current_value, f"Unknown ({current_value})", "Value not present in subtype list"))
                    return enum_items

        return [(current_value, f"Value {current_value}", "Numeric subtype is edited directly")]
    return items


def _make_fob_subtype_enum_update(index):
    def updater(self, context):
        if index in _fob_subtype_enum_guard:
            return
        try:
            value = int(getattr(self, f"fob_subtype_enum_{index}", 0))
        except (TypeError, ValueError):
            value = 0
        value = _clamp_fob_subtype_value(self, index, value)
        _set_fob_subtype_int(self, index, value)
        apply_fob_range_scale(self)
    return updater


class _LiveEditBMeshDict(dict):
    """Dictionary-like helper that returns fresh edit-mode BMesh objects without caching them."""

    __slots__ = ()

    def __setitem__(self, key, value):
        super().__setitem__(key, True)

    def acquire(self, key):
        obj = bpy.data.objects.get(key)
        if obj and obj.type == 'MESH' and obj.mode == 'EDIT':
            try:
                return bmesh.from_edit_mesh(obj.data)
            except (RuntimeError, ReferenceError):
                return None
        return None

    def __getitem__(self, key):
        if not super().__contains__(key):
            raise KeyError(key)
        bm = self.acquire(key)
        if bm is None:
            raise KeyError(key)
        return bm

    def get(self, key, default=None):
        if super().__contains__(key):
            bm = self.acquire(key)
            if bm is not None:
                return bm
        return default

    def values(self):
        for key in self.keys():
            bm = self.acquire(key)
            if bm is not None:
                yield bm

    def items(self):
        for key in self.keys():
            bm = self.acquire(key)
            if bm is not None:
                yield (key, bm)


bmesh_dic = _LiveEditBMeshDict()
_ai_route_visual_update_guard = False
_ai_route_visual_transform_state = {}
_pos_route_visual_update_guard = False
_pos_route_visual_transform_state = {}


@persistent
def edit_object_change_handler(scene):
    """Track edit-mode meshes without caching their BMesh instances."""
    obj = bpy.context.view_layer.objects.active

    if obj is None or obj.type != 'MESH':
        bmesh_dic.clear()
        return

    if obj.mode == 'EDIT':
        bmesh_dic.clear()
        bmesh_dic[obj.name] = True
    else:
        bmesh_dic.clear()


def _ai_transform_key(obj):
    matrix = obj.matrix_world
    return tuple(round(value, 6) for row in matrix for value in row)


def _route_visual_transform_changed(scene, depsgraph, predicate, state):
    updates = getattr(depsgraph, "updates", []) if depsgraph else []
    if updates:
        for update in updates:
            obj = getattr(update, "id", None)
            if not isinstance(obj, bpy.types.Object) or not predicate(obj):
                continue
            key = _ai_transform_key(obj)
            if state.get(obj.name) != key:
                state[obj.name] = key
                return True
        return False

    for obj in scene.objects:
        if not predicate(obj):
            continue
        key = _ai_transform_key(obj)
        if state.get(obj.name) != key:
            state[obj.name] = key
            return True
    return False


@persistent
def ai_route_visual_change_handler(scene, depsgraph=None):
    global _ai_route_visual_update_guard
    if _ai_route_visual_update_guard:
        return

    if not _route_visual_transform_changed(scene, depsgraph, _is_ai_node_object, _ai_route_visual_transform_state):
        return

    _ai_route_visual_update_guard = True
    try:
        fan_in.rebuild_ai_route_visuals(scene)
    except Exception:
        pass
    finally:
        _ai_route_visual_update_guard = False


@persistent
def pos_route_visual_change_handler(scene, depsgraph=None):
    global _pos_route_visual_update_guard
    if _pos_route_visual_update_guard:
        return

    if not _route_visual_transform_changed(scene, depsgraph, _is_pos_node_object, _pos_route_visual_transform_state):
        return

    _pos_route_visual_update_guard = True
    try:
        pan_in.rebuild_pos_route_visuals(scene)
    except Exception:
        pass
    finally:
        _pos_route_visual_update_guard = False


def generate_chull(context):
    scene = context.scene
    obj = context.object
    hull_name = "Convex_Hull"

    # Duplicate the object
    duplicate_obj = obj.copy()
    duplicate_obj.data = obj.data.copy()

    # Temporarily link the duplicate for processing
    temp_collection = bpy.data.collections.new("Temp_Collection")
    bpy.context.scene.collection.children.link(temp_collection)
    temp_collection.objects.link(duplicate_obj)

    bpy.context.view_layer.objects.active = duplicate_obj
    duplicate_obj.select_set(True)

    # Convert the duplicate to a convex hull
    bm = bmesh.new()
    bm.from_mesh(duplicate_obj.data)

    try:
        chull_out = bmesh.ops.convex_hull(bm, input=bm.verts)

        # Validate convex hull geometry
        if not chull_out["geom"]:
            print("No valid convex hull geometry created.")
            bm.free()
            return None

        # Remove non-hull geometry
        for face in bm.faces[:]:
            if face not in chull_out["geom"]:
                bm.faces.remove(face)
        for edge in bm.edges[:]:
            if edge not in chull_out["geom"]:
                bm.edges.remove(edge)
        for vert in bm.verts[:]:
            if vert not in chull_out["geom"]:
                bm.verts.remove(vert)

        # Create a new mesh and object for the convex hull
        me = bpy.data.meshes.new(hull_name)
        bm.to_mesh(me)
        bm.free()

        hull_ob = bpy.data.objects.new(hull_name, me)
        hull_ob.is_hull_convex = True
        hull_ob["is_hull_convex"] = True
        hull_ob.matrix_world = obj.matrix_world.copy()
        hull_ob.show_transparent = True
        hull_ob.show_wire = True
        me.materials.append(create_material("RVHull", COL_HULL, 0.3))

        # Link to the same collections as the original object
        for collection in obj.users_collection:
            collection.objects.link(hull_ob)

        # Remove the temporary duplicate
        bpy.data.objects.remove(duplicate_obj, do_unlink=True)
        bpy.data.collections.remove(temp_collection)

        # Set the convex hull as the active object
        context.view_layer.objects.active = hull_ob
        hull_ob.select_set(True)
        context.view_layer.update()

        return hull_ob
    except Exception as e:
        print(f"Failed to generate convex hull: {e}")
        bm.free()
        bpy.data.objects.remove(duplicate_obj, do_unlink=True)
        bpy.data.collections.remove(temp_collection)
        return None
    
def get_trigger_type_items(self, context):
    """Generates a list of trigger type items for the EnumProperty."""
    return [(str(k), v, "") for k, v in TRIGGER_TYPES.items()]
    
def get_trigger_type(self):
    """Retrieve the trigger_type stored as an integer."""
    return self.get("trigger_type", 0)  # Return as an integer

def set_trigger_type(self, value):
    """Store the trigger_type as an integer."""
    self["trigger_type"] = int(value)  # Store as integer
    self["trigger_type_description"] = TRIGGER_TYPES.get(int(value), "UnknownType")

    # Reset high_flag_enum if not needed
    if int(value) not in HIGH_FLAG_OPTIONS:
        self["high_flag_enum"] = 0

def get_low_flag_items(self, context):
    """Generate a list of low flag items based on the trigger type."""
    obj = context.object
    trigger_type = int(obj.trigger_type_enum)
    low_flag_data = LOW_FLAG_OPTIONS.get(trigger_type)

    if not low_flag_data or "values" not in low_flag_data:
        return []

    return [(str(k), v, "") for k, v in low_flag_data["values"].items()]

def get_high_flag_items(self, context):
    """Generate a list of high flag items based on the trigger type."""
    obj = context.object
    trigger_type = int(obj.trigger_type_enum)  # Retrieve the current trigger type
    high_flag_data = HIGH_FLAG_OPTIONS.get(trigger_type)

    if not high_flag_data:
        return []

    return [(str(i), f"High Flag {i}", "") for i in range(high_flag_data["range"][0], high_flag_data["range"][1] + 1)]

def get_low_flag(self):
    """Retrieve the stored low flag value and return it as an integer."""
    return self.get("flag_low", 0)  # Return as an integer

def set_low_flag(self, value):
    """Store the low flag value as an integer."""
    self["flag_low"] = int(value)  # Store as integer

def get_high_flag(self):
    """Retrieve the stored high flag value as an integer."""
    return self.get("flag_high", 0)  # Return as an integer

def set_high_flag(self, value):
    """Set the high flag value."""
    self["flag_high"] = int(value)
    
def map_strength_to_threshold(strength: int) -> float:
    return round(0.90 - (strength - 1) * 0.05, 2)

def trigger_type_items(self, context):
    return [(str(k), v, "") for k, v in TRIGGER_TYPES.items()]

def fob_type_items(self, context):
    return [(str(k), v, "") for k, v in OBJECT_TYPE_NAMES.items()]

def visibox_type_items(self, context):
    return [
        ('1', "Camera", "Camera visibility box"),
        ('2', "Cubes", "Cubes visibility box")
    ]

def get_rig_root(obj):
    while obj and obj.parent:
        obj = obj.parent
    return obj

def get_rig_objects(root):
    return [root] + list(root.children_recursive)

def rig_world_bbox_center(objs):
    pts = []
    for o in objs:
        if o.type not in {'MESH', 'EMPTY'}:
            continue
        for c in o.bound_box:
            pts.append(o.matrix_world @ Vector(c))
    if not pts:
        return None
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return (mn + mx) * 0.5
