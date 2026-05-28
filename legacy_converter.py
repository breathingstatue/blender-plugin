import os
import ast
import bpy
import bmesh

from bpy.types import Operator
from bpy.props import StringProperty, BoolProperty

from .common import int_to_texture, set_scene_value, MATERIALS, COLORS

default_layer_visibility = (True,) + (False,) * 19
material_enum_values = {item[0] for item in MATERIALS}

scene_prop_specs = {
    "face_edit_mode": {"type": "string", "default": "prm", "enum": {"prm", "ncp"}, "case": "lower"},
    "select_material": {"type": "string", "default": "0", "enum": material_enum_values},
    "enable_tex_mode": {"type": "bool", "default": True},
    "prefer_tex_solid_mode": {"type": "bool", "default": False},
    "rename_all_name": {"type": "string", "default": "example.prm"},
    "batch_bake_model_rgb": {"type": "bool", "default": True},
    "batch_bake_model_env": {"type": "bool", "default": True},
    "prm_check_parameters": {"type": "bool", "default": True},
    "vertex_color_picker": {"type": "color3", "default": (0.0, 0.0, 1.0)},
    "envidx": {"type": "int", "default": 0},
    "revolt_dir": {"type": "string", "default": ""},
    "triangulate_ngons": {"type": "bool", "default": True},
    "use_tex_num": {"type": "bool", "default": False},
    "apply_scale": {"type": "bool", "default": True},
    "apply_rotation": {"type": "bool", "default": True},
    "apply_translation": {"type": "bool", "default": False},
    "last_exported_filepath": {"type": "string", "default": ""},
    "last_exported_format": {"type": "string", "default": ""},
    "ncp_export_collgrid": {"type": "bool", "default": True},
    "ncp_collgrid_size": {"type": "int", "default": 1024},
    "ncp_export_selected": {"type": "bool", "default": False},
    "w_parent_meshes": {"type": "bool", "default": False},
    "w_import_bound_boxes": {"type": "bool", "default": False},
    "w_import_cubes": {"type": "bool", "default": False},
    "w_import_big_cubes": {"type": "bool", "default": False},
    "w_bound_box_layers": {"type": "bool_vector", "length": 20, "default": default_layer_visibility},
    "w_cube_layers": {"type": "bool_vector", "length": 20, "default": default_layer_visibility},
    "w_big_cube_layers": {"type": "bool_vector", "length": 20, "default": default_layer_visibility},
    "light1": {"type": "string", "default": "SUN", "enum": {"SUN", "HEMI", "POINT", "SPOT", "AREA"}, "case": "upper"},
    "light2": {"type": "string", "default": "HEMI", "enum": {"SUN", "HEMI", "POINT", "SPOT", "AREA"}, "case": "upper"},
    "light_intensity1": {"type": "float", "default": 1.5},
    "light_intensity2": {"type": "float", "default": 0.05},
    "light_orientation": {"type": "string", "default": "Z", "enum": {"X", "Y", "Z", "-X", "-Y", "-Z"}, "case": "upper"},
    "shadow_method": {"type": "string", "default": "ADAPTIVE_QMC", "enum": {"ADAPTIVE_QMC", "HIGH_QUALITY"}, "case": "upper"},
    "shadow_quality": {"type": "string", "default": "128", "enum": {"32", "64", "128", "256", "512"}},
    "shadow_resolution": {"type": "string", "default": "128", "enum": {"128", "256", "512"}},
    "shadow_softness": {"type": "float", "default": 1.0},
    "shadow_table": {"type": "string", "default": ""},
    "texture_animations": {"type": "string", "default": "[]"},
    "ta_max_slots": {"type": "int", "default": 0},
    "ta_current_slot": {"type": "int", "default": 0},
    "ta_max_frames": {"type": "int", "default": 2},
    "ta_current_frame": {"type": "int", "default": 0},
    "ta_current_frame_tex": {"type": "int", "default": 0},
    "ta_current_frame_delay": {"type": "float", "default": 0.01},
    "ta_current_frame_uv0": {"type": "float_vector", "length": 2, "default": (0.0, 0.0)},
    "ta_current_frame_uv1": {"type": "float_vector", "length": 2, "default": (1.0, 0.0)},
    "ta_current_frame_uv2": {"type": "float_vector", "length": 2, "default": (1.0, 1.0)},
    "ta_current_frame_uv3": {"type": "float_vector", "length": 2, "default": (0.0, 1.0)},
    "ta_sync_with_face": {"type": "bool", "default": False},
    "ta_texture": {"type": "int", "default": 0},
    "ta_delay": {"type": "float", "default": 0.02},
    "ta_frame_start": {"type": "int", "default": 0},
    "ta_frame_end": {"type": "int", "default": 2},
    "grid_x": {"type": "int", "default": 2},
    "grid_y": {"type": "int", "default": 2},
}

object_prop_specs = {
    "is_bcube": {"type": "bool", "default": False},
    "is_cube": {"type": "bool", "default": False},
    "is_bbox": {"type": "bool", "default": False},
    "ignore_ncp": {"type": "bool", "default": False},
    "bcube_mesh_indices": {"type": "string", "default": ""},
    "is_hull_sphere": {"type": "bool", "default": False},
    "is_hull_convex": {"type": "bool", "default": False},
    "is_instance": {"type": "bool", "default": False},
    "is_car_part": {"type": "bool", "default": False},
    "fin_col": {"type": "color3", "default": (0.5, 0.5, 0.5)},
    "fin_envcol": {"type": "color4", "default": (1.0, 1.0, 1.0, 1.0)},
    "fin_priority": {"type": "int", "default": 1},
    "fin_env": {"type": "bool", "default": True},
    "fin_model_rgb": {"type": "bool", "default": False},
    "fin_hide": {"type": "bool", "default": False},
    "fin_no_mirror": {"type": "bool", "default": False},
    "fin_no_lights": {"type": "bool", "default": False},
    "fin_no_cam_coll": {"type": "bool", "default": False},
    "fin_no_obj_coll": {"type": "bool", "default": False},
    "fin_lod_bias": {"type": "int", "default": 1024},
    "is_mirror_plane": {"type": "bool", "default": False},
    "is_track_zone": {"type": "bool", "default": False},
    "track_zone_id": {"type": "int", "default": 0},
    "is_model": {"type": "bool", "default": False},
}

# --- Patch hook for add-on register ---

def apply_patches():
    """Compatibility hook called by __init__.py during register().

    Older releases referenced legacy_converter.apply_patches(), but this module
    didn't expose it, causing AttributeError and leaving Blender with a partial
    registration (leading to class registration errors). Keep it as a no-op
    placeholder so registration can proceed safely.
    """
    return

def _get_legacy_group(owner, key="revolt"):
    if owner is None:
        return None
    try:
        attr = getattr(owner, key)
    except AttributeError:
        attr = None
    if attr:
        return attr
    if isinstance(owner, bpy.types.ID) and key in owner.keys():
        return owner[key]
    if hasattr(owner, "get"):
        return owner.get(key)
    return None

def _legacy_has(group, name):
    if group is None:
        return False
    try:
        getattr(group, name)
        return True
    except AttributeError:
        pass
    if isinstance(group, dict):
        return name in group
    try:
        group[name]
        return True
    except Exception:
        return False

def _legacy_get(group, name):
    if group is None:
        return None
    try:
        return getattr(group, name)
    except AttributeError:
        pass
    if isinstance(group, dict):
        return group.get(name)
    try:
        return group[name]
    except Exception:
        return None

def _clear_legacy_group(owner, key="revolt"):
    if owner is None:
        return
    if isinstance(owner, bpy.types.ID) and key in owner.keys():
        try:
            del owner[key]
        except Exception:
            pass
        ui = owner.get("_RNA_UI")
        if isinstance(ui, dict) and key in ui:
            try:
                del ui[key]
            except Exception:
                pass
    if hasattr(owner, key):
        try:
            delattr(owner, key)
        except AttributeError:
            pass

def _as_sequence(value):
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if hasattr(value, "to_list"):
        try:
            return list(value.to_list())
        except Exception:
            pass
    try:
        return list(value)
    except TypeError:
        return [value]

def _to_bool(value, default=False):
    if value is None:
        return default
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)

def _to_int(value, default=0):
    if value is None:
        return default
    if isinstance(value, bool):
        return int(value)
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return default

def _to_float(value, default=0.0):
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default

def _coerce_color(value, length, default):
    seq = _as_sequence(value)
    if not seq:
        seq = list(default)
    floats = [_to_float(item, 0.0) for item in seq]
    if floats and max(abs(x) for x in floats) > 1.0:
        floats = [x / 255.0 for x in floats]
    while len(floats) < length:
        index = len(floats)
        fallback = default[index] if index < len(default) else default[-1]
        floats.append(_to_float(fallback, 1.0))
    floats = [max(0.0, min(1.0, x)) for x in floats[:length]]
    return tuple(floats)

def _coerce_float_vector(value, length, default=None):
    seq = _as_sequence(value)
    if not seq:
        seq = list(default) if default is not None else []
    coerced = [_to_float(item, 0.0) for item in seq]
    if length is None:
        length = len(coerced) if coerced else (len(default) if default else 0)
    default_seq = list(default) if default is not None else [0.0] * length
    while len(coerced) < length:
        idx = len(coerced)
        fallback = default_seq[idx] if idx < len(default_seq) else default_seq[-1]
        coerced.append(_to_float(fallback, 0.0))
    return tuple(coerced[:length])

def _coerce_bool_vector(value, length, default=None):
    seq = _as_sequence(value)
    if not seq:
        seq = list(default) if default is not None else []
    coerced = [_to_bool(item, False) for item in seq]
    if length is None:
        length = len(coerced) if coerced else (len(default) if default else 0)
    default_seq = list(default) if default is not None else [False] * length
    while len(coerced) < length:
        idx = len(coerced)
        fallback = default_seq[idx] if idx < len(default_seq) else default_seq[-1]
        coerced.append(_to_bool(fallback, False))
    return tuple(coerced[:length])

def _coerce_value(spec, value):
    default = spec.get("default")
    value_type = spec.get("type")
    if value is None:
        coerced = default
    else:
        try:
            if value_type == "bool":
                coerced = _to_bool(value, default if default is not None else False)
            elif value_type == "int":
                coerced = _to_int(value, default if default is not None else 0)
            elif value_type == "float":
                coerced = _to_float(value, default if default is not None else 0.0)
            elif value_type == "string":
                coerced = str(value)
            elif value_type == "color3":
                coerced = _coerce_color(value, 3, default or (0.0, 0.0, 1.0))
            elif value_type == "color4":
                coerced = _coerce_color(value, 4, default or (1.0, 1.0, 1.0, 1.0))
            elif value_type == "float_vector":
                coerced = _coerce_float_vector(value, spec.get("length"), default)
            elif value_type == "bool_vector":
                coerced = _coerce_bool_vector(value, spec.get("length"), default)
            else:
                coerced = value
        except Exception:
            coerced = default

    enum_values = spec.get("enum")
    if enum_values is not None:
        if coerced is None:
            coerced = default
        candidate = str(coerced) if coerced is not None else ""
        case_behavior = spec.get("case")
        if case_behavior == "upper":
            candidate = candidate.upper()
        elif case_behavior == "lower":
            candidate = candidate.lower()
        synonyms = spec.get("enum_synonyms", {})
        candidate = synonyms.get(candidate, candidate)
        if candidate not in enum_values:
            if case_behavior == "upper":
                candidate = candidate.replace(" ", "_")
            candidate = synonyms.get(candidate, candidate)
        if candidate not in enum_values:
            coerced = default
        else:
            coerced = candidate
    return coerced

def _assign_property(owner, name, value):
    try:
        setattr(owner, name, value)
        return True
    except Exception:
        return False

def _mesh_has_color_layer(mesh, name):
    if mesh is None:
        return False
    ca = getattr(mesh, "color_attributes", None)
    if ca:
        try:
            if ca.get(name):
                return True
        except AttributeError:
            pass
    vc = getattr(mesh, "vertex_colors", None)
    if vc:
        try:
            vc[name]
            return True
        except KeyError:
            pass
    if mesh.loops and mesh.polygons:
        bm = bmesh.new()
        try:
            bm.from_mesh(mesh)
            if bm.loops.layers.color.get(name) or bm.faces.layers.color.get(name):
                return True
        finally:
            bm.free()
    return False


def ensure_alpha_color_layer(mesh, alpha_values=None, default_alpha=1.0):
    """
    Ensure a 'Alpha' color attribute exists (CORNER, FLOAT_COLOR) and fill it.
    Fill RGB with 1-alpha (grayscale), and set A to 1.0 so it never influences transparency.
    """
    if mesh is None or not mesh.polygons:
        return False
    ca = getattr(mesh, "color_attributes", None)
    if ca is None:
        return False
    attr = ca.get("Alpha")
    if attr is None:
        attr = ca.new(name="Alpha", type='FLOAT_COLOR', domain='CORNER')

    data = attr.data
    loop_count = len(mesh.loops)

    def clamp01(x):
        try:
            return max(0.0, min(1.0, float(x)))
        except Exception:
            return 0.0

    if alpha_values is None:
        a = clamp01(default_alpha)
        g = 1.0 - a
        for i in range(loop_count):
            data[i].color = (g, g, g, 1.0)
    else:
        if len(alpha_values) != loop_count:
            raise ValueError("alpha_values length must match mesh loops")
        for i, a in enumerate(alpha_values):
            a = clamp01(a)
            g = 1.0 - a
            data[i].color = (g, g, g, 1.0)
    return True

class ConvertLegacyTextureMappings(Operator):
    bl_idname = "helpers.convert_legacy_texture_mappings"
    bl_label = "Convert Legacy Texture Mappings"
    bl_description = (
        "Create materials from available images and assign them to faces using the "
        "Texture Number layer. Also recreates attribute materials (Col/Alpha/Env/Model RGB) "
        "and converts NCP materials when possible. In car mode, renames images/materials "
        "to car.bmp, carbox.bmp, shadow.bmp, etc."
    )
    bl_options = {"REGISTER", "UNDO"}

    base_name: StringProperty(
        name="Texture Base",
        description="Optional base for track textures; ignored in car mode.",
        default=""
    )
    is_car_mode: BoolProperty(
        name="Is Legacy Car",
        description="Use car texture handling (car.bmp, carbox.bmp, shadow.bmp...)",
        default=False,
    )

    _instance_flags_migrated = 0

    # ---------- Car naming registry (ignores texture numbers) ----------
    def _init_car_skin_registry(self):
        self._car_skin_name_for_image = {}
        self._car_assigned_names = set()

    def _next_car_alt_name(self):
        for code in range(ord('b'), ord('z') + 1):
            name = f"car{chr(code)}.bmp"
            if name not in self._car_assigned_names:
                return name
        i = 2
        while True:
            name = f"car_alt_{i}.bmp"
            if name not in self._car_assigned_names:
                return name
            i += 1

    def _canonical_car_name_for_image(self, image):
        n = (image.name or "").lower()
        base, _ = os.path.splitext(n)

        # Priority canonical names
        if "carbox" in base:
            target = "carbox.bmp"
        elif "shadow" in base:
            target = "shadow.bmp"
        elif base == "car":
            target = "car.bmp"
        elif base.startswith("car") and len(base) == 4 and base[3].isalpha():
            # Keep existing carb/carc/... as-is
            target = f"{base}.bmp"
        else:
            # Unknown skin name: first becomes car.bmp, others become carb/carc/...
            if "car.bmp" not in self._car_assigned_names:
                target = "car.bmp"
            else:
                target = self._next_car_alt_name()

        self._car_assigned_names.add(target)
        return target

    def _rename_image_datablock(self, image, target_name):
        if not image or not target_name:
            return image
        existing = bpy.data.images.get(target_name)
        if existing and existing is not image:
            return existing
        try:
            image.name = target_name
        except Exception:
            pass
        return image

    def _prepare_car_textures_and_materials(self, material_lookup, image_lookup):
        renamed = 0
        created = 0
        processed = set()

        # Iterate over a copy, as we may rename
        for img in list(bpy.data.images):
            can_name = self._canonical_car_name_for_image(img)

            # Rename the image datablock to its canonical name (if needed)
            if img.name != can_name:
                renamed_img = self._rename_image_datablock(img, can_name)
                if renamed_img is not img:
                    # Another image already had that canonical name; use the existing one
                    pass
                renamed += 1

            if can_name in processed:
                continue
            processed.add(can_name)

            # Ensure there is a material for the canonical image
            image = bpy.data.images.get(can_name)
            if image:
                mat = bpy.data.materials.get(can_name)
                if not mat:
                    mat = self._create_material_from_image(image, canonical_name=can_name)
                    created += 1

                # Update lookups so later code can find them by aliases
                for alias in self._material_aliases(mat.name):
                    material_lookup[alias] = mat
                for alias in self._image_aliases(image):
                    image_lookup[alias] = image

        return renamed, created

    # ------------------------------------------------------------------

    def invoke(self, context, event):
        base = context.scene.get("level_texture_base", "")
        self.base_name = base or ""
        try:
            self.is_car_mode = (self.base_name.lower() == "car")
        except AttributeError:
            self.is_car_mode = False
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "is_car_mode")
        row = layout.row()
        row.enabled = not self.is_car_mode
        row.prop(self, "base_name")
        if self.is_car_mode:
            layout.label(text="Texture base is ignored in car mode.", icon='INFO')

    def execute(self, context):
        self._is_car_mode = bool(self.is_car_mode)
        if self._is_car_mode:
            self._init_car_skin_registry()

        legacy_summary = self._convert_legacy_properties(context)
        mesh_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
        if not mesh_objects:
            if legacy_summary:
                summary_msg = self._format_legacy_summary(legacy_summary)
                if summary_msg:
                    self.report({'INFO'}, f"Converted legacy properties: {summary_msg}")
                return {'FINISHED'}
            self.report({'WARNING'}, "Select at least one mesh object.")
            return {'CANCELLED'}

        if context.object and context.object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        base_lower = "" if self._is_car_mode else (self.base_name.strip().lower())

        scene = context.scene
        self._instance_flags_migrated = 0

        material_lookup = self._build_material_lookup()
        image_lookup = self._build_image_lookup()

        if self._is_car_mode:
            renamed_count, created_count = self._prepare_car_textures_and_materials(material_lookup, image_lookup)
            # Refresh lookups after possible renames/creations
            material_lookup = self._build_material_lookup()
            image_lookup = self._build_image_lookup()

            if created_count or renamed_count:
                self.report({'INFO'}, f"Car mode: renamed {renamed_count} image(s), created {created_count} material(s)")

        if self._is_car_mode:
            set_scene_value(scene, "level_texture_base", "car")
        elif base_lower:
            set_scene_value(scene, "level_texture_base", base_lower)

        attribute_names = ("Col", "Alpha", "Env", "RGBModelColor")
        self.attribute_counts = {name: 0 for name in attribute_names}
        self.ncp_faces_assigned = 0
        self.ncp_materials_created = 0
        self._created_ncp_material_names = set()

        total_faces = 0
        total_assigned = 0
        missing_texnums = set()

        for obj in mesh_objects:
            self._instance_flags_migrated += self._migrate_instance_flag(obj)
            faces, assigned, missing = self._convert_object(
                obj, base_lower, material_lookup, image_lookup
            )
            total_faces += faces
            total_assigned += assigned
            missing_texnums.update(missing)

            # Ensure attribute materials. For Alpha, make sure the layer exists and is opaque.
            created_attrs = self._convert_attribute_materials(
                obj,
                [("Col", "Col"), ("Alpha", "Alpha"), ("Env", "Env")]
            )
            for attr in created_attrs:
                if attr in self.attribute_counts:
                    self.attribute_counts[attr] += 1

            created_rgb = self._convert_attribute_materials(
                obj,
                [("RGBModelColor", "RGBModelColor")]
            )
            for attr in created_rgb:
                if attr in self.attribute_counts:
                    self.attribute_counts[attr] += 1

            faces_updated, new_materials = self._convert_ncp_materials(obj)
            self.ncp_faces_assigned += faces_updated
            self.ncp_materials_created += new_materials

        texture_animation_migrated = self._migrate_texture_animations(context)

        notes = []

        if self._is_car_mode:
            notes.append("Legacy Converter: using car texture mapping (canonical names).")

        if base_lower and not self._is_car_mode:
            set_scene_value(scene, "level_texture_base", base_lower)

            # Optional rename/fix tools for non-car mode can go here if you keep them

        if total_faces == 0:
            self.report({'WARNING'}, "No faces processed. Ensure meshes have a 'Texture Number' layer.")
        else:
            self.report({'INFO'}, f"Assigned materials to {total_assigned} of {total_faces} faces across {len(mesh_objects)} object(s).")

        if missing_texnums:
            missing_list = ", ".join(str(num) for num in sorted(missing_texnums))
            self.report({'WARNING'}, f"No images or materials found for texture numbers: {missing_list}")

        attribute_labels = {"Col": "Vertex Color", "Alpha": "Vertex Alpha", "Env": "EnvMap", "RGBModelColor": "Model Color"}
        attribute_summary = [f"{attribute_labels[name]} ({count})" for name, count in self.attribute_counts.items() if count]
        if attribute_summary:
            notes.append("Created attribute materials: " + ", ".join(attribute_summary))

        if self.ncp_faces_assigned:
            ncp_msg = f"Assigned NCP materials to {self.ncp_faces_assigned} face(s)"
            if self.ncp_materials_created:
                ncp_msg += f" ({self.ncp_materials_created} new material(s))"
            notes.append(ncp_msg)

        if texture_animation_migrated:
            notes.append("Migrated legacy texture animation data.")

        if getattr(self, "_instance_flags_migrated", 0):
            notes.append(f"Migrated instance flag for {self._instance_flags_migrated} object(s).")

        if legacy_summary:
            summary_msg = self._format_legacy_summary(legacy_summary)
            if summary_msg:
                notes.append(f"Converted legacy properties: {summary_msg}")

        for m in notes:
            self.report({'INFO'}, m)

        return {'FINISHED'}

    # --------- Legacy props conversion ---------
    def _convert_legacy_properties(self, context):
        scene = context.scene
        scene_converted = self._convert_legacy_scene(scene)
        object_converted = 0
        for obj in context.scene.objects:
            if self._convert_legacy_object(obj):
                object_converted += 1
        if not scene_converted and object_converted == 0:
            return None
        return {"scene": scene_converted, "objects": object_converted}

    def _convert_legacy_scene(self, scene):
        legacy = _get_legacy_group(scene)
        if not legacy:
            return False
        changed = False
        for name, spec in scene_prop_specs.items():
            if not _legacy_has(legacy, name):
                continue
            value = _legacy_get(legacy, name)
            coerced = _coerce_value(spec, value)
            if _assign_property(scene, name, coerced):
                changed = True
        if changed:
            _clear_legacy_group(scene)
        return changed

    def _convert_legacy_object(self, obj):
        legacy = _get_legacy_group(obj)
        if not legacy:
            return False
        changed = False
        for name, spec in object_prop_specs.items():
            if not _legacy_has(legacy, name):
                continue
            value = _legacy_get(legacy, name)
            if _assign_property(obj, name, _coerce_value(spec, value)):
                changed = True
        if changed:
            _clear_legacy_group(obj)
        return changed

    # --------- Core conversion ---------
    def _convert_object(self, obj, base_name, material_lookup, image_lookup):
        mesh = obj.data
        bm = bmesh.new()
        bm.from_mesh(mesh)

        tex_layer = bm.faces.layers.int.get("Texture Number")
        if tex_layer is None:
            bm.free()
            return 0, 0, set()

        bm.faces.ensure_lookup_table()
        faces_total = len(bm.faces)
        unique_texnums = sorted({face[tex_layer] for face in bm.faces if face[tex_layer] >= 0})
        if not unique_texnums:
            bm.free()
            return faces_total, 0, set()

        material_indices = {}
        missing = set()

        for tex_num in unique_texnums:
            mat = self._ensure_material_for_texnum(tex_num, base_name, material_lookup, image_lookup)
            if mat:
                if mat.name not in mesh.materials:
                    mesh.materials.append(mat)
                material_indices[tex_num] = mesh.materials.find(mat.name)
            else:
                missing.add(tex_num)

        assigned = 0
        for face in bm.faces:
            tex_value = face[tex_layer]
            if tex_value >= 0 and tex_value in material_indices:
                face.material_index = material_indices[tex_value]
                assigned += 1

        bm.to_mesh(mesh)
        mesh.update()
        bm.free()

        return faces_total, assigned, missing

    def _convert_attribute_materials(self, obj, attr_pairs):
        mesh = obj.data
        if mesh is None:
            return []

        # Seed Alpha layer if missing (opaque)
        scene = bpy.context.scene
        alpha_pct = getattr(scene, "vertex_alpha_percentage", None)
        default_alpha = (float(alpha_pct) / 100.0) if alpha_pct is not None else 1.0

        created_attrs = []
        for attr_name, suffix in attr_pairs:
            if attr_name == "Alpha" and not _mesh_has_color_layer(mesh, "Alpha"):
                ensure_alpha_color_layer(mesh, default_alpha=default_alpha)

            if not self._has_color_attribute(obj, mesh, attr_name):
                continue

            material, created = self._ensure_attribute_material(obj, attr_name, suffix)
            if created:
                created_attrs.append(attr_name)
        return created_attrs

    def _convert_ncp_materials(self, obj):
        mesh = obj.data
        if mesh is None:
            return 0, 0

        bm = bmesh.new()
        bm.from_mesh(mesh)
        ncp_layer = bm.faces.layers.int.get("NCPType")
        if ncp_layer is None:
            bm.free()
            return 0, 0

        material_layer = bm.faces.layers.int.get("Material")
        if material_layer is None:
            material_layer = bm.faces.layers.int.new("Material")

        unique_types = set(face[ncp_layer] for face in bm.faces)
        material_map = {}
        new_materials = 0

        for ncp_value in unique_types:
            mat, created = self._get_or_create_ncp_material(mesh, ncp_value)
            if created:
                new_materials += 1
            material_map[ncp_value] = mat

        faces_updated = 0
        for face in bm.faces:
            ncp_value = face[ncp_layer]
            mat = material_map.get(ncp_value)
            if not mat:
                continue
            face[material_layer] = ncp_value
            mat_index = mesh.materials.find(mat.name)
            if mat_index >= 0:
                face.material_index = mat_index
                faces_updated += 1

        bm.to_mesh(mesh)
        mesh.update()
        bm.free()
        return faces_updated, new_materials

    # --------- Helpers (materials/images) ---------
    def _has_color_attribute(self, obj, mesh, name):
        if _mesh_has_color_layer(mesh, name):
            return True
        if name == "RGBModelColor" and obj is not None:
            color = getattr(obj, "fin_col", None)
            if color is None and hasattr(obj, "keys") and "fin_col" in obj.keys():
                color = obj["fin_col"]
            if color and len(color) >= 3:
                return True
        return False

    def _material_base_name(self, obj):
        base = obj.data.name if obj.data else obj.name
        base = base.split('|', 1)[0]
        base = base.split('.', 1)[0]
        return base

    def _ensure_attribute_material(self, obj, attr_name, suffix):
        mesh = obj.data
        if mesh is None:
            return None, False

        has_color_layer = _mesh_has_color_layer(mesh, attr_name)

        base_name = self._material_base_name(obj)
        material_name = f"{base_name}_{suffix}"
        material = bpy.data.materials.get(material_name)
        created = False

        if not material:
            material = bpy.data.materials.new(name=material_name)
            created = True

        material.use_nodes = True
        nodes = material.node_tree.nodes
        links = material.node_tree.links
        nodes.clear()

        if attr_name == "RGBModelColor" and not has_color_layer:
            color = getattr(obj, "fin_col", None)
            if color is None and hasattr(obj, "keys") and "fin_col" in obj.keys():
                color = obj["fin_col"]
            if not color:
                color = (0.5, 0.5, 0.5)
            try:
                color = tuple(color)
            except TypeError:
                color = (color, color, color)
            if len(color) < 3:
                color = tuple(list(color)[:1] * 3)
            base_color = (color[0], color[1], color[2], 1.0)

            bsdf = nodes.new('ShaderNodeBsdfPrincipled')
            output = nodes.new('ShaderNodeOutputMaterial')
            bsdf.inputs['Base Color'].default_value = base_color
            bsdf.inputs['Alpha'].default_value = 1.0
            links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

            if hasattr(material, "blend_method"):
                material.blend_method = 'OPAQUE'
            if hasattr(material, "shadow_method"):
                material.shadow_method = 'OPAQUE'
        else:
            attr_node = nodes.new('ShaderNodeAttribute')
            attr_node.attribute_name = attr_name
            attr_node.attribute_type = 'GEOMETRY'

            bsdf = nodes.new('ShaderNodeBsdfPrincipled')
            output = nodes.new('ShaderNodeOutputMaterial')

            if suffix == "Alpha":
                # Opaque: do NOT use Alpha for transparency
                links.new(attr_node.outputs['Color'], bsdf.inputs['Base Color'])
                bsdf.inputs['Alpha'].default_value = 1.0
                if hasattr(material, "blend_method"):
                    material.blend_method = 'OPAQUE'
                if hasattr(material, "shadow_method"):
                    material.shadow_method = 'OPAQUE'
            else:
                links.new(attr_node.outputs['Color'], bsdf.inputs['Base Color'])
                bsdf.inputs['Alpha'].default_value = 1.0
                if hasattr(material, "blend_method"):
                    material.blend_method = 'OPAQUE'
                if hasattr(material, "shadow_method"):
                    material.shadow_method = 'OPAQUE'

            links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

        if mesh.materials.find(material.name) == -1:
            mesh.materials.append(material)

        return material, created

    def _get_or_create_ncp_material(self, mesh, ncp_value):
        mat_entry = next((item for item in MATERIALS if int(item[0]) == ncp_value), None)
        material_name = mat_entry[1] if mat_entry else f"NCP_{ncp_value}"

        material = bpy.data.materials.get(material_name)
        created = False
        if not material:
            material = bpy.data.materials.new(name=material_name)
            material.use_nodes = True
            bsdf = material.node_tree.nodes.get('Principled BSDF')
            if bsdf:
                if ncp_value == -1:
                    color = (1.0, 0.0, 0.0, 1.0)
                elif 0 <= ncp_value < len(COLORS):
                    color = (*COLORS[ncp_value], 1.0)
                else:
                    color = (1.0, 1.0, 1.0, 1.0)
                bsdf.inputs['Base Color'].default_value = color
            created = True

        if mesh.materials.find(material.name) == -1:
            mesh.materials.append(material)

        if created:
            # track unique created material name
            pass

        return material, created

    def _build_material_lookup(self):
        lookup = {}
        for mat in bpy.data.materials:
            for alias in self._material_aliases(mat.name):
                lookup.setdefault(alias, mat)
        return lookup

    def _build_image_lookup(self):
        lookup = {}
        for image in bpy.data.images:
            for alias in self._image_aliases(image):
                lookup.setdefault(alias, image)
        return lookup

    def _material_aliases(self, name):
        aliases = set()
        lower = name.lower()
        aliases.add(lower)
        if lower.endswith('.bmp'):
            aliases.add(lower[:-4])
        base, _ = os.path.splitext(lower)
        if base:
            aliases.add(base)
        return aliases

    def _image_aliases(self, image):
        aliases = set()
        lower = image.name.lower()
        aliases.add(lower)
        base, ext = os.path.splitext(lower)
        if base:
            aliases.add(base)
            if ext and ext != '.bmp':
                aliases.add(f"{base}.bmp")
        if lower.endswith('.bmp'):
            aliases.add(lower[:-4])
        if base.isdigit():
            stripped = base.lstrip('0') or '0'
            aliases.add(stripped)
            aliases.add(stripped.zfill(2))
        # Car-ish names to help discovery
        for k in ("car", "carbox", "shadow"):
            if k in base:
                aliases.add(k)
                aliases.add(f"{k}.bmp")
        return aliases

    def _candidate_names(self, tex_num, base_name):
        # In car mode, we want to match any car-ish image name regardless of tex num
        if self._is_car_mode:
            return {"car", "car.bmp", "car.png", "carbox", "carbox.bmp", "carbox.png", "shadow", "shadow.bmp", "shadow.png"}
        # Non-car mode: original numeric + base patterns
        names = set()
        numeric = str(tex_num)
        padded = numeric.zfill(2)
        def add_alias(v):
            if v:
                names.add(v.lower())
        add_alias(numeric); add_alias(f"{numeric}.bmp")
        add_alias(padded);  add_alias(f"{padded}.bmp")
        generic = int_to_texture(tex_num, "")
        add_alias(generic)
        if generic.lower().endswith(".bmp"):
            add_alias(generic[:-4])
        if base_name:
            letter_with_base = int_to_texture(tex_num, base_name)
            add_alias(letter_with_base)
            if letter_with_base.lower().endswith(".bmp"):
                add_alias(letter_with_base[:-4])
            add_alias(f"{base_name}{numeric}"); add_alias(f"{base_name}{numeric}.bmp")
            add_alias(f"{base_name}{padded}");  add_alias(f"{base_name}{padded}.bmp")
        return names

    def _ensure_material_for_texnum(self, tex_num, base_name, material_lookup, image_lookup):
        candidates = self._candidate_names(tex_num, base_name)
        # Existing material by alias
        for c in candidates:
            m = material_lookup.get(c)
            if m:
                return m

        # Build from image
        for c in candidates:
            img = image_lookup.get(c)
            if img:
                if self._is_car_mode:
                    can_name = self._canonical_car_name_for_image(img)  # car.bmp / carb.bmp / ...
                    img = self._rename_image_datablock(img, can_name)
                    # update image lookup so all aliases point to this image now
                    for a in candidates:
                        image_lookup[a] = img
                    mat = self._create_material_from_image(img, canonical_name=can_name)
                else:
                    mat = self._create_material_from_image(img, canonical_name=None)

                # Map all aliases to this material for reuse
                for alias in self._material_aliases(mat.name):
                    material_lookup[alias] = mat
                for alias in candidates:
                    material_lookup[alias] = mat
                return mat
        return None

    def _create_material_from_image(self, image, canonical_name=None):
        raw_name = image.name
        base, ext = os.path.splitext(raw_name)
        if canonical_name:
            mat_name = canonical_name
        elif self._is_car_mode:
            mat_name = f"{base}.bmp"
        else:
            mat_name = raw_name if ext.lower() == ".bmp" else base

        material = bpy.data.materials.get(mat_name)
        if not material:
            material = bpy.data.materials.new(name=mat_name)

        material.use_nodes = True
        nodes = material.node_tree.nodes
        links = material.node_tree.links
        nodes.clear()

        tex = nodes.new('ShaderNodeTexImage')
        tex.image = image
        tex.interpolation = 'Linear'

        bsdf = nodes.new('ShaderNodeBsdfPrincipled')
        bsdf.inputs['Alpha'].default_value = 1.0

        out = nodes.new('ShaderNodeOutputMaterial')
        links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
        links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])

        if hasattr(material, "blend_method"):
            material.blend_method = 'OPAQUE'
        if hasattr(material, "shadow_method"):
            material.shadow_method = 'OPAQUE'
        return material

    # --------- Misc ---------
    def _format_legacy_summary(self, summary):
        if not summary:
            return ""
        parts = []
        if summary.get("scene"):
            parts.append("scene")
        obj_count = summary.get("objects", 0)
        if obj_count:
            parts.append(f"{obj_count} object(s)")
        return ", ".join(parts)

    def _migrate_texture_animations(self, context):
        scene = context.scene
        if not hasattr(scene, "texture_animations"):
            return False
        existing = (scene.texture_animations or "").strip()
        if existing and existing not in {"[]", ""}:
            return False

        legacy = None
        if "ta_animations" in scene:
            legacy = scene["ta_animations"]
        elif "ta_animations" in bpy.data.texts:
            legacy = bpy.data.texts["ta_animations"].as_string()

        if not legacy:
            return False
        try:
            parsed = ast.literal_eval(legacy) if isinstance(legacy, str) else legacy
        except Exception:
            return False
        if not isinstance(parsed, list):
            return False

        scene.texture_animations = repr(parsed)
        scene.ta_max_slots = len(parsed)
        current_slot = scene.ta_current_slot if parsed else 0
        if parsed:
            current_slot = max(0, min(scene.ta_current_slot, len(parsed) - 1))
        scene.ta_current_slot = current_slot

        if parsed:
            first = parsed[current_slot if current_slot < len(parsed) else 0]
            if isinstance(first, dict):
                frame_count = first.get("frame_count")
                if frame_count is None and isinstance(first.get("frames"), list):
                    frame_count = len(first["frames"])
                frame_count = frame_count or 0
                scene.ta_max_frames = frame_count
            else:
                scene.ta_max_frames = 0
        else:
            scene.ta_max_frames = 0

        if "ta_animations" in scene:
            del scene["ta_animations"]
        return True

    def _migrate_instance_flag(self, obj):
        legacy_value = None
        try:
            legacy_revolt = getattr(obj, "revolt", None)
        except Exception:
            legacy_revolt = None
        if legacy_revolt and hasattr(legacy_revolt, "is_instance"):
            try:
                legacy_value = bool(legacy_revolt.is_instance)
            except Exception:
                legacy_value = bool(getattr(legacy_revolt, "is_instance", False))
        if legacy_value is None and "is_instance" in obj.keys():
            try:
                legacy_value = bool(obj["is_instance"])
            except Exception:
                legacy_value = None
        if legacy_value is None:
            return 0
        try:
            obj.is_instance = bool(legacy_value)
        except Exception:
            pass
        if "is_instance" in obj.keys():
            try:
                del obj["is_instance"]
            except Exception:
                pass
            ui_data = obj.get("_RNA_UI")
            if isinstance(ui_data, dict) and "is_instance" in ui_data:
                try:
                    del ui_data["is_instance"]
                except Exception:
                    pass
        return 1