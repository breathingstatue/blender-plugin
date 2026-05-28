"""
Name:    operators
Purpose: Provides operators for importing and exporting and other buttons.

Description:
These operators are used for importing and exporting files, as well as
providing the functions behind the UI buttons.
"""

import os
import bpy
import re
import time
import shutil
import bmesh
import heapq
import math
import mathutils
import string
from mathutils import Vector as BlenderVector
from mathutils.bvhtree import BVHTree
from bpy_extras.io_utils import ExportHelper
from bpy_extras.io_utils import ImportHelper
from . import common
from . import tools
from .hul_in import create_sphere
from .texanim import *
from .tools import generate_chull
from .rvstruct import *
from . import carinfo
from .common import MAX_MODEL_SLOTS, get_format, FORMAT_PRM, FORMAT_FIN, FORMAT_NCP, FORMAT_HUL, FORMAT_W, FORMAT_M, FORMAT_RIM
from .common import FORMAT_TAZ, FORMAT_TRI, FORMAT_UNK, MATERIALS, COLORS, FORMAT_FOB, FORMAT_FAN, FORMAT_PAN, FORMAT_LIT, FORMAT_VIS, FORMAT_FLD
from .common import get_model_materials, get_errors, msg_box, FORMATS, to_revolt_scale, FORMAT_CAR, TEX_PAGES_MAX, int_to_texture
from .common import to_revolt_coord, clean_model_base_name, set_level_texture_base_from_filepath, apply_fob_range_scale
from .common import get_scene_value, set_scene_value
from .common import generate_fob_name, create_directional_fob_mesh_ui
from .layers import set_face_env, create_or_assign_env_material
from .parameters_out_redux import append_aerial_info, append_axle_info, append_back_left_wheel, append_back_right_wheel
from .parameters_out_redux import append_front_left_wheel, append_front_right_wheel, append_pin_info, append_spring_info
from .parameters_out_redux import compare_and_adjust_axle_lengths, remove_imported_axles, compare_and_adjust_spring_lengths
from .parameters_out_redux import remove_imported_springs, compare_and_adjust_pin_lengths, remove_imported_pins
from .taz_in import create_zone
from .texanim import copy_frame_to_uv, copy_uv_to_frame
from .tools import AI_NODE_PROPERTY_ITEMS, trigger_type_items, fob_type_items, visibox_type_items, get_rig_objects, get_rig_root, rig_world_bbox_center
from .fob_subtypes import OBJECT_TYPE_NAMES
from .tri_in import create_trigger
from .fan_in import create_ai_node_object, ensure_collection, rebuild_ai_route_visuals, update_ai_node_handles
from .pan_in import create_pos_node_object, ensure_collection as ensure_pos_collection, rebuild_pos_route_visuals

from bpy.props import (
    BoolProperty,
    BoolVectorProperty,
    EnumProperty,
    FloatProperty,
    IntProperty,
    StringProperty,
    FloatVectorProperty,
    PointerProperty
)


AI_NODE_AUTOMATION_SPACING = 12.0 / 0.90


"""
BUTTONS ------------------------------------------------------------------------
"""

"""
IMPORT AND EXPORT -------------------------------------------------------------
"""

class ImportRV(bpy.types.Operator):
    bl_idname = "import_scene.revolt"
    bl_label = "Import Re-Volt Files"
    bl_description = "Import Re-Volt game files"
    filepath: bpy.props.StringProperty(subtype="FILE_PATH")

    def execute(self, context):
        scene = context.scene
        frmt = get_format(self.filepath)

        if frmt in {FORMAT_W, FORMAT_PRM, FORMAT_FIN, FORMAT_M}:
            set_level_texture_base_from_filepath(scene, self.filepath)

        start_time = time.time()
        context.window.cursor_set("WAIT")

        print("Importing {}".format(self.filepath))

        result = {'FINISHED'}

        try:
            if frmt == FORMAT_UNK:
                self.report({'ERROR'}, "Unsupported format.")
                result = {'CANCELLED'}

            elif frmt == FORMAT_CAR:
                from . import parameters_in
                parameters_in.import_file(self.filepath, context.scene)

            elif frmt == FORMAT_FIN:
                from . import fin_in
                fin_in.import_file(self.filepath, context.scene)

            elif frmt == FORMAT_FOB:
                from . import fob_in
                fob_in.import_file(self.filepath, scene)

            elif frmt == FORMAT_FLD:
                from . import fld_in
                fld_in.import_file(self.filepath, scene)

            elif frmt == FORMAT_HUL:
                from . import hul_in
                hul_in.import_file(self.filepath, scene)

            elif frmt == FORMAT_LIT:
                from . import lit_in
                lit_in.import_file(self.filepath, scene)

            elif frmt == FORMAT_NCP:
                from . import ncp_in
                ncp_in.import_file(self.filepath, scene)

            elif frmt == FORMAT_PRM:
                from . import prm_in
                prm_in.import_file(self.filepath, context.scene)

            elif frmt == FORMAT_RIM:
                from . import rim_in
                rim_in.import_file(self.filepath, scene)

            elif frmt == FORMAT_TAZ:
                from . import taz_in
                taz_in.import_file(self.filepath, scene)

            elif frmt == FORMAT_FAN:
                from . import fan_in
                fan_in.import_file(self.filepath, scene)

            elif frmt == FORMAT_PAN:
                from . import pan_in
                pan_in.import_file(self.filepath, scene)

            elif frmt == FORMAT_TRI:
                from . import tri_in
                tri_in.import_file(self.filepath, scene)

            elif frmt == FORMAT_VIS:
                from . import vis_in
                vis_in.import_file(self.filepath, scene)

            elif frmt == FORMAT_W:
                from . import w_in
                w_in.import_file(self.filepath, context.scene)

            elif frmt == FORMAT_M:
                from . import m_in

                context.scene.pending_import_filepath = self.filepath
                model_name = os.path.splitext(os.path.basename(self.filepath))[0].lower()
                context.scene.m_model_name_0 = model_name

                bpy.ops.import_scene.set_texture_source(
                    'INVOKE_DEFAULT',
                    slot_index=0,
                    model_name=model_name
                )

                result = {'FINISHED'}

            else:
                self.report({'ERROR'}, "Format not yet supported: {}".format(FORMATS.get(frmt, "Unknown Format")))
                result = {'CANCELLED'}

            if result != {'CANCELLED'}:
                for area in context.screen.areas:
                    if area.type in ['VIEW_3D', 'PROPERTIES']:
                        area.tag_redraw()

                self.report({'INFO'}, "Import completed in {:.2f} seconds".format(time.time() - start_time))

        except Exception as e:
            self.report({'ERROR'}, "Failed to import: {}".format(str(e)))
            result = {'CANCELLED'}
        finally:
            context.window.cursor_set("DEFAULT")

        return result

    def draw(self, context):
        layout = self.layout
        space = context.space_data

        # Gets the format from the file path
        frmt = get_format(space.params.filename)

        if frmt == -1 and not space.params.filename == "":
            layout.label(text="Format not supported", icon="ERROR")
        elif frmt != -1:
            layout.label(text="Import {}:".format(FORMATS[frmt]))

    def invoke(self, context, event):
        print("[DEBUG] ImportRV.invoke() triggered")
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

class ExportRV(bpy.types.Operator):
    bl_idname = "export_scene.revolt"
    bl_label = "Export Re-Volt Files"
    bl_description = "Export Re-Volt game files"
    filepath: bpy.props.StringProperty(subtype="FILE_PATH")
    filename_ext = ""

    format_type: bpy.props.EnumProperty(
        name="Format",
        description="Choose the file format to export",
        items=[
            ('NONE', "Select filetype…", "Pick a Re-Volt file type"),
            ('FIN',  "FIN (.fin)", "Instance file"),
            ('FOB',  "FOB (.fob)", "FOB object file"),
            ('FLD',  "FLD (.fld)", "Force fields file"),
            ('HUL',  "HUL (.hul)", "Hull file"),
            ('LIT',  "LIT (.lit)", "Lights file"),
            ('NCP',  "NCP (.ncp)", "Collision file"),
            ('PRM',  "PRM (.prm)", "Mesh file"),
            ('RIM',  "RIM (.rim)", "Mirror file"),
            ('TAZ',  "TAZ (.taz)", "Track zone file"),
            ('FAN',  "FAN (.fan)", "AI Nodes file"),
            ('PAN',  "PAN (.pan)", "Position Nodes file"),
            ('TRI',  "TRI (.tri)", "Trigger file"),
            ('VIS',  "VIS (.vis)", "Visibox file"),
            ('W',    "W (.w)",     "World file"),
            ('M',    "M (.m)",     "Model file"),
        ],
        default='NONE',
        update=None
    )

    def execute(self, context):
        # Fallback for filepath if user somehow runs execute without fileselect
        if not self.filepath:
            self.filepath = context.scene.get("last_exported_filepath", "")

        # Maps extension -> format code
        ext_map = {
            ".fin": "FIN", ".fob": "FOB", ".fld": "FLD", ".hul": "HUL",
            ".lit": "LIT",
            ".ncp": "NCP", ".prm": "PRM", ".rim": "RIM", ".taz": "TAZ",
            ".fan": "FAN", ".pan": "PAN", ".tri": "TRI", ".vis": "VIS",
            ".w": "W", ".m": "M"
        }
        format_to_ext = {v: k for k, v in ext_map.items()}

        base, ext = os.path.splitext(self.filepath)
        ext = ext.lower()

        # --- Determine actual format ---
        if ext in ext_map:
            # If user typed an explicit extension, infer format_type from it
            self.format_type = ext_map[ext]
        elif self.format_type != 'NONE':
            # If no extension but dropdown selected, append it
            add_ext = format_to_ext.get(self.format_type)
            if add_ext:
                self.filepath = base + add_ext
                ext = add_ext
        else:
            # Neither dropdown selection nor extension typed → invalid
            self.report({'ERROR'}, "Please select a file type or include the extension in the filename.")
            return {'CANCELLED'}

        print(f"Exporting to filepath: {self.filepath}, format: {self.format_type}")

        # Save for reuse
        context.scene["last_exported_filepath"] = self.filepath
        context.scene["last_exported_format"] = self.format_type

        result = exec_export(self.filepath, self.format_type, context)
        return result

    def invoke(self, context, event):
        # Restore last used format if available
        last_fmt = context.scene.get("last_exported_format")
        valid_formats = {
            "FIN", "FOB", "FLD", "HUL", "NCP", "PRM", "RIM",
            "TAZ", "FAN", "PAN", "TRI", "VIS", "W", "M"
        }
        if last_fmt in valid_formats:
            self.format_type = last_fmt
        else:
            self.format_type = 'NONE'

        # Restore last path suggestion
        last_path = context.scene.get("last_exported_filepath")
        if last_path:
            self.filepath = last_path

        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

class ExportExtension(bpy.types.Operator):
    bl_idname = "wm.select_default_texture"
    bl_label = "Select Default Texture and Level Base"
    bl_description = "Select the default car texture and level base texture name before exporting"

    texture_name: bpy.props.EnumProperty(
        name="Car Texture",
        description="Select the default car texture",
        items=lambda self, context: [
            (img.name, img.name, "") for img in bpy.data.images
            if img.name not in ["Render Result", "Viewer Node"]
        ],
    )

    level_texture_base: bpy.props.StringProperty(
        name="Level Texture Base",
        description="Prefix for level textures (e.g. 'box', 'arena')",
        default=""
    )

    use_car_texture: bpy.props.BoolProperty(
        name="Use 'car' as Level Base",
        description="Use 'car' as the level texture base instead of custom",
        default=False
    )

    def invoke(self, context, event):
        # Determine if a prompt is necessary (e.g., no 'car.bmp' present)
        if len(context.selected_objects) == 1:
            obj = context.selected_objects[0]
            car_part_prefixes = ["body", "wheel", "axle", "spring", "pin", "spinner"]
            if any(obj.name.startswith(prefix) for prefix in car_part_prefixes):
                car_texture = bpy.data.images.get('car')
                car_bmp_texture = bpy.data.images.get('car.bmp')
                if not car_texture and not car_bmp_texture:
                    return context.window_manager.invoke_props_dialog(self)

        # Otherwise skip prompt and export immediately
        return bpy.ops.export_scene.revolt('INVOKE_DEFAULT')

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "texture_name")
        layout.separator()
        layout.prop(self, "level_texture_base")
        layout.prop(self, "use_car_texture")

    def execute(self, context):
        scene = context.scene
        scene.default_texture_name = self.texture_name

        if self.use_car_texture:
            set_scene_value(scene, "level_texture_base", "car")
            self.report({'INFO'}, "Using 'car' as level texture base.")
        elif self.level_texture_base.strip():
            set_scene_value(scene, "level_texture_base", self.level_texture_base.strip().lower())
            self.report({'INFO'}, f"Set level texture base to '{self.level_texture_base.strip()}'")

        return bpy.ops.export_scene.revolt('INVOKE_DEFAULT')

def check_missing_textures(export_folder):
    missing = []
    for img in bpy.data.images:
        if not img.filepath:
            continue
        # Ignore generated images like 'Render Result'
        if img.name in {"Render Result", "Viewer Node"}:
            continue
        expected_path = os.path.join(export_folder, img.name)

        # Skip if the image has an absolute path and exists
        if os.path.isabs(bpy.path.abspath(img.filepath)) and os.path.exists(bpy.path.abspath(img.filepath)):
            continue

        # Otherwise, check in export folder
        if not os.path.exists(expected_path):
            print(f"[WARN] Texture expected at {expected_path} but doesn't exist.")
            missing.append(img.name)
    return missing

def exec_export(filepath, format_type, context):
    import shutil
    import time

    start_time = time.time()
    bpy.context.window.cursor_set("WAIT")

    format_map = {
        'FIN': '.fin',
        'FOB': '.fob',
        'FLD': '.fld',
        'HUL': '.hul',
        'LIT': '.lit',
        'NCP': '.ncp',
        'PRM': '.prm',
        'RIM': '.rim',
        'TAZ': '.taz',
        'FAN': '.fan',
        'PAN': '.pan',
        'TRI': '.tri',
        'VIS': '.vis',
        'W': '.w',
        'M': '.m'
    }

    _, file_ext = os.path.splitext(filepath)
    file_ext = file_ext.lower()

    if file_ext in format_map.values():
        frmt = next((k for k, v in format_map.items() if v == file_ext), None)
    else:
        frmt = format_type

    if not frmt:
        print({'ERROR'}, "Unsupported format.")
        return {'CANCELLED'}

    print(f"Determined export format: {frmt}")

    try:
        if frmt == 'FIN':
            from . import fin_out
            fin_out.export_file(filepath, context.scene)

        elif frmt == 'FOB':
            from . import fob_out
            fob_out.export_file(filepath, context.scene)

        elif frmt == 'FLD':
            from . import fld_out
            fld_out.export_file(filepath, context.scene)

        elif frmt == 'HUL':
            from . import hul_out
            hul_out.export_file(filepath, context.scene)

        elif frmt == 'LIT':
            from . import lit_out
            lit_out.export_file(filepath, context.scene)

        elif frmt == 'NCP':
            from . import ncp_out
            ncp_out.export_file(filepath, context.scene)

        elif frmt == 'PRM':
            from . import prm_out
            prm_out.export_file(filepath, context.scene)

        elif frmt == 'RIM':
            from . import rim_out
            rim_out.export_file(filepath, context.scene)

        elif frmt == 'TAZ':
            from . import taz_out
            taz_out.export_file(filepath, context.scene)

        elif frmt == 'FAN':
            from . import fan_out
            fan_out.export_file(filepath, context.scene)

        elif frmt == 'PAN':
            from . import pan_out
            pan_out.export_file(filepath, context.scene)

        elif frmt == 'TRI':
            from . import tri_out
            tri_out.export_file(filepath, context.scene)

        elif frmt == 'VIS':
            from . import vis_out
            vis_out.export_file(filepath, context.scene)

        elif frmt == 'W':
            from . import w_out
            w_out.export_file(filepath, context.scene)

        elif frmt == 'M':
            from . import m_out
            scene = context.scene

            model_name = os.path.splitext(os.path.basename(filepath))[0].lower()

            # --- 1) If we already have a slot for this model, skip the prompt entirely ---
            from .common import get_scene_value  # if not already imported at top

            existing_slot = -1
            for i in range(MAX_MODEL_SLOTS):
                slot_name = get_scene_value(scene, f"m_model_name_{i}", "").lower()
                if slot_name == model_name:
                    existing_slot = i
                    break

            if existing_slot != -1:
                print(f"[M EXPORT] Using existing texture config for '{model_name}' (slot {existing_slot}), no prompt.")
                m_out.export_file(filepath, scene)
                return {'FINISHED'}

            # --- 2) Second-chance path: skip prompt if flag is set (dialog already ran) ---
            if scene.get("skip_texture_prompt_once", False):
                print("[M EXPORT] skip_texture_prompt_once=True → exporting directly without prompting")
                del scene["skip_texture_prompt_once"]
                m_out.export_file(filepath, scene)
                return {'FINISHED'}

            # --- 3) Otherwise: first time for this model → optional light check + prompt ---
            print("Checking textures before exporting .m file...")
            export_folder = os.path.dirname(filepath)
            missing = check_missing_textures(export_folder)

            if missing:
                print(f"[WARNING] {len(missing)} texture(s) not found in export folder, but continuing anyway.")
                print("[INFO] RVGL will find textures from its own folders")

            scene.last_exported_filepath = filepath
            scene["skip_texture_prompt_once"] = True
            bpy.ops.wm.prompt_texture_prefix_model('INVOKE_DEFAULT', model_name=model_name)
            return {'CANCELLED'}

    finally:
        bpy.context.preferences.edit.use_global_undo = True
        bpy.context.window.cursor_set("DEFAULT")
        end_time = time.time() - start_time
        print(f"Export to {filepath} done in {end_time:.3f} seconds.")

    return {'FINISHED'}
    
class MFileExtension(bpy.types.Operator):
    bl_idname = "import_scene.set_texture_source"
    bl_label = "Set Texture Source"
    bl_description = "Choose how to load textures for .m file import"

    slot_index: bpy.props.IntProperty(name="Slot Index", default=-1)
    model_name: bpy.props.StringProperty(name="Model Name", default="")

    choice: bpy.props.EnumProperty(
        name="Source",
        description="Choose how to load textures",
        items=[
            ('LEVEL_TEXTURES', "Level Textures", "Select a folder with texturea.bmp, textureb.bmp..."),
            ('TEXTURE_NAME', "Texture File", "Select a single texture file like fxpage1.bmp"),
            ('VERTEX_COLOR', "Vertex Colours", "Skip texture loading entirely"),
        ],
        default='LEVEL_TEXTURES'
    )

    texture_folder: bpy.props.StringProperty(
        name="Folder",
        subtype='DIR_PATH'
    )

    texture_file: bpy.props.StringProperty(
        name="File",
        subtype='FILE_PATH'
    )

    def draw(self, context):
        layout = self.layout

        # Inline fxpage1 warning logic
        fxpage1_models = {
            "aerial", "aerialt", "beachball", "bottle",
            "firework", "generator", "speedup"
        }
        if self.model_name and self.model_name.lower() in fxpage1_models:
            box = layout.box()
            box.label(text=f"'{self.model_name}' usually uses fxpage1.bmp", icon='INFO')

        layout.prop(self, "choice")

        if self.choice == 'LEVEL_TEXTURES':
            layout.prop(self, "texture_folder")
        elif self.choice == 'TEXTURE_NAME':
            layout.prop(self, "texture_file")
        elif self.choice == 'VERTEX_COLOR':
            layout.label(text="No texture will be loaded; vertex colours will be used.")

    def execute(self, context):
        scene = context.scene

        if not (0 <= self.slot_index < MAX_MODEL_SLOTS):
            self.report({'ERROR'}, "Invalid model slot index.")
            return {'CANCELLED'}

        # Save selected model name
        set_scene_value(scene, f"m_model_name_{self.slot_index}", self.model_name)

        # Store selected choice and path
        set_scene_value(scene, f"m_texture_mode_{self.slot_index}", self.choice)
        if self.choice == 'LEVEL_TEXTURES':
            if not os.path.isdir(self.texture_folder):
                self.report({'ERROR'}, "Invalid folder path")
                return {'CANCELLED'}
            set_scene_value(scene, f"m_texture_path_{self.slot_index}", self.texture_folder)

        elif self.choice == 'TEXTURE_NAME':
            if not self.texture_file.lower().endswith('.bmp') or not os.path.isfile(self.texture_file):
                self.report({'ERROR'}, "Please select a valid .bmp file")
                return {'CANCELLED'}
            set_scene_value(scene, f"m_texture_path_{self.slot_index}", self.texture_file)

        else:  # VERTEX_COLOR
            set_scene_value(scene, f"m_texture_path_{self.slot_index}", "")  # Clear path

        print(
            f"[SLOT {self.slot_index}] {self.model_name} → {self.choice}, Path: "
            f"{get_scene_value(scene, f'm_texture_path_{self.slot_index}', '')}"
        )

        # If this was a .m or .fin import that was cancelled earlier
        filepath = getattr(scene, "pending_import_filepath", "")
        if filepath:
            # Clear pending filepath (StringProperty lives on Scene, not ID props)
            scene.pending_import_filepath = ""
            if filepath.lower().endswith(".m"):
                from . import m_in
                m_in.import_file(filepath, scene, model_name=self.model_name)
            elif filepath.lower().endswith(".fin"):
                from . import fin_in
                fin_in.import_file(filepath, scene)

        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=500)

class TexturePrefixPrompt(bpy.types.Operator):
    bl_idname = "wm.prompt_texture_prefix_model"
    bl_label = "Texture Prefix Selection"
    bl_description = "Choose texture mode for a specific .m model"

    model_name: bpy.props.StringProperty()

    choice: bpy.props.EnumProperty(
        name="Source",
        items=[
            ('LEVEL_TEXTURES', "Level Texture", "Use prefix like 'market', textures must be suffixed like 'tracka.bmp'"),
            ('TEXTURE_NAME', "Texture Filename", "Use exact texture filename, no suffixing"),
            ('VERTEX_COLOR', "Vertex Colours", "Ignore textures entirely"),
        ],
        default='LEVEL_TEXTURES'
    )

    texture_path_input: bpy.props.StringProperty(
        name="Folder/File",
        description="Folder/File",
        subtype='FILE_PATH',
        default=""
    )

    def draw(self, context):
        layout = self.layout
        layout.label(text=f"Texture settings for model: {self.model_name}")
        layout.prop(self, "choice", expand=True)
        if self.choice == 'LEVEL_TEXTURES':
            layout.prop(self, "texture_path_input", text="Folder With Track Textures")
        elif self.choice == 'TEXTURE_NAME':
            layout.prop(self, "texture_path_input", text="Texture File (.bmp)")

    def execute(self, context):
        scene = context.scene

        from .common import get_scene_value, set_scene_value

        # --- Reuse existing slot if present ---
        target_slot = -1
        for i in range(MAX_MODEL_SLOTS):
            slot_name = get_scene_value(scene, f"m_model_name_{i}", "").lower()
            if slot_name == self.model_name.lower():
                target_slot = i
                break

        # --- Otherwise pick first free slot ---
        if target_slot == -1:
            for i in range(MAX_MODEL_SLOTS):
                slot_name = get_scene_value(scene, f"m_model_name_{i}", "")
                if not slot_name:
                    target_slot = i
                    break

        if target_slot == -1:
            self.report({'ERROR'}, "No free model slots available.")
            return {'CANCELLED'}

        # --- Save selection ---
        set_scene_value(scene, f"m_model_name_{target_slot}", self.model_name)
        set_scene_value(scene, f"m_texture_mode_{target_slot}", self.choice)
        set_scene_value(scene, f"m_texture_path_{target_slot}", self.texture_path_input)

        # --- Single export path (no queue) ---
        if not hasattr(scene, "m_models_prompt_queue"):
            context.scene["skip_texture_prompt_once"] = True
            bpy.ops.export_scene.revolt('EXEC_DEFAULT')
            return {'FINISHED'}

        # --- Queue continues ---
        scene.m_models_prompt_index += 1
        if scene.m_models_prompt_index < len(scene.m_models_prompt_queue):
            next_model = scene.m_models_prompt_queue[scene.m_models_prompt_index]
            bpy.ops.wm.prompt_texture_prefix_model('INVOKE_DEFAULT', model_name=next_model)
        else:
            del scene.m_models_prompt_queue
            del scene.m_models_prompt_index
            context.scene["skip_texture_prompt_once"] = True
            bpy.ops.export_scene.revolt('EXEC_DEFAULT')

        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

class RVIO_OT_ReadCarParameters(bpy.types.Operator):
    bl_idname = "rvio.read_car_parameters"
    bl_label = "Read Car Parameters"
    bl_description = "Read car parameters from a parameters.txt file"

    # Filepath handler
    filepath: bpy.props.StringProperty(subtype="FILE_PATH")
    directory: bpy.props.StringProperty(subtype="DIR_PATH")
    filter_glob: bpy.props.StringProperty(default="*.txt", options={'HIDDEN'})

    def execute(self, context):
        if not self.filepath.lower().endswith("parameters.txt"):
            self.report({'ERROR'}, "Please select a valid parameters.txt file")
            return {'CANCELLED'}

        parameters = carinfo.read_parameters(self.filepath)
        parameters_str = self.format_parameters(parameters)

        text_block_name = os.path.basename(self.filepath)
        text_block = bpy.data.texts.new(name=text_block_name)
        text_block.write(parameters_str)

        self.report({'INFO'}, f"Car parameters from '{self.filepath}' imported to Text Editor")
        return {'FINISHED'}

    def format_parameters(self, parameters):
        def format_inertia(vals, indent="    "):
            # Expect 9 values; print as 3 rows of 3 with semicolons
            if not isinstance(vals, (list, tuple)) or len(vals) != 9:
                return f"{indent}{vals}\n"
            out = ""
            for i in range(0, 9, 3):
                row = vals[i:i+3]
                line = "; ".join(f"{v:g}" for v in row) + ";"
                out += f"{indent}{line}\n"
            return out

        formatted_str = ""
        for key, value in parameters.items():
            if key == 'model':
                formatted_str += f"{key}:\n"
                for model_key, model_value in value.items():
                    formatted_str += f"  {model_key}: {model_value}\n"

            elif key in ['wheel', 'spring', 'pin', 'axle', 'spinner', 'aerial', 'body', 'ai']:
                formatted_str += f"{key}:\n"
                if isinstance(value, dict):
                    for sub_key, sub_value in value.items():
                        # Special-case inertia (3x3) formatting
                        if sub_key == 'inertia' and isinstance(sub_value, (list, tuple)) and len(sub_value) == 9:
                            formatted_str += f"  {sub_key}:\n"
                            formatted_str += format_inertia(sub_value, indent="    ")
                        elif isinstance(sub_value, dict):
                            formatted_str += f"  {sub_key}:\n"
                            for sub_sub_key, sub_sub_value in sub_value.items():
                                if sub_sub_key == 'inertia' and isinstance(sub_sub_value, (list, tuple)) and len(sub_sub_value) == 9:
                                    formatted_str += f"    {sub_sub_key}:\n"
                                    formatted_str += format_inertia(sub_sub_value, indent="      ")
                                else:
                                    formatted_str += f"    {sub_sub_key}: {sub_sub_value}\n"
                        else:
                            # Single line for simple entries (covers AI values nicely)
                            formatted_str += f"  {sub_key}: {sub_value}\n"

                elif isinstance(value, list):
                    for item in value:
                        formatted_str += f"  - {item}\n"

            else:
                formatted_str += f"{key}: {value}\n"

        return formatted_str

    def invoke(self, context, event):
        # Prefer the .blend's directory if available; fall back to home directory
        try:
            blend_dir = os.path.dirname(bpy.data.filepath) if bpy.data.filepath else bpy.path.abspath("//")
        except Exception:
            blend_dir = ""

        if blend_dir and os.path.isdir(blend_dir):
            self.directory = blend_dir
        else:
            self.directory = os.path.expanduser("~")

        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

class ButtonReExport(bpy.types.Operator):
    bl_idname = "export_scene.revolt_redo"
    bl_label = "Re-Export"
    bl_description = "Redo the same export again"

    def execute(self, context):
        scene = context.scene
        filepath = context.scene.last_exported_filepath
        format_type = context.scene.last_exported_format
        if not filepath or not format_type:
            self.report({'WARNING'}, "No file path or format saved for re-export.")
            return {'CANCELLED'}
        return exec_export(filepath, format_type, context)

"""
HELPERS -----------------------------------------------------------------------
"""

class ButtonRenameAllObjects(bpy.types.Operator):
    bl_idname = "helpers.rename_selected_objects"
    bl_label = "Rename Selected Objects"
    bl_description = "Renames all selected objects using a new name"

    new_name: bpy.props.StringProperty(
        name="New Name",
        default="",
        description="Enter a new name for the selected objects (max 8 characters)"
    )

    @classmethod
    def poll(cls, context):
        return len(context.selected_objects) > 0

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def execute(self, context):
        selected_objects = bpy.context.selected_objects
        if len(selected_objects) == 0:
            self.report({'WARNING'}, "No objects selected")
            return {'CANCELLED'}

        if len(self.new_name) > 8:
            self.report({'ERROR'}, "Name too long. Max 62 characters.")
            return {'CANCELLED'}

        base_name = self.new_name[:61] if len(selected_objects) > 1 else self.new_name

        for index, obj in enumerate(selected_objects):
            suffix = str(index + 1) if len(selected_objects) > 1 else ""
            obj.name = base_name + suffix

        return {'FINISHED'}
    
class SelectByName(bpy.types.Operator):
    bl_idname = "helpers.select_by_name"
    bl_label = "Select by name"
    bl_description = "Selects all objects that contain the name"

    name_filter: bpy.props.StringProperty(
        name="Name Filter",
        default="",
        description="Enter a part of the name to filter objects"
    )

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def execute(self, context):
        name_filter = self.name_filter
        selected_count = 0

        for obj in bpy.data.objects:
            if name_filter in obj.name:
                obj.select_set(True)
                selected_count += 1
            else:
                obj.select_set(False)

        self.report({'INFO'}, "Selected {} objects".format(selected_count))
        return {'FINISHED'}

class SelectByData(bpy.types.Operator):
    bl_idname = "helpers.select_by_data"
    bl_label = "Select by data"
    bl_description = "Selects all objects with the same object data (mesh)"

    def execute(self, context):
        active_obj = context.active_object

        # Check if there is an active object and it has mesh data
        if not active_obj or active_obj.type != 'MESH':
            self.report({'WARNING'}, "No active mesh object selected")
            return {'CANCELLED'}

        mesh_data = active_obj.data
        selected_count = 0

        for obj in bpy.data.objects:
            if obj.type == 'MESH' and obj.data == mesh_data:
                obj.select_set(True)
                selected_count += 1
            else:
                obj.select_set(False)

        # Optionally, you might want to reselect the initially active object
        active_obj.select_set(True)

        self.report({'INFO'}, "Selected {} objects".format(selected_count))
        return {'FINISHED'}

class TexturesSave(bpy.types.Operator, ImportHelper):
    bl_idname = "helpers.textures_save"
    bl_label = "Save Textures to Disk"
    bl_description = "Saves all used track texture files to selected directory"
    bl_options = {'REGISTER', 'UNDO'}

    filename_ext = ""  # We just use the directory

    filter_glob: bpy.props.StringProperty(
        default="*", options={'HIDDEN'}
    )

    texture_base: bpy.props.StringProperty(
        name="Level Texture Base",
        description="Base name for level textures (optional)",
        default=""
    )

    auto_fix: bpy.props.BoolProperty(
        name="Auto-Rename Materials",
        description="Automatically rename materials to match exported texture names (.bmp)",
        default=True
    )

    numbered_names: bpy.props.BoolProperty(
        name="Numbered Names",
        description="Export textures as 0.bmp, 1.bmp, ... and (optionally) rename materials to match",
        default=False
    )

    start_index: bpy.props.IntProperty(
        name="Start Index",
        description="Starting index for numbered texture names",
        default=0,
        min=0
    )

    def execute(self, context):
        selected_path = self.filepath
        directory = selected_path if os.path.isdir(selected_path) else os.path.dirname(selected_path)
        if not os.path.isdir(directory):
            self.report({'ERROR'}, "Invalid directory selected.")
            return {'CANCELLED'}

        renamed = 0
        saved = 0

        base_prefix = self.texture_base.strip()[:8]
        base_prefix_lower = base_prefix.lower()

        # Collect used images
        used_images = [
            image for image in bpy.data.images
            if image.source == 'FILE' and image.users > 0
        ]
        if not used_images:
            self.report({'INFO'}, "No image textures to export.")
            return {'CANCELLED'}

        used_images.sort(key=lambda img: img.name.lower())

        # Build target filename mapping for each image
        filenames_by_image = {}
        used_names = set()

        for i, image in enumerate(used_images, start=self.start_index):
            if self.numbered_names:
                # Strictly numbered naming
                filename = f"{i}.bmp"
            else:
                # Original naming logic with optional base prefix
                image_base = os.path.splitext(image.name)[0]
                image_base_lower = image_base.lower()

                if base_prefix:
                    suffix = ""
                    if image_base_lower.startswith(base_prefix_lower):
                        suffix = image_base_lower[len(base_prefix_lower):]
                    else:
                        match = re.search(r'([a-z]{1,2})$', image_base_lower)
                        suffix = match.group(1) if match else ""

                    if suffix:
                        filename = f"{base_prefix}{suffix}.bmp"
                    else:
                        filename = int_to_texture(i - self.start_index, name=base_prefix)
                else:
                    filename = f"{image_base[:8]}.bmp"

                # Ensure uniqueness (only for non-numbered mode)
                filename_lower = filename.lower()
                if filename_lower in used_names:
                    counter = i - self.start_index
                    name_prefix = base_prefix or image_base[:6]
                    filename = int_to_texture(counter, name=name_prefix)
                    filename_lower = filename.lower()
                    while filename_lower in used_names:
                        counter += 1
                        filename = int_to_texture(counter, name=name_prefix)
                        filename_lower = filename.lower()

                used_names.add(filename_lower)

            filenames_by_image[image] = filename

        # Auto-rename materials to match the final filenames
        # This replaces the previous pre-rename logic so that numbering works correctly.
        if self.auto_fix:
            for mat in bpy.data.materials:
                if not mat.use_nodes:
                    continue

                target_name = None
                for node in mat.node_tree.nodes:
                    if node.type == 'TEX_IMAGE' and node.image and node.image in filenames_by_image:
                        target_name = filenames_by_image[node.image]
                        break

                if target_name is None:
                    continue

                if mat.name != target_name:
                    try:
                        print(f"[INFO] Renaming material '{mat.name}' → '{target_name}'")
                        mat.name = target_name
                        renamed += 1
                    except Exception as e:
                        self.report({'WARNING'}, f"Failed to rename material '{mat.name}': {e}")
        else:
            # If auto-fix is disabled, ensure materials already match the intended names
            for mat in bpy.data.materials:
                if not mat.use_nodes:
                    continue
                for node in mat.node_tree.nodes:
                    if node.type == 'TEX_IMAGE' and node.image and node.image in filenames_by_image:
                        expected = filenames_by_image[node.image]
                        if mat.name != expected:
                            self.report({'WARNING'}, f"Material '{mat.name}' does not match '{expected}'. Enable Auto-Rename to fix.")
                            return {'CANCELLED'}
                        break

        if renamed:
            self.report({'INFO'}, f"Renamed {renamed} materials to match texture names.")

        # Save each image as .bmp using the finalized mapping
        for image in used_images:
            filename = filenames_by_image[image]
            dst_path = os.path.join(directory, filename)

            try:
                orig_path = image.filepath_raw
                orig_format = image.file_format

                image.filepath_raw = dst_path
                image.file_format = 'BMP'
                image.save_render(dst_path)

                image.filepath_raw = orig_path
                image.file_format = orig_format
                image.reload()

                saved += 1
            except Exception as e:
                self.report({'ERROR'}, f"Failed to save '{image.name}': {e}")
                continue

        self.report({'INFO'}, f"Saved {saved} textures to: {directory}")
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

class TexturesRename(bpy.types.Operator):
    bl_idname = "helpers.textures_rename"
    bl_label = "Rename Textures"
    bl_description = "Rename texture images and their materials sequentially (a, b, c, …) using the current image list order; ignores Texture Number"
    bl_options = {'REGISTER', 'UNDO'}

    base_name: bpy.props.StringProperty(
        name="Base Name",
        description="Base name for textures and materials (e.g. 'track')",
        maxlen=64
    )

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def index_to_suffix(self, index: int) -> str:
        # 0->a, 25->z, 26->aa, 27->ab, ...
        index += 1
        s = ""
        while index > 0:
            index, r = divmod(index - 1, 26)
            s = chr(ord('a') + r) + s
        return s

    def valid_image(self, img: bpy.types.Image) -> bool:
        if not img:
            return False
        if img.name in {"Viewer Node", "Render Result"}:
            return False
        if img.source != 'FILE':
            return False
        if img.users <= 0:
            return False
        return True

    def images_in_scope(self, context):
        # Prefer images actually used by selected objects (in datablock order).
        used = set()
        for obj in context.selected_objects:
            if obj.type != 'MESH':
                continue
            for mat in obj.data.materials:
                if not (mat and mat.use_nodes):
                    continue
                for node in mat.node_tree.nodes:
                    if node.type == 'TEX_IMAGE' and node.image and self.valid_image(node.image):
                        used.add(node.image)

        if used:
            # Keep the current datablock order
            ordered = [img for img in bpy.data.images if img in used and self.valid_image(img)]
            return ordered

        # Fallback: all valid images in datablock order
        return [img for img in bpy.data.images if self.valid_image(img)]

    def execute(self, context):
        if not self.base_name:
            self.report({'WARNING'}, "No base name provided")
            return {'CANCELLED'}

        images = self.images_in_scope(context)
        if not images:
            self.report({'WARNING'}, "No images to rename")
            return {'CANCELLED'}

        used_image_names = set(img.name for img in bpy.data.images)
        used_material_names = set(mat.name for mat in bpy.data.materials)

        def unique_image_name(target):
            # Reserve a unique name for images
            if target not in used_image_names:
                used_image_names.add(target)
                return target
            i = 1
            while True:
                cand = f"{target}.{i:03d}"
                if cand not in used_image_names:
                    used_image_names.add(cand)
                    return cand
                i += 1

        def unique_material_name(target):
            # Reserve a unique name for materials
            if target not in used_material_names:
                used_material_names.add(target)
                return target
            i = 1
            while True:
                cand = f"{target}.{i:03d}"
                if cand not in used_material_names:
                    used_material_names.add(cand)
                    return cand
                i += 1

        for idx, image in enumerate(images):
            suffix = self.index_to_suffix(idx)
            new_image_name = f"{self.base_name}{suffix}"       # image datablock name (no .bmp)
            new_mat_name = f"{new_image_name}.bmp"             # material name includes .bmp

            if image.name != new_image_name:
                used_image_names.discard(image.name)
                final_img_name = unique_image_name(new_image_name)
                print(f"[ORDER] {image.name} → {final_img_name}")
                image.name = final_img_name
            else:
                final_img_name = image.name
                used_image_names.add(final_img_name)

            # Rename every material that uses this image
            for mat in bpy.data.materials:
                if not (mat and mat.use_nodes):
                    continue
                uses_this_image = any(
                    node.type == 'TEX_IMAGE' and node.image == image
                    for node in mat.node_tree.nodes
                )
                if not uses_this_image:
                    continue

                if mat.name != new_mat_name:
                    used_material_names.discard(mat.name)
                    final_mat_name = unique_material_name(new_mat_name)
                    print(f"[ORDER] Material {mat.name} → {final_mat_name}")
                    mat.name = final_mat_name
                else:
                    used_material_names.add(mat.name)

        self.report({'INFO'}, f"Renamed {len(images)} images/materials using base '{self.base_name}' by list order")
        return {'FINISHED'}
    
class CopyWheelParams(bpy.types.Operator):
    bl_idname = "headers.copy_wheel_params"
    bl_label = "Copy Wheel Parameters"
    bl_description = ("Copies wheel parameters to the clipboard. Wheels must be children of 'body' "
                      "and named starting with 'wheel'.")

    def execute(self, context):
        body = bpy.data.objects.get("body")
        if not body:
            msg_box("Car body object named 'body' not found.", "ERROR")
            return {'CANCELLED'}

        # Check if any children of body start with "wheel"
        wheel_children = [child for child in body.children if child.name.lower().startswith("wheel")]
        if not wheel_children:
            msg_box("No wheel objects found as children of 'body'.\nWheels must be child objects of body.", "WARNING")
            return {'CANCELLED'}

        processed = set()
        params = ""
        params = append_front_left_wheel(params, body, processed)
        params = append_front_right_wheel(params, body, processed)
        params = append_back_left_wheel(params, body, processed)
        params = append_back_right_wheel(params, body, processed)

        bpy.context.window_manager.clipboard = params
        self.report({'INFO'}, "Wheel parameters copied to clipboard.")
        return {"FINISHED"}

class AxleMessageBox(bpy.types.Operator):
    bl_idname = "headers.axle_message_box"
    bl_label = "Load the original axle for comparison"
    bl_description = ("Imports the original axle, compares it to your current axle under 'body', "
                      "copies axle parameters to the clipboard, and removes the imported axle. "
                      "Requires a child named starting with 'axle' under 'body'.")
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        body = bpy.data.objects.get("body")
        if not body:
            msg_box("Car body object named 'body' not found.", "ERROR")
            return {'CANCELLED'}

        # Check for child named "axle" under body
        axle_child = next((child for child in body.children if child.name.lower().startswith("axle")), None)
        if not axle_child:
            msg_box("Axle must be a child object of body.", "WARNING")
            return {'CANCELLED'}

        bpy.ops.headers.confirm_load_original_axle('INVOKE_DEFAULT')
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

class ConfirmLoadOriginalAxle(bpy.types.Operator):
    bl_idname = "headers.confirm_load_original_axle"
    bl_label = "Load the original axle for comparison"
    bl_options = {'REGISTER', 'INTERNAL'}

    MAX_TIMER_CHECKS = 300

    def __init__(self):
        self._timer = None
        self._check_count = 0

    def _cleanup_timer(self, context):
        if self._timer:
            context.window_manager.event_timer_remove(self._timer)
            self._timer = None

    def execute(self, context):
        context.scene['existing_objects'] = list(bpy.data.objects.keys())
        bpy.ops.import_scene.revolt('INVOKE_DEFAULT')
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if event.type == 'TIMER':
            self._check_count += 1
            imported_objects = set(bpy.data.objects.keys()) - set(context.scene['existing_objects'])
            if imported_objects:
                imported_object = None
                for obj_name in imported_objects:
                    obj = bpy.data.objects.get(obj_name)
                    if obj:
                        imported_object = obj
                        break  # Assuming only one imported object

                # Store the single imported object in the scene
                context.scene['imported_object'] = imported_object

                compare_and_adjust_axle_lengths(imported_object)
                bpy.ops.headers.copy_and_remove_axles('INVOKE_DEFAULT')

                # Report a message to the user
                self.report({'INFO'}, "Axle parameters copied to clipboard.")

                self._cleanup_timer(context)
                return {'FINISHED'}

            if self._check_count >= self.MAX_TIMER_CHECKS:
                self.report({'WARNING'}, "No imported axle detected. Import may have been cancelled.")
                self._cleanup_timer(context)
                return {'CANCELLED'}

        return {'PASS_THROUGH'}

    def invoke(self, context, event):
        self._check_count = 0
        self._timer = context.window_manager.event_timer_add(0.1, window=context.window)
        return self.execute(context)

    def cancel(self, context):
        self._cleanup_timer(context)

class CopyAndRemoveAxles(bpy.types.Operator):
    bl_idname = "headers.copy_and_remove_axles"
    bl_label = "Copy Parameters and Remove Imported Axles"
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        # Retrieve the body object from the scene
        body = bpy.data.objects.get("body")
        if not body:
            self.report({'ERROR'}, "Body object not found in the scene.")
            return {'CANCELLED'}

        # Initialize parameters string and processed set
        params = ""
        processed = set()

        # Call append_axle_info to build the parameters string
        params = append_axle_info(params, body, processed)

        # Copy the parameters to the clipboard
        bpy.context.window_manager.clipboard = params

        # Report a message to the user
        self.report({'INFO'}, "Axle parameters copied to clipboard.")

        # Retrieve the imported object from the scene
        imported_object = context.scene.get('imported_object')
        if imported_object:
            # Remove the imported axle
            remove_imported_axles([imported_object])
            # Clear the stored object after use
            context.scene['imported_object'] = None

        return {'FINISHED'}

class SpringMessageBox(bpy.types.Operator):
    bl_idname = "headers.spring_message_box"
    bl_label = "Load the original spring for comparison"
    bl_description = ("Imports the original spring, compares it to your current spring under 'body', "
                      "copies spring parameters to the clipboard, and removes the imported spring. "
                      "Requires a child named starting with 'spring' under 'body'.")
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        body = bpy.data.objects.get("body")
        if not body:
            msg_box("Car body object named 'body' not found.", "ERROR")
            return {'CANCELLED'}

        # Check for spring as a child of body
        spring_child = next((child for child in body.children if child.name.lower().startswith("spring")), None)
        if not spring_child:
            msg_box("Spring must be a child object of body.", "WARNING")
            return {'CANCELLED'}

        bpy.ops.headers.confirm_load_original_spring('INVOKE_DEFAULT')
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

class ConfirmLoadOriginalSpring(bpy.types.Operator):
    bl_idname = "headers.confirm_load_original_spring"
    bl_label = "Load the original spring for comparison"
    bl_options = {'REGISTER', 'INTERNAL'}

    MAX_TIMER_CHECKS = 300

    def __init__(self):
        self._timer = None
        self._check_count = 0

    def _cleanup_timer(self, context):
        if self._timer:
            context.window_manager.event_timer_remove(self._timer)
            self._timer = None

    def execute(self, context):
        context.scene['existing_objects'] = list(bpy.data.objects.keys())
        bpy.ops.import_scene.revolt('INVOKE_DEFAULT')
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if event.type == 'TIMER':
            self._check_count += 1
            imported_objects = set(bpy.data.objects.keys()) - set(context.scene['existing_objects'])
            if imported_objects:
                imported_object = None
                for obj_name in imported_objects:
                    obj = bpy.data.objects.get(obj_name)
                    if obj:
                        imported_object = obj
                        break  # Assuming only one imported object

                # Store the single imported object in the scene
                context.scene['imported_object'] = imported_object

                compare_and_adjust_spring_lengths(imported_object)
                bpy.ops.headers.copy_and_remove_springs('INVOKE_DEFAULT')

                # Report a message to the user
                self.report({'INFO'}, "Spring parameters copied to clipboard.")

                self._cleanup_timer(context)
                return {'FINISHED'}

            if self._check_count >= self.MAX_TIMER_CHECKS:
                self.report({'WARNING'}, "No imported spring detected. Import may have been cancelled.")
                self._cleanup_timer(context)
                return {'CANCELLED'}

        return {'PASS_THROUGH'}

    def invoke(self, context, event):
        self._check_count = 0
        self._timer = context.window_manager.event_timer_add(0.1, window=context.window)
        return self.execute(context)

    def cancel(self, context):
        self._cleanup_timer(context)

class CopyAndRemoveSprings(bpy.types.Operator):
    bl_idname = "headers.copy_and_remove_springs"
    bl_label = "Copy Parameters and Remove Imported Springs"
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        # Retrieve the body object from the scene
        body = bpy.data.objects.get("body")
        if not body:
            self.report({'ERROR'}, "Body object not found in the scene.")
            return {'CANCELLED'}

        # Initialize parameters string and processed set
        params = ""
        processed = set()

        # Call append_spring_info to build the parameters string
        params = append_spring_info(params, body, processed)

        # Copy the parameters to the clipboard
        bpy.context.window_manager.clipboard = params

        # Report a message to the user
        self.report({'INFO'}, "Spring parameters copied to clipboard.")

        # Retrieve the imported object from the scene
        imported_object = context.scene.get('imported_object')
        if imported_object:
            # Remove the imported spring
            remove_imported_springs([imported_object])
            # Clear the stored object after use
            context.scene['imported_object'] = None

        return {'FINISHED'}

class PinMessageBox(bpy.types.Operator):
    bl_idname = "headers.pin_message_box"
    bl_label = "Load the original pin for comparison"
    bl_description = ("Imports the original pin, compares it to your current pin under 'body', "
                      "copies pin parameters to the clipboard, and removes the imported pin. "
                      "Requires a child named starting with 'pin' under 'body'.")
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        body = bpy.data.objects.get("body")
        if not body:
            msg_box("Car body object named 'body' not found.", "ERROR")
            return {'CANCELLED'}

        # Check for pin as a child of body
        pin_child = next((child for child in body.children if child.name.lower().startswith("pin")), None)
        if not pin_child:
            msg_box("Pin must be a child object of body.", "WARNING")
            return {'CANCELLED'}

        bpy.ops.headers.confirm_load_original_pin('INVOKE_DEFAULT')
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

class ConfirmLoadOriginalPin(bpy.types.Operator):
    bl_idname = "headers.confirm_load_original_pin"
    bl_label = "Load the original pin for comparison"
    bl_options = {'REGISTER', 'INTERNAL'}

    MAX_TIMER_CHECKS = 300

    def __init__(self):
        self._timer = None
        self._check_count = 0

    def _cleanup_timer(self, context):
        if self._timer:
            context.window_manager.event_timer_remove(self._timer)
            self._timer = None

    def execute(self, context):
        context.scene['existing_objects'] = list(bpy.data.objects.keys())
        bpy.ops.import_scene.revolt('INVOKE_DEFAULT')
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if event.type == 'TIMER':
            self._check_count += 1
            imported_objects = set(bpy.data.objects.keys()) - set(context.scene['existing_objects'])
            if imported_objects:
                imported_object = None
                for obj_name in imported_objects:
                    obj = bpy.data.objects.get(obj_name)
                    if obj:
                        imported_object = obj
                        break  # Assuming only one imported object

                # Store the single imported object in the scene
                context.scene['imported_object'] = imported_object

                compare_and_adjust_pin_lengths(imported_object)
                bpy.ops.headers.copy_and_remove_pins('INVOKE_DEFAULT')

                # Report a message to the user
                self.report({'INFO'}, "Pin parameters copied to clipboard.")

                self._cleanup_timer(context)
                return {'FINISHED'}

            if self._check_count >= self.MAX_TIMER_CHECKS:
                self.report({'WARNING'}, "No imported pin detected. Import may have been cancelled.")
                self._cleanup_timer(context)
                return {'CANCELLED'}

        return {'PASS_THROUGH'}

    def invoke(self, context, event):
        self._check_count = 0
        self._timer = context.window_manager.event_timer_add(0.1, window=context.window)
        return self.execute(context)

    def cancel(self, context):
        self._cleanup_timer(context)

class CopyAndRemovePins(bpy.types.Operator):
    bl_idname = "headers.copy_and_remove_pins"
    bl_label = "Copy Parameters and Remove Imported Pins"
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        # Retrieve the body object from the scene
        body = bpy.data.objects.get("body")
        if not body:
            self.report({'ERROR'}, "Body object not found in the scene.")
            return {'CANCELLED'}

        # Initialize parameters string and processed set
        params = ""
        processed = set()

        # Call append_pin_info to build the parameters string
        params = append_pin_info(params, body, processed)

        # Copy the parameters to the clipboard
        bpy.context.window_manager.clipboard = params

        # Report a message to the user
        self.report({'INFO'}, "Pin parameters copied to clipboard.")

        # Retrieve the imported object from the scene
        imported_object = context.scene.get('imported_object')
        if imported_object:
            # Remove the imported pin
            remove_imported_pins([imported_object])
            # Clear the stored object after use
            context.scene['imported_object'] = None

        return {'FINISHED'}

class CopyAerialParams(bpy.types.Operator):
    bl_idname = "headers.copy_aerial_params"
    bl_label = "Copy Aerial Parameters"
    bl_description = ("Copies aerial parameters to the clipboard. Requires a child named starting "
                      "with 'aerial' under 'body'.")

    def execute(self, context):
        body = bpy.data.objects.get("body")
        if not body:
            msg_box("Car body object named 'body' not found.", "ERROR")
            return {'CANCELLED'}

        # Check for aerial as a child of body
        aerial_child = next((child for child in body.children if child.name.lower().startswith("aerial")), None)
        if not aerial_child:
            msg_box("Aerial must be a child object of body.", "WARNING")
            return {'CANCELLED'}

        processed = set()
        params = ""
        params = append_aerial_info(params, body, processed)

        bpy.context.window_manager.clipboard = params
        self.report({'INFO'}, "Aerial parameters copied to clipboard.")
        return {'FINISHED'}
    
class AlignCarRevolt(bpy.types.Operator):
    bl_idname = "headers.align_car_to_revolt"
    bl_label = "Align Car to Re-Volt"
    bl_description = ("Rotates the car so the vector from the car’s center to the 3D Cursor points to +Y "
                      "(Re-Volt forward). Place the 3D Cursor at the front bumper center before running.")
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        if not obj:
            self.report({'ERROR'}, "Select the car (or any part of it) first.")
            return {'CANCELLED'}

        root = get_rig_root(obj)
        objs = get_rig_objects(root)

        center = rig_world_bbox_center(objs)
        if center is None:
            self.report({'ERROR'}, "Could not compute car bounding box center.")
            return {'CANCELLED'}

        cursor = context.scene.cursor.location.copy()
        fwd = (cursor - center)
        fwd.z = 0.0

        if fwd.length < 1e-6:
            self.report({'ERROR'}, "Cursor is too close to car center. Place it at the front bumper center.")
            return {'CANCELLED'}

        fwd.normalize()
        target_fwd = BlenderVector((0, 1, 0))

        # Rotate root so fwd -> +Y
        rot = fwd.rotation_difference(target_fwd)

        # Apply rotation in WORLD space by rotating matrix_world
        mw = root.matrix_world.copy()
        R = rot.to_matrix().to_4x4()
        root.matrix_world = R @ mw

        # Optional: snap tiny floating errors
        context.view_layer.update()

        self.report({'INFO'}, f"Aligned '{root.name}' so cursor points to +Y (Re-Volt forward).")
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=420)

    def draw(self, context):
        layout = self.layout
        layout.label(text="Place the 3D Cursor at the FRONT bumper center", icon='INFO')
        layout.label(text="(between the front tires), then click OK.", icon='BLANK1')
        layout.separator()
        layout.label(text="Rule: Cursor defines where the car's nose should point.", icon='DOT')

"""
INSTANCES -----------------------------------------------------------------------
"""

class SetInstanceProperty(bpy.types.Operator):
    bl_idname = "instances.set_instance_property"
    bl_label = "Mark as Instance"
    bl_description = "Marks selected objects as instances and stores texture base"
    
    texture_base: bpy.props.StringProperty(
        name="Texture Base",
        description="Base name for level textures (e.g. 'elementary1')",
        default="texture"
    )

    def execute(self, context):
        for obj in context.selected_objects:
            if obj.type == 'MESH' and obj.mode == 'OBJECT':

                # ✔ Use RNA properties
                obj.is_instance = True
                obj.fin_env = True

                # ✔ ID props can still be used for arbitrary data
                obj["fin_texture_base"] = self.texture_base

                create_or_assign_env_material(obj)

        self.report({'INFO'}, f"Marked {len(context.selected_objects)} objects as instances")
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)


class RemoveInstanceProperty(bpy.types.Operator):
    bl_idname = "instances.rem_instance_property"
    bl_label = "Remove Instance Property"
    bl_description = "Removes the instance marking"

    def execute(self, context):
        removed_count = 0

        for obj in context.selected_objects:

            # ✔ Clear RNA property
            if getattr(obj, "is_instance", False):
                obj.is_instance = False
                removed_count += 1
                
            # Optional: disable env
            if hasattr(obj, "fin_env"):
                obj.fin_env = False

            # ✔ Remove helper ID property
            if "fin_texture_base" in obj:
                del obj["fin_texture_base"]

        context.view_layer.update()
        self.report({'INFO'}, f"Removed instance flag from {removed_count} objects")
        return {'FINISHED'}


class ImportInstanceNCP(bpy.types.Operator, ImportHelper):
    bl_idname = "instances.import_instance_ncp"
    bl_label = "Import Instance NCP"
    bl_description = "Import a .fin instance file using matching .ncp collision meshes instead of .prm visuals"
    filename_ext = ".fin"
    filter_glob: bpy.props.StringProperty(default="*.fin", options={'HIDDEN'})

    def execute(self, context):
        from . import fin_in

        before = set(context.scene.objects)
        try:
            fin_in.import_file(self.filepath, context.scene, mesh_extension=".ncp")
        except Exception as exc:
            self.report({'ERROR'}, f"Failed to import instance NCP: {exc}")
            return {'CANCELLED'}

        imported = [
            obj for obj in context.scene.objects
            if obj not in before and obj.get("is_ncp_collision")
        ]
        for obj in context.scene.objects:
            obj.select_set(False)
        for obj in imported:
            obj.select_set(True)
        if imported:
            context.view_layer.objects.active = imported[0]

        self.report({'INFO'}, f"Imported {len(imported)} instance NCP object(s).")
        return {'FINISHED'}
    
"""
MAKEITGOOD & HULL SPHERE -------------------------------------------------------
"""

class AddTrackZone(bpy.types.Operator):
    bl_idname = "scene.add_track_zone"
    bl_label = "Track Zone"
    bl_description = "Adds a new track zone under cursor location"
    bl_options = {'UNDO'}
    
    def execute(self, context):
        cursor_location = context.scene.cursor.location
        existing_zones = [obj for obj in bpy.data.objects if obj.get("is_track_zone")]
        next_id = max([obj.get("track_zone_id", -1) for obj in existing_zones], default=-1) + 1

        obj = create_zone(next_id, cursor_location)
        obj.is_track_zone = True
        context.view_layer.objects.active = obj  # Set the new zone as the active object
        obj.select_set(True)

        # Keep the focus on the Scene panel
        for area in context.screen.areas:
            if area.type == 'PROPERTIES':
                for space in area.spaces:
                    if space.type == 'PROPERTIES':
                        space.context = 'SCENE'
                        break

        return {'FINISHED'}


AI_NODE_NAME_RE = re.compile(r"^AI_(\d+)(?:_(\d+))?$", re.IGNORECASE)
AI_SELECTED_PATH_MARK_LAYER = "rv_ai_path_marker"
AI_SELECTED_PATH_START = 1
AI_SELECTED_PATH_END = 2


def _ai_node_objects(scene):
    return [
        obj for obj in scene.objects
        if getattr(obj, "is_ai_node", False) or obj.get("is_ai_node")
    ]


def _ai_node_index(obj, fallback=0):
    return int(getattr(obj, "ai_node_index", obj.get("ai_node_index", fallback)))


def _ai_node_name_parts(obj):
    match = AI_NODE_NAME_RE.match(obj.name)
    if not match:
        return (_ai_node_index(obj) + 1, 0)
    main = int(match.group(1))
    branch = int(match.group(2) or 0)
    return (main, branch)


def _ai_name_sort_key(obj):
    main, branch = _ai_node_name_parts(obj)
    is_branch = bool(branch or getattr(obj, "ai_is_secondary_path", obj.get("ai_is_secondary_path", False)))
    return (main, 1 if is_branch else 0, branch, _ai_node_index(obj), obj.name)


def _ai_node_by_index(scene, index):
    for obj in _ai_node_objects(scene):
        if _ai_node_index(obj) == index:
            return obj
    return None


def _ai_primary_nodes(scene):
    return sorted(
        [
            obj for obj in _ai_node_objects(scene)
            if not getattr(obj, "ai_is_secondary_path", obj.get("ai_is_secondary_path", False))
            and _ai_node_name_parts(obj)[1] == 0
        ],
        key=_ai_name_sort_key,
    )


def _ai_branch_nodes(scene, start_index):
    return sorted(
        [
            obj for obj in _ai_node_objects(scene)
            if (
                getattr(obj, "ai_is_secondary_path", obj.get("ai_is_secondary_path", False))
                and int(getattr(obj, "ai_branch_start_index", obj.get("ai_branch_start_index", -1))) == start_index
            )
        ],
        key=_ai_name_sort_key,
    )


def _ai_is_branch_node(obj):
    return bool(obj and getattr(obj, "ai_is_secondary_path", obj.get("ai_is_secondary_path", False)))


def _ai_branch_start_object(scene, obj):
    if obj is None:
        return None
    if _ai_is_branch_node(obj):
        start_index = int(getattr(obj, "ai_branch_start_index", obj.get("ai_branch_start_index", -1)))
        return _ai_node_by_index(scene, start_index)
    return obj


def _ai_branch_number(obj):
    helper_name = str(obj.get("ai_route_helper_name", ""))
    match = AI_NODE_NAME_RE.match(helper_name)
    if match:
        return int(match.group(2) or 0)
    _main, branch = _ai_node_name_parts(obj)
    return branch


def _ai_next_branch_display_number(scene, start_index):
    branch_nodes = _ai_branch_nodes(scene, start_index)
    numbers = [_ai_branch_number(obj) for obj in branch_nodes]
    numbers.append(len(branch_nodes))
    return max(numbers, default=0) + 1


def _ai_next_index(scene):
    return max([_ai_node_index(obj, -1) for obj in _ai_node_objects(scene)], default=-1) + 1


def _ai_next_primary_display_number(scene):
    mains = [
        _ai_node_name_parts(obj)[0]
        for obj in _ai_primary_nodes(scene)
    ]
    return max(mains, default=0) + 1


def _ai_connections(obj):
    values = list(getattr(obj, "ai_connections", obj.get("ai_connections", [-1, -1, -1, -1])))
    values = [int(value) for value in values[:4]]
    while len(values) < 4:
        values.append(-1)
    return values


def _set_ai_connections(obj, values):
    values = [int(value) for value in values[:4]]
    while len(values) < 4:
        values.append(-1)
    obj.ai_connections = values
    obj["ai_connections"] = values


def _prune_invalid_ai_references(scene):
    nodes = _ai_node_objects(scene)
    valid_indices = {_ai_node_index(obj) for obj in nodes}
    if not valid_indices:
        return 0

    changed = 0
    for obj in nodes:
        own_index = _ai_node_index(obj)
        connections = _ai_connections(obj)
        cleaned = [
            value if value in valid_indices and value != own_index else -1
            for value in connections
        ]
        if cleaned != connections:
            _set_ai_connections(obj, cleaned)
            changed += 1

        for attr_name in ("ai_branch_start_index", "ai_branch_join_index"):
            value = int(getattr(obj, attr_name, obj.get(attr_name, -1)))
            if value >= 0 and value not in valid_indices:
                setattr(obj, attr_name, -1)
                obj[attr_name] = -1
                changed += 1

        source_index = int(obj.get("ai_property_source_index", own_index))
        if source_index not in valid_indices:
            obj["ai_property_source_index"] = own_index
            obj["ai_property_source_reason"] = "raw/self"
            changed += 1

    header_start = int(getattr(scene, "ai_nodes_start_node", scene.get("ai_nodes_start_node", 0)))
    if header_start not in valid_indices:
        scene.ai_nodes_start_node = min(valid_indices)
        scene["ai_nodes_start_node"] = int(scene.ai_nodes_start_node)
        changed += 1

    header_end = int(getattr(scene, "ai_nodes_end_node", scene.get("ai_nodes_end_node", 0)))
    if header_end >= 0 and header_end not in valid_indices:
        scene.ai_nodes_end_node = min(valid_indices)
        scene["ai_nodes_end_node"] = int(scene.ai_nodes_end_node)
        changed += 1

    return changed


def _disconnect_ai_pair(first, second):
    first_index = _ai_node_index(first)
    second_index = _ai_node_index(second)
    changed = False

    first_connections = _ai_connections(first)
    cleaned_first = [-1 if value == second_index else value for value in first_connections]
    if cleaned_first != first_connections:
        _set_ai_connections(first, cleaned_first)
        changed = True

    second_connections = _ai_connections(second)
    cleaned_second = [-1 if value == first_index else value for value in second_connections]
    if cleaned_second != second_connections:
        _set_ai_connections(second, cleaned_second)
        changed = True

    return changed


def _ai_forward_link_score(source, target):
    source_index = _ai_node_index(source)
    target_index = _ai_node_index(target)
    source_connections = _ai_connections(source)
    target_connections = _ai_connections(target)
    score = 0
    if source_connections[2] == target_index:
        score += 8
    if target_connections[0] == source_index:
        score += 8
    if source_connections[3] == target_index:
        score += 4
    if target_connections[1] == source_index:
        score += 4
    if target_index in source_connections[2:4]:
        score += 2
    if source_index in target_connections[:2]:
        score += 2
    return score


def _ordered_ai_insert_pair(first, second, active=None):
    first_to_second = _ai_forward_link_score(first, second)
    second_to_first = _ai_forward_link_score(second, first)

    if first_to_second > second_to_first:
        return first, second
    if second_to_first > first_to_second:
        return second, first

    if active == first:
        return second, first
    if active == second:
        return first, second
    return first, second


def _connect_ai_forward(source, target, alternate=False):
    source_connections = _ai_connections(source)
    target_connections = _ai_connections(target)
    source_connections[3 if alternate else 2] = _ai_node_index(target)
    target_connections[1 if alternate else 0] = _ai_node_index(source)
    _set_ai_connections(source, source_connections)
    _set_ai_connections(target, target_connections)


def _connect_ai_rejoin(source, target):
    source_connections = _ai_connections(source)
    target_connections = _ai_connections(target)
    source_connections[2] = _ai_node_index(target)
    target_connections[1] = _ai_node_index(source)
    _set_ai_connections(source, source_connections)
    _set_ai_connections(target, target_connections)
    source.ai_branch_join_index = _ai_node_index(target)
    source["ai_branch_join_index"] = _ai_node_index(target)


def _clear_ai_connections(obj):
    _set_ai_connections(obj, [-1, -1, -1, -1])


def _remap_ai_index_value(value, index_map):
    value = int(value)
    return index_map.get(value, value) if value >= 0 else value


def _renumber_ai_nodes_after_insert(scene, inserted_obj, target_obj):
    target_index = _ai_node_index(target_obj)
    target_display, _target_branch = _ai_node_name_parts(target_obj)
    inserted_old_index = _ai_node_index(inserted_obj)
    if inserted_old_index == target_index:
        return

    nodes = _ai_node_objects(scene)
    index_map = {inserted_old_index: target_index}
    for obj in nodes:
        if obj == inserted_obj:
            continue
        old_index = _ai_node_index(obj)
        if old_index >= target_index:
            index_map[old_index] = old_index + 1

    final_names = {}
    for obj in nodes:
        main, branch = _ai_node_name_parts(obj)
        if obj == inserted_obj:
            final_names[obj] = f"AI_{target_display:03d}"
        elif main >= target_display:
            final_names[obj] = f"AI_{main + 1:03d}_{branch:03d}" if branch else f"AI_{main + 1:03d}"

    for obj in final_names:
        obj.name = f"__AI_RENUMBER_TMP_{id(obj)}"

    for obj in nodes:
        old_index = _ai_node_index(obj)
        new_index = index_map.get(old_index, old_index)
        obj.ai_node_index = new_index
        obj["ai_node_index"] = new_index
        if obj in final_names:
            obj.name = final_names[obj]

    for obj in nodes:
        _set_ai_connections(obj, [_remap_ai_index_value(value, index_map) for value in _ai_connections(obj)])
        branch_start = int(getattr(obj, "ai_branch_start_index", obj.get("ai_branch_start_index", -1)))
        branch_join = int(getattr(obj, "ai_branch_join_index", obj.get("ai_branch_join_index", -1)))
        if branch_start >= 0:
            obj.ai_branch_start_index = _remap_ai_index_value(branch_start, index_map)
            obj["ai_branch_start_index"] = int(obj.ai_branch_start_index)
        if branch_join >= 0:
            obj.ai_branch_join_index = _remap_ai_index_value(branch_join, index_map)
            obj["ai_branch_join_index"] = int(obj.ai_branch_join_index)

    scene.ai_nodes_start_node = _remap_ai_index_value(
        int(getattr(scene, "ai_nodes_start_node", 0)),
        index_map,
    )
    scene.ai_nodes_end_node = _remap_ai_index_value(
        int(getattr(scene, "ai_nodes_end_node", 0)),
        index_map,
    )


def _display_ai_ratio(value):
    value = float(value)
    return value if 0.0 <= value <= 1.0 else 0.5


def _rebuild_ai_node_helper_vertices(obj):
    if obj.type != "MESH" or not obj.data or len(obj.data.vertices) < 4:
        return
    left = obj.data.vertices[0].co
    right = obj.data.vertices[1].co
    racing_ratio = _display_ai_ratio(getattr(obj, "ai_racing_ratio", obj.get("ai_racing_ratio", 0.5)))
    preferred_ratio = _display_ai_ratio(getattr(obj, "ai_overtake_ratio", obj.get("ai_overtake_ratio", 0.5)))
    obj.data.vertices[2].co = left.lerp(right, racing_ratio)
    obj.data.vertices[3].co = left.lerp(right, preferred_ratio)
    obj.data.update()


def _apply_ai_creation_defaults(obj, scene, start_node=False):
    property_type = int(getattr(scene, "ai_nodes_default_property", 0))
    left_wall = bool(getattr(scene, "ai_nodes_default_left_wall", False))
    right_wall = bool(getattr(scene, "ai_nodes_default_right_wall", False))
    left_wall_flags = 0x03 if left_wall else 0
    right_wall_flags = 0x03 if right_wall else 0
    obj.ai_property_type = property_type
    obj.ai_property_enum = str(property_type)
    obj.ai_start_node = bool(start_node)
    obj.ai_left_wall = left_wall
    obj.ai_right_wall = right_wall
    obj.ai_left_wall_flags = left_wall_flags
    obj.ai_right_wall_flags = right_wall_flags
    obj.ai_flags = (
        (property_type & 0xFF)
        | (0x100 if start_node else 0)
        | (left_wall_flags << 16)
        | (right_wall_flags << 24)
    )
    obj["ai_flags"] = int(obj.ai_flags)
    obj["ai_left_wall_flags"] = left_wall_flags
    obj["ai_right_wall_flags"] = right_wall_flags
    obj.ai_green_speed = 30
    obj.ai_red_speed = 30
    obj.ai_racing_speed = 30
    obj.ai_center_speed = 30
    obj.ai_racing_ratio = 0.5
    obj.ai_overtake_ratio = 0.5
    obj.ai_lane_width = max(0.01, float(getattr(scene, "ai_nodes_lane_width", 2.0)))


class AddAINode(bpy.types.Operator):
    bl_idname = "scene.add_ai_node"
    bl_label = "AI Node Segment"
    bl_description = "Adds a new AI node segment at the 3D cursor, or inserts it between selected AI nodes"
    bl_options = {'REGISTER', 'UNDO'}

    update_names_after_insert: BoolProperty(
        name="Update the node names?",
        description="When inserting between two connected nodes, rename and renumber the inserted node and following nodes",
        default=True,
    )

    def _will_insert_between_selected(self, context):
        scene = context.scene
        if bool(getattr(scene, "ai_nodes_secondary_path", False)):
            return False
        if not bool(getattr(scene, "ai_nodes_connect_to_selected", True)):
            return False
        selected_nodes = [
            obj for obj in context.selected_objects
            if getattr(obj, "is_ai_node", False) or obj.get("is_ai_node")
        ]
        if any(_ai_is_branch_node(obj) for obj in selected_nodes):
            return False
        return len(selected_nodes) >= 2

    def invoke(self, context, event):
        if self._will_insert_between_selected(context):
            return context.window_manager.invoke_props_dialog(self, width=360)
        return self.execute(context)

    def draw(self, context):
        layout = self.layout
        layout.label(text="Update the node names?")
        layout.prop(self, "update_names_after_insert", text="Rename and renumber following nodes")

    def execute(self, context):
        scene = context.scene
        collection = ensure_collection()
        _prune_invalid_ai_references(scene)
        existing = _ai_node_objects(scene)
        selected_nodes = [
            obj for obj in context.selected_objects
            if getattr(obj, "is_ai_node", False) or obj.get("is_ai_node")
        ]
        active = context.view_layer.objects.active
        selected_active = active if active in selected_nodes else None
        connect_to_selected = bool(getattr(scene, "ai_nodes_connect_to_selected", True))
        next_index = _ai_next_index(scene)
        width = max(0.01, float(getattr(scene, "ai_nodes_lane_width", 2.0)))
        secondary_enabled = bool(getattr(scene, "ai_nodes_secondary_path", False))
        selected_branch = selected_active if _ai_is_branch_node(selected_active) else next(
            (obj for obj in selected_nodes if _ai_is_branch_node(obj)),
            None,
        )
        continue_selected_branch = connect_to_selected and selected_branch is not None

        branch_start = None
        previous = None
        insert_target = None
        name = None
        start_node = not existing
        location = scene.cursor.location.copy()

        if secondary_enabled or continue_selected_branch:
            branch_reference = selected_branch if continue_selected_branch else None
            if branch_reference is None:
                branch_start_index = int(getattr(scene, "ai_nodes_branch_start", "-1"))
                branch_reference = _ai_node_by_index(scene, branch_start_index)
            branch_start = _ai_branch_start_object(scene, branch_reference)
            if branch_start is None:
                self.report({'WARNING'}, "Choose a Branch Start node before creating a secondary path node.")
                return {'CANCELLED'}

            branch_start_index = _ai_node_index(branch_start)
            start_display, _ = _ai_node_name_parts(branch_start)
            branch_number = _ai_next_branch_display_number(scene, branch_start_index)
            name = f"AI_{start_display:03d}_{branch_number:03d}"
            if _ai_is_branch_node(branch_reference):
                previous = branch_reference
            else:
                branch_nodes = _ai_branch_nodes(scene, branch_start_index)
                previous = branch_nodes[-1] if branch_nodes else branch_start
            start_node = False
        elif connect_to_selected and len(selected_nodes) >= 2:
            first = selected_active or selected_nodes[0]
            second = next((obj for obj in selected_nodes if obj != first), selected_nodes[0])
            source, target = _ordered_ai_insert_pair(first, second, active=selected_active)
            display_number = _ai_next_primary_display_number(scene)
            name = f"AI_{display_number:03d}"
            previous = source
            insert_target = target
            location = (_ai_node_center_world(source) + _ai_node_center_world(target)) * 0.5
            start_node = False
        elif connect_to_selected and selected_nodes:
            display_number = _ai_next_primary_display_number(scene)
            name = f"AI_{display_number:03d}"
            previous = selected_active or selected_nodes[0]
            start_node = False
        else:
            display_number = _ai_next_primary_display_number(scene)
            name = f"AI_{display_number:03d}"
            primaries = _ai_primary_nodes(scene)
            previous = primaries[-1] if primaries else None

        obj = create_ai_node_object(
            index=next_index,
            location=location,
            collection=collection,
            width=width,
            name=name,
        )
        _apply_ai_creation_defaults(obj, scene, start_node=start_node)

        if (secondary_enabled or continue_selected_branch) and branch_start:
            obj.ai_is_secondary_path = True
            obj["ai_is_secondary_path"] = True
            obj["ai_route_helper_name"] = name
            obj.ai_branch_start_index = _ai_node_index(branch_start)
            obj["ai_branch_start_index"] = _ai_node_index(branch_start)
            if previous == branch_start:
                _connect_ai_forward(branch_start, obj, alternate=True)
            else:
                previous.ai_branch_join_index = -1
                previous["ai_branch_join_index"] = -1
                _connect_ai_forward(previous, obj, alternate=False)
        elif previous:
            if insert_target:
                _disconnect_ai_pair(previous, insert_target)
            _connect_ai_forward(previous, obj, alternate=False)
            if insert_target:
                _connect_ai_forward(obj, insert_target, alternate=False)
                if self.update_names_after_insert:
                    _renumber_ai_nodes_after_insert(scene, obj, insert_target)

        context.view_layer.objects.active = obj
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        rebuild_ai_route_visuals(scene)
        return {'FINISHED'}


def _is_pos_node_object(obj):
    return bool(obj and (getattr(obj, "is_pos_node", False) or obj.get("is_pos_node")))


def _pos_node_objects(scene):
    collection = bpy.data.collections.get("POS_NODES")
    source = collection.objects if collection else scene.objects
    return sorted(
        [obj for obj in source if _is_pos_node_object(obj)],
        key=lambda obj: int(getattr(obj, "pos_node_index", obj.get("pos_node_index", 0))),
    )


def _pos_node_index(obj):
    return int(getattr(obj, "pos_node_index", obj.get("pos_node_index", 0)))


def _pos_next_index(scene):
    existing = _pos_node_objects(scene)
    if not existing:
        return 0
    return max(_pos_node_index(obj) for obj in existing) + 1


def _pos_connections(obj, attr_name, key_name):
    values = list(getattr(obj, attr_name, obj.get(key_name, [-1, -1, -1, -1])))
    values = [int(v) for v in values[:4]]
    while len(values) < 4:
        values.append(-1)
    return values


def _set_pos_connections(obj, prev_nodes=None, next_nodes=None):
    if prev_nodes is not None:
        prev_nodes = [int(v) for v in prev_nodes[:4]]
        while len(prev_nodes) < 4:
            prev_nodes.append(-1)
        obj.pos_prev_nodes = prev_nodes
        obj["pos_prev_nodes"] = prev_nodes
    if next_nodes is not None:
        next_nodes = [int(v) for v in next_nodes[:4]]
        while len(next_nodes) < 4:
            next_nodes.append(-1)
        obj.pos_next_nodes = next_nodes
        obj["pos_next_nodes"] = next_nodes


def _pos_connection_slot(values, target_index, preferred_slot=0, replace=True):
    target_index = int(target_index)
    for slot, value in enumerate(values):
        if int(value) == target_index:
            return slot

    if 0 <= preferred_slot < len(values) and (replace or int(values[preferred_slot]) < 0):
        return preferred_slot

    for slot, value in enumerate(values):
        if int(value) < 0:
            return slot

    return preferred_slot if replace else -1


def _pos_has_outgoing_connection(obj):
    return any(
        value >= 0
        for value in _pos_connections(obj, "pos_next_nodes", "pos_next_nodes")
    )


def _update_view_layer(context):
    try:
        context.view_layer.update()
    except Exception:
        pass


def _connect_pos_forward(source, target, alternate=False, replace=True):
    source_next = _pos_connections(source, "pos_next_nodes", "pos_next_nodes")
    target_prev = _pos_connections(target, "pos_prev_nodes", "pos_prev_nodes")
    preferred_slot = 1 if alternate else 0
    source_slot = _pos_connection_slot(source_next, _pos_node_index(target), preferred_slot, replace)
    target_slot = _pos_connection_slot(target_prev, _pos_node_index(source), preferred_slot, replace)
    if source_slot < 0 or target_slot < 0:
        return False
    source_next[source_slot] = _pos_node_index(target)
    target_prev[target_slot] = _pos_node_index(source)
    _set_pos_connections(source, next_nodes=source_next)
    _set_pos_connections(target, prev_nodes=target_prev)
    return True


def _connect_pos_chain(created, append_tail=None, closed=False):
    if append_tail and created:
        tail_next = _pos_connections(append_tail, "pos_next_nodes", "pos_next_nodes")
        tail_next[0] = _pos_node_index(created[0])
        _set_pos_connections(append_tail, next_nodes=tail_next)

    close_created_loop = bool(closed and len(created) > 1 and not append_tail)
    for i, obj in enumerate(created):
        prev_nodes = [-1, -1, -1, -1]
        next_nodes = [-1, -1, -1, -1]
        if i > 0:
            prev_nodes[0] = _pos_node_index(created[i - 1])
        elif append_tail:
            prev_nodes[0] = _pos_node_index(append_tail)
        elif close_created_loop:
            prev_nodes[0] = _pos_node_index(created[-1])
        if i < len(created) - 1:
            next_nodes[0] = _pos_node_index(created[i + 1])
        elif close_created_loop:
            next_nodes[0] = _pos_node_index(created[0])
        _set_pos_connections(obj, prev_nodes=prev_nodes, next_nodes=next_nodes)


def _pos_node_center_world(obj):
    return obj.matrix_world.translation.copy()


def _pos_start_ai_node(scene):
    nodes = _ai_primary_nodes(scene)
    if not nodes:
        return None

    by_index = {_ai_node_index(obj): obj for obj in nodes}
    header_start = int(getattr(scene, "ai_nodes_start_node", scene.get("ai_nodes_start_node", -1)))
    if header_start in by_index:
        return by_index[header_start]

    for obj in nodes:
        if bool(getattr(obj, "ai_start_node", obj.get("ai_start_node", False))):
            return obj

    return nodes[0]


def _pos_ordered_ai_primary_nodes(scene):
    start = _pos_start_ai_node(scene)
    nodes = _ai_primary_nodes(scene)
    if start is None:
        return nodes

    by_index = {_ai_node_index(obj): obj for obj in nodes}
    ordered = []
    visited = set()
    current_index = _ai_node_index(start)

    while current_index in by_index and current_index not in visited:
        obj = by_index[current_index]
        ordered.append(obj)
        visited.add(current_index)
        next_index = -1
        for candidate in _ai_connections(obj)[2:4]:
            if candidate in by_index and candidate not in visited:
                next_index = candidate
                break
        current_index = next_index

    ordered.extend(obj for obj in nodes if _ai_node_index(obj) not in visited)
    return ordered


def _pos_auto_density(scene):
    value = float(getattr(scene, "pos_nodes_auto_spacing", 2.0))
    value = max(1.0, min(3.0, value))
    return 0.8 + ((value - 1.0) * 0.2)


def _path_length(points):
    if len(points) < 2:
        return 0.0
    return sum((points[i] - points[i - 1]).length for i in range(1, len(points)))


def _resample_path_points(points, target_count):
    if len(points) < 2 or target_count <= 0:
        return points

    target_count = max(2, int(target_count))
    if target_count == len(points):
        return [point.copy() for point in points]

    segment_lengths = [(points[i] - points[i - 1]).length for i in range(1, len(points))]
    total_length = sum(segment_lengths)
    if total_length <= 0.000001:
        return [point.copy() for point in points[:target_count]]

    result = [points[0].copy()]
    segment_index = 0
    segment_start_distance = 0.0
    step = total_length / float(target_count - 1)

    for sample_index in range(1, target_count - 1):
        distance = step * sample_index
        while (
            segment_index < len(segment_lengths) - 1
            and segment_start_distance + segment_lengths[segment_index] < distance
        ):
            segment_start_distance += segment_lengths[segment_index]
            segment_index += 1

        segment_length = segment_lengths[segment_index]
        if segment_length <= 0.000001:
            result.append(points[segment_index + 1].copy())
            continue
        factor = (distance - segment_start_distance) / segment_length
        result.append(points[segment_index].lerp(points[segment_index + 1], factor))

    result.append(points[-1].copy())
    return result


def _resample_closed_path_points(points, target_count):
    if len(points) < 2 or target_count <= 0:
        return points

    target_count = max(2, int(target_count))
    segment_lengths = [
        (points[(i + 1) % len(points)] - points[i]).length
        for i in range(len(points))
    ]
    total_length = sum(segment_lengths)
    if total_length <= 0.000001:
        return [points[i % len(points)].copy() for i in range(target_count)]

    result = []
    segment_index = 0
    segment_start_distance = 0.0
    step = total_length / float(target_count)

    for sample_index in range(target_count):
        distance = step * sample_index
        while (
            segment_index < len(segment_lengths) - 1
            and segment_start_distance + segment_lengths[segment_index] < distance
        ):
            segment_start_distance += segment_lengths[segment_index]
            segment_index += 1

        segment_length = segment_lengths[segment_index]
        start = points[segment_index]
        end = points[(segment_index + 1) % len(points)]
        if segment_length <= 0.000001:
            result.append(end.copy())
            continue
        factor = (distance - segment_start_distance) / segment_length
        result.append(start.lerp(end, factor))

    return result


def _pos_automation_spacing_distance(scene, points=None):
    source_points = points
    if not source_points:
        source_points = [_ai_point_from_object(obj) for obj in _pos_ordered_ai_primary_nodes(scene)]

    if source_points and len(source_points) > 1:
        base_spacing = _path_length(source_points) / float(len(source_points) - 1)
    else:
        base_spacing = 12.0

    return max(0.5, base_spacing / _pos_auto_density(scene))


def _recalculate_pos_node_distances(scene, objects=None):
    if objects is None:
        objects = _pos_node_objects(scene)
    if not objects:
        scene.pos_nodes_total_dist = 0.0
        return 0.0

    start_index = int(getattr(scene, "pos_nodes_start_node", scene.get("pos_nodes_start_node", _pos_node_index(objects[-1]))))
    by_index = {_pos_node_index(obj): obj for obj in objects}
    reverse_order = []
    visited = set()
    current_index = start_index
    while current_index in by_index and current_index not in visited:
        reverse_order.append(current_index)
        visited.add(current_index)
        current_obj = by_index[current_index]
        prev_candidates = [
            idx for idx in _pos_connections(current_obj, "pos_prev_nodes", "pos_prev_nodes")
            if idx in by_index and idx not in visited
        ]
        if not prev_candidates:
            break
        current_index = prev_candidates[0]

    for obj in reversed(objects):
        index = _pos_node_index(obj)
        if index not in visited:
            reverse_order.append(index)
            visited.add(index)

    running = 0.0
    previous_obj = None
    for index in reverse_order:
        obj = by_index[index]
        if previous_obj is not None:
            running += to_revolt_scale((_pos_node_center_world(previous_obj) - _pos_node_center_world(obj)).length)
        obj.pos_node_distance = float(running)
        obj["pos_node_distance"] = float(running)
        previous_obj = obj

    start_obj = by_index.get(start_index)
    if previous_obj is not None and start_obj is not None:
        previous_index = _pos_node_index(previous_obj)
        if previous_index in _pos_connections(start_obj, "pos_next_nodes", "pos_next_nodes"):
            running += to_revolt_scale((_pos_node_center_world(previous_obj) - _pos_node_center_world(start_obj)).length)

    scene.pos_nodes_total_dist = float(running)
    return running


class AddPosNode(bpy.types.Operator):
    bl_idname = "scene.add_pos_node"
    bl_label = "Position Node"
    bl_description = "Adds a new position node at the 3D cursor and connects it to the selected, split, or previous position node"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        collection = ensure_pos_collection()
        existing = _pos_node_objects(scene)
        selected_nodes = [obj for obj in context.selected_objects if _is_pos_node_object(obj)]
        active = context.view_layer.objects.active
        selected_active = active if active in selected_nodes else None
        split_enabled = bool(getattr(scene, "pos_nodes_split_route", False))
        previous = None
        split_start = None

        if split_enabled:
            if selected_active is None:
                self.report({'WARNING'}, "Select the position node to split from.")
                return {'CANCELLED'}
            split_start = selected_active
            previous = selected_active
        else:
            previous = selected_active if selected_active else (selected_nodes[-1] if selected_nodes else (existing[-1] if existing else None))

        next_index = _pos_next_index(scene)
        obj = create_pos_node_object(
            index=next_index,
            location=scene.cursor.location.copy(),
            collection=collection,
            name=f"POS_{next_index + 1:03d}",
        )
        if previous:
            use_extra_slot = split_enabled and _pos_has_outgoing_connection(previous)
            _connect_pos_forward(previous, obj, alternate=use_extra_slot, replace=not split_enabled)
        if split_enabled:
            obj.pos_is_split_route = True
            obj["pos_is_split_route"] = True
            obj.pos_route_start_index = _pos_node_index(split_start)
            obj["pos_route_start_index"] = _pos_node_index(split_start)
        if not split_enabled:
            scene.pos_nodes_start_node = _pos_node_index(obj)

        context.view_layer.objects.active = obj
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        _update_view_layer(context)
        _recalculate_pos_node_distances(scene)
        rebuild_pos_route_visuals(scene)
        _update_view_layer(context)
        return {'FINISHED'}


class ConnectPosPathToTarget(bpy.types.Operator):
    bl_idname = "scene.connect_pos_path_to_target"
    bl_label = "Connect Selected"
    bl_description = "Connect exactly two selected position nodes; the non-active node points to the active node"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        target = context.active_object
        if not _is_pos_node_object(target):
            self.report({'WARNING'}, "Make the target position node active.")
            return {'CANCELLED'}

        selected_nodes = [obj for obj in context.selected_objects if _is_pos_node_object(obj)]
        if len(selected_nodes) != 2 or target not in selected_nodes:
            self.report({'WARNING'}, "Select exactly two position nodes. The active node is the target.")
            return {'CANCELLED'}

        source = next(obj for obj in selected_nodes if obj != target)
        if not _connect_pos_forward(source, target, alternate=False, replace=False):
            self.report({'WARNING'}, "No free position-node connection slot was available.")
            return {'CANCELLED'}

        _update_view_layer(context)
        _recalculate_pos_node_distances(context.scene)
        rebuild_pos_route_visuals(context.scene)
        _update_view_layer(context)
        self.report({'INFO'}, f"Connected {source.name} to {target.name}.")
        return {'FINISHED'}


def _ai_point_from_object(obj):
    if getattr(obj, "is_ai_node", False) or obj.get("is_ai_node"):
        if obj.type == "MESH" and obj.data and len(obj.data.vertices) >= 2:
            left = obj.matrix_world @ obj.data.vertices[0].co
            right = obj.matrix_world @ obj.data.vertices[1].co
            return (left + right) * 0.5
    return obj.matrix_world.translation.copy()


def _nearest_order(points, start_index=0):
    if not points:
        return []

    remaining = list(range(len(points)))
    ordered = [remaining.pop(start_index)]
    while remaining:
        current = points[ordered[-1]]
        next_pos = min(remaining, key=lambda idx: (points[idx] - current).length_squared)
        ordered.append(next_pos)
        remaining.remove(next_pos)
    return [points[idx] for idx in ordered]


def _remove_ai_node_objects(scene):
    for obj in list(scene.objects):
        if (
            getattr(obj, "is_ai_node", False)
            or obj.get("is_ai_node")
            or obj.get("is_ai_route_visual")
            or obj.get("is_ai_node_handle")
        ):
            data = obj.data if obj.type in {"MESH", "CURVE"} else None
            is_curve = obj.type == "CURVE"
            bpy.data.objects.remove(obj, do_unlink=True)
            if data and data.users == 0:
                if is_curve:
                    bpy.data.curves.remove(data)
                else:
                    bpy.data.meshes.remove(data)


def _track_zone_center_world(obj):
    if obj.type == "MESH" and obj.bound_box:
        points = [obj.matrix_world @ BlenderVector(corner) for corner in obj.bound_box]
        center = BlenderVector((0.0, 0.0, 0.0))
        for point in points:
            center += point
        return center / len(points)
    return obj.matrix_world.translation.copy()


def _collision_mesh_objects(scene):
    result = []
    for obj in scene.objects:
        if obj.type != "MESH" or not obj.data or not obj.data.polygons:
            continue
        if (
            getattr(obj, "is_ai_node", False)
            or obj.get("is_ai_node")
            or obj.get("is_ai_node_handle")
            or obj.get("is_ai_route_visual")
            or getattr(obj, "is_track_zone", False)
            or obj.get("is_track_zone")
            or obj.get("is_bbox")
            or obj.get("is_cube")
            or obj.get("is_bcube")
        ):
            continue
        source_path = str(obj.get("source_path", ""))
        name = obj.name.lower()
        if obj.get("is_ncp_collision") or source_path.lower().endswith(".ncp") or ".ncp" in name:
            result.append(obj)
    return result


def _automation_obstacle_mesh_objects(scene, floor_meshes):
    floor_set = set(floor_meshes)
    result = list(floor_meshes)
    for obj in scene.objects:
        if obj in floor_set or obj.type != "MESH" or not obj.data or not obj.data.polygons:
            continue
        source_path = str(obj.get("source_path", "")).lower()
        name = obj.name.lower()
        if not (obj.get("is_ncp_collision") or source_path.endswith(".ncp") or ".ncp" in name):
            continue
        if (
            getattr(obj, "is_ai_node", False)
            or obj.get("is_ai_node")
            or obj.get("is_ai_node_handle")
            or obj.get("is_ai_route_visual")
            or getattr(obj, "is_track_zone", False)
            or obj.get("is_track_zone")
            or obj.get("is_bbox")
            or obj.get("is_cube")
            or obj.get("is_bcube")
        ):
            continue
        result.append(obj)
    return result


def _collision_bvh_entries(context, objects):
    depsgraph = context.evaluated_depsgraph_get()
    entries = []
    for obj in objects:
        try:
            tree = BVHTree.FromObject(obj, depsgraph)
        except Exception:
            tree = None
        if tree:
            entries.append((obj, tree, obj.matrix_world.copy(), obj.matrix_world.inverted_safe()))
    return entries


def _raycast_collision_bvhs(entries, origin, direction, distance):
    best = None
    for obj, tree, matrix, inverse in entries:
        local_origin = inverse @ origin
        local_direction = inverse.to_3x3() @ direction
        if local_direction.length <= 0.000001:
            continue
        local_direction.normalize()
        hit = tree.ray_cast(local_origin, local_direction, distance * 2.0)
        if hit[0] is None:
            continue
        hit_local, normal_local, face_index, _hit_distance = hit
        hit_world = matrix @ hit_local
        world_distance = (hit_world - origin).length
        if world_distance > distance:
            continue
        normal_world = (matrix.to_3x3() @ normal_local).normalized()
        if best is None or world_distance < best[3]:
            best = (hit_world, normal_world, face_index, world_distance, obj)
    return best


def _project_point_to_collision_floor(entries, point, height=120.0):
    origin = point + BlenderVector((0.0, 0.0, height))
    hit = _raycast_collision_bvhs(entries, origin, BlenderVector((0.0, 0.0, -1.0)), height * 2.0)
    if not hit:
        return None
    hit_world, normal_world, _face_index, _distance, _obj = hit
    if normal_world.z < 0.25:
        return None
    return hit_world


def _project_point_to_collision_floor_near(entries, point, height=18.0):
    hit = _raycast_collision_bvhs(
        entries,
        point + BlenderVector((0.0, 0.0, height * 0.5)),
        BlenderVector((0.0, 0.0, -1.0)),
        height,
    )
    if not hit:
        return None
    hit_world, normal_world, _face_index, _distance, _obj = hit
    if normal_world.z < 0.25:
        return None
    if abs(hit_world.z - point.z) > height:
        return None
    return hit_world


def _project_point_to_collision_floor_near_hit(entries, point, height=18.0):
    hit = _raycast_collision_bvhs(
        entries,
        point + BlenderVector((0.0, 0.0, height * 0.5)),
        BlenderVector((0.0, 0.0, -1.0)),
        height,
    )
    if not hit:
        return None
    hit_world, normal_world, _face_index, _distance, _obj = hit
    if normal_world.z < 0.25:
        return None
    if abs(hit_world.z - point.z) > height:
        return None
    return hit_world, normal_world


def _world_bbox_bounds(obj):
    if obj.type == "MESH" and obj.bound_box:
        points = [obj.matrix_world @ BlenderVector(corner) for corner in obj.bound_box]
    else:
        point = obj.matrix_world.translation.copy()
        points = [point]
    min_x = min(point.x for point in points)
    max_x = max(point.x for point in points)
    min_y = min(point.y for point in points)
    max_y = max(point.y for point in points)
    min_z = min(point.z for point in points)
    max_z = max(point.z for point in points)
    return min_x, max_x, min_y, max_y, min_z, max_z


def _track_zone_collision_floor_candidates(entries, zone):
    min_x, max_x, min_y, max_y, min_z, max_z = _world_bbox_bounds(zone)
    center = _track_zone_center_world(zone)
    margin = 1.0
    ray_distance = max(1.0, (max_z - min_z) + margin * 2.0)
    samples = [(center.x, center.y)]

    for factor in (0.18, -0.18, 0.32, -0.32):
        samples.append((center.x + (max_x - min_x) * factor, center.y))
        samples.append((center.x, center.y + (max_y - min_y) * factor))
    for fx in (-0.28, 0.0, 0.28):
        for fy in (-0.28, 0.0, 0.28):
            samples.append((center.x + (max_x - min_x) * fx, center.y + (max_y - min_y) * fy))

    origin_z_values = [
        max_z + margin,
    ]
    results = []
    seen = set()
    for sample_x, sample_y in samples:
        for origin_z in origin_z_values:
            origin = BlenderVector((sample_x, sample_y, origin_z))
            hit = _raycast_collision_bvhs(entries, origin, BlenderVector((0.0, 0.0, -1.0)), ray_distance)
            if not hit:
                continue
            hit_world, normal_world, _face_index, _distance, _obj = hit
            if normal_world.z < 0.25:
                continue
            if hit_world.z < min_z - margin or hit_world.z > max_z + margin:
                continue
            key = (round(hit_world.x, 3), round(hit_world.y, 3), round(hit_world.z, 3))
            if key in seen:
                continue
            seen.add(key)
            score = (BlenderVector((hit_world.x, hit_world.y, 0.0)) - BlenderVector((center.x, center.y, 0.0))).length_squared
            results.append((score, hit_world))

    results.sort(key=lambda item: item[0])
    return [point for _score, point in results]


def _track_zone_collision_floor_point(entries, zone):
    candidates = _track_zone_collision_floor_candidates(entries, zone)
    return candidates[0] if candidates else None


def _track_zone_id(obj):
    return int(getattr(obj, "track_zone_id", obj.get("track_zone_id", 0)))


def _track_zone_candidate_order_score(obstacle_entries, previous_point, point, previous_direction=None):
    distance = (point - previous_point).length
    blocked = _collision_segment_blocked(obstacle_entries, previous_point, point)
    direction_penalty = 0.0
    if previous_direction is not None:
        movement = point - previous_point
        movement.z = 0.0
        if movement.length > 0.000001:
            movement.normalize()
            dot = max(-1.0, min(1.0, previous_direction.dot(movement)))
            if dot < 0.15:
                direction_penalty += distance * (0.15 - dot) * 1.8 + 6.0
            if dot < -0.25:
                direction_penalty += 50.0
    return distance + direction_penalty + (100000.0 if blocked else 0.0)


def _best_track_zone_candidate_point(obstacle_entries, previous_point, candidate_points, previous_direction=None):
    if not candidate_points:
        return None
    if previous_point is None:
        return candidate_points[0]
    scored = []
    for order, point in enumerate(candidate_points):
        scored.append((
            _track_zone_candidate_order_score(
                obstacle_entries,
                previous_point,
                point,
                previous_direction,
            ) + order * 8.0,
            (point - previous_point).length_squared,
            point,
        ))
    return min(scored, key=lambda item: (item[0], item[1]))[2]


def _track_zone_overlap_floor_point(floor_entries, zone_a, zone_b, z_hint):
    a_min_x, a_max_x, a_min_y, a_max_y, _a_min_z, _a_max_z = _world_bbox_bounds(zone_a)
    b_min_x, b_max_x, b_min_y, b_max_y, _b_min_z, _b_max_z = _world_bbox_bounds(zone_b)
    min_x = max(a_min_x, b_min_x)
    max_x = min(a_max_x, b_max_x)
    min_y = max(a_min_y, b_min_y)
    max_y = min(a_max_y, b_max_y)
    if max_x <= min_x or max_y <= min_y:
        return None

    center = BlenderVector(((min_x + max_x) * 0.5, (min_y + max_y) * 0.5, z_hint))
    return _project_point_to_collision_floor_near(floor_entries, center, height=5.0)


def _insert_track_zone_overlap_points(floor_entries, obstacle_entries, ordered, spacing):
    if len(ordered) < 2:
        return ordered

    result = [ordered[0]]
    for i in range(1, len(ordered)):
        prev_zone, prev_point = result[-1]
        zone, point = ordered[i]
        overlap = _track_zone_overlap_floor_point(floor_entries, prev_zone, zone, (prev_point.z + point.z) * 0.5)

        if overlap is not None:
            add_overlap = (
                (overlap - prev_point).length >= 0.35
                and (overlap - point).length >= 0.35
            )
            if add_overlap and i + 1 < len(ordered):
                incoming = prev_point - (result[-2][1] if len(result) > 1 else prev_point)
                outgoing = ordered[i + 1][1] - point
                incoming.z = 0.0
                outgoing.z = 0.0
                if incoming.length > 0.000001 and outgoing.length > 0.000001:
                    incoming.normalize()
                    outgoing.normalize()
                    add_overlap = incoming.dot(outgoing) < 0.72
            if add_overlap:
                direct_blocked = _collision_segment_blocked(obstacle_entries, prev_point, point)
                via_blocked = (
                    _collision_segment_blocked(obstacle_entries, prev_point, overlap)
                    or _collision_segment_blocked(obstacle_entries, overlap, point)
                )
                if not via_blocked or direct_blocked:
                    result.append((prev_zone, overlap))

        result.append((zone, point))

    return result


def _ordered_selected_track_zone_points(floor_entries, obstacle_entries, zones, active_zone=None):
    candidates = []
    missing_floor = []
    for zone in zones:
        floor_points = _track_zone_collision_floor_candidates(floor_entries, zone)
        if not floor_points:
            missing_floor.append(zone.name)
            continue
        candidates.append((_track_zone_id(zone), zone, floor_points))

    if len(candidates) < 2:
        return [], missing_floor, 0

    by_id = {}
    for zone_id, zone, points in candidates:
        by_id.setdefault(zone_id, []).append((zone, points))

    selected_ids = sorted(by_id)

    ordered = []
    previous_direction = None
    for chain_index, zone_id in enumerate(selected_ids):
        choices = by_id[zone_id]
        previous_point = ordered[-1][1] if ordered else None
        if active_zone in [zone for zone, _points in choices]:
            zone, points = next((zone, points) for zone, points in choices if zone == active_zone)
            point = _best_track_zone_candidate_point(obstacle_entries, previous_point, points, previous_direction)
        elif chain_index == 0:
            zone, points = sorted(choices, key=lambda item: item[0].name)[0]
            point = points[0]
        else:
            zone, points = min(
                choices,
                key=lambda item: (
                    _track_zone_candidate_order_score(
                        obstacle_entries,
                        previous_point,
                        _best_track_zone_candidate_point(obstacle_entries, previous_point, item[1], previous_direction),
                        previous_direction,
                    ),
                    item[0].name,
                ),
            )
            point = _best_track_zone_candidate_point(obstacle_entries, previous_point, points, previous_direction)
        if point is None:
            continue
        if previous_point is not None:
            delta = point - previous_point
            horizontal = BlenderVector((delta.x, delta.y, 0.0))
            if horizontal.length > 0.000001:
                previous_direction = horizontal.normalized()
        ordered.append((zone, point))

    ordered_count = len(ordered)
    ordered = _insert_track_zone_overlap_points(floor_entries, obstacle_entries, ordered, spacing=4.0)
    ignored = len(candidates) - ordered_count
    return [point for _zone, point in ordered], missing_floor, ignored


def _dedupe_path_points(points, threshold=0.05, closed=False):
    deduped = []
    for point in points:
        if deduped and (point - deduped[-1]).length < threshold:
            continue
        deduped.append(point)
    if closed and len(deduped) > 1 and (deduped[0] - deduped[-1]).length < threshold:
        deduped.pop()
    return deduped


def _path_corner_support_points(floor_entries, obstacle_entries, points, spacing, closed=True):
    if len(points) < 3:
        return points

    result = []
    count = len(points)
    start = 0 if closed else 1
    end = count if closed else count - 1

    if not closed:
        result.append(points[0])

    for i in range(start, end):
        prev_point = points[(i - 1) % count]
        point = points[i]
        next_point = points[(i + 1) % count]
        incoming = point - prev_point
        outgoing = next_point - point
        incoming.z = 0.0
        outgoing.z = 0.0

        if incoming.length <= 0.000001 or outgoing.length <= 0.000001:
            result.append(point)
            continue

        incoming_len = incoming.length
        outgoing_len = outgoing.length
        incoming.normalize()
        outgoing.normalize()
        dot = max(-1.0, min(1.0, incoming.dot(outgoing)))

        if dot > 0.82:
            result.append(point)
            continue

        offset = min(spacing * 0.35, incoming_len * 0.35, outgoing_len * 0.35)
        offset = max(0.25, offset)
        candidates = [point]

        # Keep track-zone points as hard corner anchors. Adding an approach point
        # before the corner made some automated paths begin turning too early.
        # A short exit support still gives the spacing/refinement pass enough
        # information to follow the turn without cutting across the wall.
        if dot < 0.72:
            candidates.append(point + outgoing * offset)

        for candidate in candidates:
            floor = _project_point_to_collision_floor_near(floor_entries, candidate, height=3.5)
            if floor is None:
                continue
            if result and (floor - result[-1]).length < 0.05:
                continue
            if result and _collision_segment_blocked(obstacle_entries, result[-1], floor):
                # Keep the original zone point as an anchor, then let refinement
                # search around the obstruction instead of smoothing across it.
                anchor = _project_point_to_collision_floor_near(floor_entries, point, height=3.5)
                if anchor is not None and (not result or (anchor - result[-1]).length >= 0.05):
                    result.append(anchor)
                continue
            result.append(floor)

    if not closed:
        result.append(points[-1])

    return _dedupe_path_points(result, threshold=0.08, closed=closed)


def _collision_segment_blocked(entries, start, end, clearance=0.28):
    delta = end - start
    distance = delta.length
    if distance <= 0.000001:
        return False
    direction = delta.normalized()
    side = BlenderVector((-direction.y, direction.x, 0.0))
    if side.length > 0.000001:
        side.normalize()
    else:
        side = BlenderVector((0.0, 0.0, 0.0))
    for z_offset in (clearance, clearance * 2.0, clearance * 3.2):
        for side_offset in (0.0, clearance * 0.6, -clearance * 0.6):
            origin = start + direction * 0.05 + side * side_offset + BlenderVector((0.0, 0.0, z_offset))
            hit = _raycast_collision_bvhs(entries, origin, direction, max(0.0, distance - 0.1))
            if hit and hit[1].z < 0.35:
                return True
    return False


def _collision_path_segment_clear(floor_entries, obstacle_entries, start, end, spacing):
    if _collision_segment_blocked(obstacle_entries, start, end):
        return False
    distance = (end - start).length
    if distance <= 0.000001:
        return True
    steps = max(1, int(math.ceil(distance / max(1.0, spacing * 0.6))))
    for step in range(1, steps):
        factor = step / steps
        sample = start.lerp(end, factor)
        floor = _project_point_to_collision_floor_near(floor_entries, sample, height=2.5)
        if floor is None:
            return False
        if abs(floor.z - sample.z) > 3.0:
            return False
    return True


def _automation_side_floor_distance(floor_entries, obstacle_entries, center, side, default_half_width, spacing):
    step = max(0.25, min(0.75, default_half_width * 0.35))
    max_distance = max(default_half_width, spacing * 0.9)
    last_good = max(0.1, default_half_width * 0.35)
    base_hit = _project_point_to_collision_floor_near_hit(floor_entries, center, height=3.0)
    base_z = center.z if base_hit is None else base_hit[0].z

    distance = step
    while distance <= max_distance + 0.0001:
        candidate = center + side * distance
        hit = _project_point_to_collision_floor_near_hit(floor_entries, candidate, height=3.0)
        if hit is None:
            break
        floor_point, normal = hit
        if normal.z < 0.72:
            break
        if abs(floor_point.z - base_z) > 1.2:
            break
        if _collision_segment_blocked(obstacle_entries, center, floor_point, clearance=0.22):
            break
        last_good = distance
        distance += step

    return max(0.1, last_good)


def _automation_node_edges(floor_entries, obstacle_entries, center, side, default_half_width, spacing):
    left_distance = _automation_side_floor_distance(
        floor_entries,
        obstacle_entries,
        center,
        side,
        default_half_width,
        spacing,
    )
    right_distance = _automation_side_floor_distance(
        floor_entries,
        obstacle_entries,
        center,
        -side,
        default_half_width,
        spacing,
    )
    left = center + side * left_distance
    right = center - side * right_distance
    left_floor = _project_point_to_collision_floor_near(floor_entries, left, height=3.0)
    right_floor = _project_point_to_collision_floor_near(floor_entries, right, height=3.0)
    if left_floor is not None:
        left = left_floor
    if right_floor is not None:
        right = right_floor
    return left, right


def _midpoint_around_collision(floor_entries, obstacle_entries, start, end, spacing):
    midpoint = (start + end) * 0.5
    delta = end - start
    horizontal = BlenderVector((delta.x, delta.y, 0.0))
    if horizontal.length <= 0.000001:
        candidates = [midpoint]
    else:
        horizontal.normalize()
        side = BlenderVector((-horizontal.y, horizontal.x, 0.0))
        offsets = [0.0, spacing * 0.5, -spacing * 0.5, spacing, -spacing, spacing * 1.5, -spacing * 1.5]
        candidates = [midpoint + side * offset for offset in offsets]

    best = None
    for candidate in candidates:
        floor = _project_point_to_collision_floor_near(floor_entries, candidate)
        if floor is None:
            continue
        blocked = _collision_segment_blocked(obstacle_entries, start, floor) or _collision_segment_blocked(obstacle_entries, floor, end)
        penalty = 1000.0 if blocked else 0.0
        score = penalty + (floor - midpoint).length_squared
        if best is None or score < best[0]:
            best = (score, floor, blocked)
    if best and not best[2]:
        return best[1]
    return None


def _refine_collision_path(floor_entries, obstacle_entries, points, spacing, closed=True):
    if len(points) < 2:
        return points

    refined = []
    segment_count = len(points) if closed else len(points) - 1
    for i in range(segment_count):
        start = points[i]
        end = points[(i + 1) % len(points)]
        if not refined:
            refined.append(start)

        stack = [(start, end, 0)]
        segment_points = []
        while stack:
            a, b, depth = stack.pop()
            length = (b - a).length
            blocked = _collision_segment_blocked(obstacle_entries, a, b)
            too_long = length > spacing
            if (too_long or blocked) and depth < 4:
                midpoint = None
                if blocked:
                    midpoint = _midpoint_around_collision(floor_entries, obstacle_entries, a, b, spacing)
                if midpoint is None and too_long:
                    midpoint = _project_point_to_collision_floor_near(floor_entries, (a + b) * 0.5)
                if midpoint is not None and (midpoint - a).length > 0.05 and (midpoint - b).length > 0.05:
                    stack.append((midpoint, b, depth + 1))
                    stack.append((a, midpoint, depth + 1))
                    continue
            if not closed or not refined or (b - refined[0]).length > 0.05:
                segment_points.append(b)

        refined.extend(segment_points)

    return _dedupe_path_points(refined, threshold=0.05, closed=closed)


def _smooth_collision_path(floor_entries, obstacle_entries, points, spacing, closed=True):
    if len(points) < 3:
        return points

    smoothed = list(points)
    iterations = 1
    for _iteration in range(iterations):
        next_points = list(smoothed)
        start = 0 if closed else 1
        end = len(smoothed) if closed else len(smoothed) - 1
        for i in range(start, end):
            prev_point = smoothed[(i - 1) % len(smoothed)]
            point = smoothed[i]
            next_point = smoothed[(i + 1) % len(smoothed)]
            incoming = point - prev_point
            outgoing = next_point - point
            incoming.z = 0.0
            outgoing.z = 0.0
            if incoming.length > 0.000001 and outgoing.length > 0.000001:
                incoming.normalize()
                outgoing.normalize()
                if incoming.dot(outgoing) < 0.75:
                    continue
            candidate = point.lerp((prev_point + next_point) * 0.5, 0.22)
            floor = _project_point_to_collision_floor_near(floor_entries, candidate, height=2.5)
            if floor is None:
                continue
            original_length = (point - prev_point).length + (next_point - point).length
            candidate_length = (floor - prev_point).length + (next_point - floor).length
            if candidate_length > original_length * 1.05:
                continue
            if not _collision_path_segment_clear(floor_entries, obstacle_entries, prev_point, floor, spacing):
                continue
            if not _collision_path_segment_clear(floor_entries, obstacle_entries, floor, next_point, spacing):
                continue
            next_points[i] = floor
        smoothed = next_points

    return smoothed


def _find_ai_append_tail(scene, first_center, spacing):
    tails = []
    for obj in _ai_primary_nodes(scene):
        connections = _ai_connections(obj)
        if connections[2] >= 0 or connections[3] >= 0:
            continue
        tails.append(obj)

    candidates = tails or _ai_primary_nodes(scene)
    if not candidates:
        return None, False

    max_distance = max(2.0, spacing * 1.5)
    best = min(
        candidates,
        key=lambda obj: (_ai_node_center_world(obj) - first_center).length_squared,
    )
    distance = (_ai_node_center_world(best) - first_center).length
    if distance > max_distance:
        return None, False
    return best, distance < max(0.75, spacing * 0.35)


def _mark_selected_mesh_ai_path_endpoint(context, marker, label):
    obj = context.view_layer.objects.active
    if obj is None or obj.type != "MESH" or context.mode != "EDIT_MESH":
        return False, f"Select one {label.lower()} face on a mesh in Edit Mode."

    bm = bmesh.from_edit_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    bm.faces.index_update()
    selected_faces = [face for face in bm.faces if face.select]
    if len(selected_faces) != 1:
        return False, f"Select exactly one face before marking the {label.lower()}."
    selected_index = selected_faces[0].index

    layer = bm.faces.layers.int.get(AI_SELECTED_PATH_MARK_LAYER)
    if layer is None:
        layer = bm.faces.layers.int.new(AI_SELECTED_PATH_MARK_LAYER)
        bm.faces.ensure_lookup_table()

    for face in bm.faces:
        if face[layer] == marker:
            face[layer] = 0

    bm.faces.ensure_lookup_table()
    bm.faces[selected_index][layer] = marker
    bmesh.update_edit_mesh(obj.data)
    obj["ai_selected_path_has_markers"] = True
    return True, f"Marked {label.lower()} face."


def _selected_mesh_ai_path_endpoints(bm, selected_indices):
    layer = bm.faces.layers.int.get(AI_SELECTED_PATH_MARK_LAYER)
    if layer is None:
        return None, None

    start_index = None
    end_index = None
    for face in bm.faces:
        marker = int(face[layer])
        if marker == AI_SELECTED_PATH_START:
            start_index = face.index
        elif marker == AI_SELECTED_PATH_END:
            end_index = face.index

    if start_index not in selected_indices:
        start_index = None
    if end_index not in selected_indices:
        end_index = None
    return start_index, end_index


class MarkAISelectedPathStart(bpy.types.Operator):
    bl_idname = "scene.mark_ai_selected_path_start"
    bl_label = "Starting Node"
    bl_description = "Mark the currently selected mesh face as the start for AI Nodes to Selected"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        ok, message = _mark_selected_mesh_ai_path_endpoint(
            context,
            AI_SELECTED_PATH_START,
            "Starting Node",
        )
        self.report({'INFO'} if ok else {'WARNING'}, message)
        return {'FINISHED'} if ok else {'CANCELLED'}


class MarkAISelectedPathEnd(bpy.types.Operator):
    bl_idname = "scene.mark_ai_selected_path_end"
    bl_label = "Ending Node"
    bl_description = "Mark the currently selected mesh face as the end for AI Nodes to Selected"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        ok, message = _mark_selected_mesh_ai_path_endpoint(
            context,
            AI_SELECTED_PATH_END,
            "Ending Node",
        )
        self.report({'INFO'} if ok else {'WARNING'}, message)
        return {'FINISHED'} if ok else {'CANCELLED'}


def _selected_mesh_ai_path_data(context, spacing):
    obj = context.view_layer.objects.active
    if obj is None or obj.type != "MESH" or context.mode != "EDIT_MESH":
        return None, "Select a road mesh in Edit Mode and select the floor faces for this AI path."

    bm = bmesh.from_edit_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    bm.faces.index_update()
    selected_faces = [face for face in bm.faces if face.select]
    if len(selected_faces) < 2:
        return None, "Select at least two connected floor faces."

    selected_indices = {face.index for face in selected_faces}
    start_index, end_index = _selected_mesh_ai_path_endpoints(bm, selected_indices)
    if start_index is None or end_index is None:
        return None, "Mark one selected face as Starting Node and one as Ending Node before running AI Nodes to Selected."
    if start_index == end_index:
        return None, "Starting Node and Ending Node must be different faces."

    face_by_index = {face.index: face for face in selected_faces}
    world = obj.matrix_world
    centers = {}
    face_vertices = {}
    for face in selected_faces:
        center = world @ face.calc_center_median()
        centers[face.index] = center
        face_vertices[face.index] = [world @ vert.co for vert in face.verts]

    neighbors = {index: set() for index in selected_indices}
    edge_lengths = []
    for face in selected_faces:
        face_index = face.index
        for edge in face.edges:
            edge_lengths.append((world @ edge.verts[0].co - world @ edge.verts[1].co).length)
            for linked in edge.link_faces:
                linked_index = linked.index
                if linked_index == face_index or linked_index not in selected_indices:
                    continue
                neighbors[face_index].add(linked_index)
        for vert in face.verts:
            for linked in vert.link_faces:
                linked_index = linked.index
                if linked_index == face_index or linked_index not in selected_indices:
                    continue
                neighbors[face_index].add(linked_index)

    def walk_distances():
        distances = {end_index: 0.0}
        queue = [(0.0, end_index)]
        while queue:
            distance, face_index = heapq.heappop(queue)
            if distance > distances.get(face_index, float("inf")) + 0.000001:
                continue
            for linked_index in neighbors[face_index]:
                step = (centers[linked_index] - centers[face_index]).length
                new_distance = distance + step
                if new_distance + 0.000001 < distances.get(linked_index, float("inf")):
                    distances[linked_index] = new_distance
                    heapq.heappush(queue, (new_distance, linked_index))
        return distances

    distances = walk_distances()
    if start_index not in distances:
        avg_edge = sum(edge_lengths) / len(edge_lengths) if edge_lengths else 0.25
        bridge_distance = max(0.12, min(1.0, avg_edge * 1.5))
        ordered_indices = sorted(selected_indices)
        for pos, first_index in enumerate(ordered_indices):
            first_points = face_vertices[first_index]
            for second_index in ordered_indices[pos + 1:]:
                if second_index in neighbors[first_index]:
                    continue
                if (centers[first_index] - centers[second_index]).length > max(bridge_distance * 3.0, 0.5):
                    continue
                second_points = face_vertices[second_index]
                closest = min((a - b).length for a in first_points for b in second_points)
                if closest <= bridge_distance:
                    neighbors[first_index].add(second_index)
                    neighbors[second_index].add(first_index)
        distances = walk_distances()
    if start_index not in distances:
        avg_edge = sum(edge_lengths) / len(edge_lengths) if edge_lengths else 0.5
        max_bridge_distance = max(2.0, min(8.0, spacing * 1.6, avg_edge * 16.0))

        def components():
            remaining = set(selected_indices)
            result = []
            while remaining:
                root = remaining.pop()
                component = {root}
                stack = [root]
                while stack:
                    current = stack.pop()
                    for linked in neighbors[current]:
                        if linked in remaining:
                            remaining.remove(linked)
                            component.add(linked)
                            stack.append(linked)
                result.append(component)
            return result

        for _attempt in range(len(selected_indices)):
            comps = components()
            if len(comps) <= 1:
                break
            reachable = set(walk_distances())
            if start_index in reachable:
                distances = walk_distances()
                break
            reachable_comps = [comp for comp in comps if comp & reachable]
            other_comps = [comp for comp in comps if not comp & reachable]
            if not reachable_comps or not other_comps:
                break
            best = None
            for first_comp in reachable_comps:
                for second_comp in other_comps:
                    for first_index in first_comp:
                        for second_index in second_comp:
                            center_distance = (centers[first_index] - centers[second_index]).length
                            if center_distance > max_bridge_distance * 1.75:
                                continue
                            vertex_distance = min(
                                (a - b).length
                                for a in face_vertices[first_index]
                                for b in face_vertices[second_index]
                            )
                            distance = min(center_distance, vertex_distance)
                            if best is None or distance < best[0]:
                                best = (distance, first_index, second_index)
            if best is None or best[0] > max_bridge_distance:
                break
            _distance, first_index, second_index = best
            neighbors[first_index].add(second_index)
            neighbors[second_index].add(first_index)
            distances = walk_distances()

    reachable_indices = [face.index for face in selected_faces if face.index in distances]
    if start_index not in distances:
        return None, "The marked Starting Node face is not connected to the marked Ending Node face through the selected faces. Select the missing bridge faces too, or mark start/end on the same selected mesh island."

    max_distance = distances[start_index]
    route_indices = [
        index for index in reachable_indices
        if distances[index] <= max_distance + 0.000001
    ]
    sample_spacing = max(0.45, spacing * 0.55)
    sample_count = max(2, int(math.ceil(max_distance / sample_spacing)) + 1)
    path = [centers[start_index]]
    for sample_index in range(1, sample_count):
        target_distance = max_distance - min(max_distance, sample_index * sample_spacing)
        window = max(sample_spacing * 0.6, 0.35)
        bucket = [
            index for index in route_indices
            if abs(distances[index] - target_distance) <= window
        ]
        if not bucket:
            bucket = [min(route_indices, key=lambda index: abs(distances[index] - target_distance))]
        point = BlenderVector((0.0, 0.0, 0.0))
        total_weight = 0.0
        for index in bucket:
            weight = 1.0 / (0.15 + abs(distances[index] - target_distance))
            point += centers[index] * weight
            total_weight += weight
        if total_weight > 0.0:
            point /= total_weight
        if not path or (point - path[-1]).length >= 0.12:
            path.append(point)

    end_center = centers[end_index]
    if path and (path[-1] - end_center).length > 0.12:
        path.append(end_center)

    route_samples = [
        (distances[index], point)
        for index in route_indices
        for point in face_vertices[index]
    ]
    return {
        "object": obj,
        "path": _dedupe_path_points(path, threshold=0.12, closed=False),
        "route_samples": route_samples,
        "ignored": len(selected_faces) - len(route_indices),
    }, None


def _selected_mesh_node_edges(center, tangent, route_samples, route_distance, default_half_width, spacing):
    horizontal = BlenderVector((tangent.x, tangent.y, 0.0))
    if horizontal.length <= 0.000001:
        horizontal = BlenderVector((1.0, 0.0, 0.0))
    horizontal.normalize()
    side = BlenderVector((-horizontal.y, horizontal.x, 0.0))
    longitudinal_window = max(0.75, spacing * 0.55)
    distance_window = max(0.75, spacing * 0.65)
    positive = []
    negative = []
    fallback = []
    for sample_distance, point in route_samples:
        route_delta = abs(sample_distance - route_distance)
        if route_delta > distance_window:
            continue
        delta = point - center
        flat = BlenderVector((delta.x, delta.y, 0.0))
        if abs(flat.dot(horizontal)) > longitudinal_window:
            continue
        side_distance = flat.dot(side)
        fallback.append((route_delta, abs(flat.dot(horizontal)), side_distance))
        if side_distance >= 0.0:
            positive.append(side_distance)
        else:
            negative.append(-side_distance)

    if not positive or not negative:
        candidates = []
        for sample_distance, point in route_samples:
            delta = point - center
            flat = BlenderVector((delta.x, delta.y, 0.0))
            route_delta = abs(sample_distance - route_distance)
            if route_delta <= distance_window * 1.75:
                candidates.append((route_delta, abs(flat.dot(horizontal)), flat.dot(side)))
        candidates.sort(key=lambda item: item[0])
        for _route_delta, _longitudinal, side_distance in candidates[:24]:
            if side_distance >= 0.0:
                positive.append(side_distance)
            else:
                negative.append(-side_distance)

    left_distance = max(positive) if positive else default_half_width
    right_distance = max(negative) if negative else default_half_width
    max_side_distance = max(default_half_width * 1.4, min(spacing * 0.42, default_half_width * 3.0))
    left_distance = max(0.15, min(left_distance, max_side_distance))
    right_distance = max(0.15, min(right_distance, max_side_distance))
    return center + side * left_distance, center - side * right_distance


def _selected_ai_segment_fits(floor_entries, obstacle_entries, left, right):
    if (right - left).length <= 0.25:
        return False
    if not obstacle_entries and not floor_entries:
        return True
    center = (left + right) * 0.5
    if obstacle_entries:
        if _collision_segment_blocked(obstacle_entries, center, left, clearance=0.18):
            return False
        if _collision_segment_blocked(obstacle_entries, center, right, clearance=0.18):
            return False
    if floor_entries:
        left_floor = _project_point_to_collision_floor_near(floor_entries, left, height=2.5)
        right_floor = _project_point_to_collision_floor_near(floor_entries, right, height=2.5)
        if left_floor is None or right_floor is None:
            return False
    return True


def _post_optimize_selected_ai_nodes(
    created,
    centers,
    route_samples,
    center_distances,
    spacing,
    default_half_width,
    floor_entries=None,
    obstacle_entries=None,
):
    if len(created) < 3 or len(created) != len(centers):
        return 0

    floor_entries = floor_entries or []
    obstacle_entries = obstacle_entries or []
    max_center_distance = center_distances[-1] if center_distances else 0.0
    optimized_centers = [point.copy() for point in centers]
    optimized_edges = [_ai_node_left_right_world(obj) for obj in created]
    max_nudge = max(0.25, min(spacing * 0.22, default_half_width * 1.75))
    min_rotation = math.radians(1.5)
    changed = 0

    for _iteration in range(2):
        iteration_edges = list(optimized_edges)
        iteration_centers = [point.copy() for point in optimized_centers]

        for i, obj in enumerate(created):
            current_left, current_right = optimized_edges[i]
            current_center = (current_left + current_right) * 0.5
            current_side = _flat_normalized(current_left - current_center)
            tangent = _automation_path_tangent(optimized_centers, i, False)
            target_side = BlenderVector((-tangent.y, tangent.x, 0.0))
            if target_side.dot(current_side) < 0.0:
                target_side = -target_side

            if _flat_angle_between(current_side, target_side) < min_rotation:
                continue

            best = None
            offsets = (
                0.0,
                max_nudge * 0.35,
                -max_nudge * 0.35,
                max_nudge * 0.7,
                -max_nudge * 0.7,
                max_nudge,
                -max_nudge,
            )
            for offset in offsets:
                candidate_center = centers[i] + tangent * offset
                route_distance = max_center_distance - center_distances[i] if max_center_distance > 0.0 else 0.0
                route_distance = max(0.0, min(max_center_distance, route_distance - offset))
                left, right = _selected_mesh_node_edges(
                    candidate_center,
                    tangent,
                    route_samples,
                    route_distance,
                    default_half_width,
                    spacing,
                )
                if not _selected_ai_segment_fits(floor_entries, obstacle_entries, left, right):
                    continue

                actual_center = (left + right) * 0.5
                movement = (actual_center - centers[i]).length
                if movement > max(spacing * 0.33, default_half_width * 2.0):
                    continue

                old_prev = centers[i - 1] if i > 0 else None
                old_next = centers[i + 1] if i < len(centers) - 1 else None
                old_length = 0.0
                new_length = 0.0
                if old_prev is not None:
                    old_length += (centers[i] - old_prev).length
                    new_length += (actual_center - old_prev).length
                if old_next is not None:
                    old_length += (old_next - centers[i]).length
                    new_length += (old_next - actual_center).length
                width = (right - left).length
                width_penalty = abs(width - float(getattr(obj, "ai_lane_width", obj.get("ai_lane_width", width)))) * 0.2
                score = movement * 1.35 + abs(new_length - old_length) * 0.45 + width_penalty + abs(offset) * 0.15
                if best is None or score < best[0]:
                    best = (score, actual_center, left, right)

            if best is None:
                continue

            _score, actual_center, left, right = best
            iteration_centers[i] = actual_center
            iteration_edges[i] = (left, right)

        optimized_centers = iteration_centers
        optimized_edges = iteration_edges

    for obj, (old_left, old_right), (new_left, new_right) in zip(created, [_ai_node_left_right_world(obj) for obj in created], optimized_edges):
        old_center = (old_left + old_right) * 0.5
        new_center = (new_left + new_right) * 0.5
        old_side = _flat_normalized(old_left - old_center)
        new_side = _flat_normalized(new_left - new_center, fallback=old_side)
        if (new_center - old_center).length <= 0.001 and _flat_angle_between(old_side, new_side) <= min_rotation:
            continue
        if _set_ai_node_world_edges(obj, new_left, new_right):
            changed += 1

    return changed


class GenerateAINodesToSelected(bpy.types.Operator):
    bl_idname = "scene.generate_ai_nodes_to_selected"
    bl_label = "AI Nodes to Selected"
    bl_description = "Create AI nodes along selected mesh faces from the marked start face to the marked end face"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        spacing = AI_NODE_AUTOMATION_SPACING
        width = max(0.01, float(getattr(scene, "ai_nodes_lane_width", 2.0)))
        half_width = width * 0.5
        data, error = _selected_mesh_ai_path_data(context, spacing)
        if error:
            self.report({'WARNING'}, error)
            return {'CANCELLED'}

        centers = data["path"]
        route_samples = data["route_samples"]
        if len(centers) < 2:
            self.report({'WARNING'}, "AI Nodes to Selected could not build a long enough path from the selected mesh.")
            return {'CANCELLED'}

        if context.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")

        selected_route_obj = data.get("object")
        collision_meshes = _collision_mesh_objects(scene)
        floor_meshes = list(collision_meshes)
        if selected_route_obj is not None and selected_route_obj.type == "MESH" and selected_route_obj not in floor_meshes:
            floor_meshes.append(selected_route_obj)
        floor_bvhs = _collision_bvh_entries(context, floor_meshes) if floor_meshes else []
        obstacle_meshes = _automation_obstacle_mesh_objects(scene, collision_meshes) if collision_meshes else []
        obstacle_bvhs = _collision_bvh_entries(context, obstacle_meshes) if obstacle_meshes else []

        centers = _smooth_collision_path([], [], centers, spacing, closed=False)
        collection = ensure_collection()
        existing_nodes = _ai_primary_nodes(scene)
        append_tail, skip_first_center = _find_ai_append_tail(scene, centers[0], spacing)
        create_centers = centers[1:] if append_tail and skip_first_center and len(centers) > 1 else centers
        if not create_centers:
            self.report({'WARNING'}, "AI Nodes to Selected found only an already existing route tail.")
            return {'CANCELLED'}

        created = []
        next_ai_index = _ai_next_index(scene)
        next_display_number = _ai_next_primary_display_number(scene)
        segment_lengths = []
        if append_tail:
            segment_lengths.append((_ai_node_center_world(append_tail) - create_centers[0]).length)
        for i in range(max(0, len(create_centers) - 1)):
            segment_lengths.append((create_centers[i + 1] - create_centers[i]).length)
        total_dist = sum(to_revolt_scale(length) for length in segment_lengths)
        running = 0.0
        center_distances = [0.0]
        for i in range(max(0, len(create_centers) - 1)):
            center_distances.append(center_distances[-1] + (create_centers[i + 1] - create_centers[i]).length)
        max_center_distance = center_distances[-1] if center_distances else 0.0

        for i, center in enumerate(create_centers):
            prev_center = create_centers[i - 1] if i > 0 else (
                _ai_node_center_world(append_tail) if append_tail else create_centers[i]
            )
            next_center = create_centers[i + 1] if i < len(create_centers) - 1 else create_centers[i]
            tangent = next_center - prev_center
            if tangent.length <= 0.000001 and i > 0:
                tangent = center - prev_center
            route_distance = max_center_distance - center_distances[i] if max_center_distance > 0.0 else 0.0
            left, right = _selected_mesh_node_edges(
                center,
                tangent,
                route_samples,
                route_distance,
                half_width,
                spacing,
            )

            node = AiNode()
            node.left_pos = Vector(data=to_revolt_coord(left))
            node.right_pos = Vector(data=to_revolt_coord(right))
            node.racing_ratio = 0.5
            node.overtake_ratio = 0.5
            node.property_type = int(getattr(scene, "ai_nodes_default_property", 0))
            node.start_node = (i == 0 and not existing_nodes and not append_tail)
            node.left_wall_flags = 0x03 if bool(getattr(scene, "ai_nodes_default_left_wall", False)) else 0
            node.right_wall_flags = 0x03 if bool(getattr(scene, "ai_nodes_default_right_wall", False)) else 0
            node.flags = (
                (node.property_type & 0xFF)
                | (0x100 if node.start_node else 0)
                | (node.left_wall_flags << 16)
                | (node.right_wall_flags << 24)
            )
            node.green_speed = 30
            node.red_speed = 30
            node.racing_speed = 30
            node.center_speed = 30
            node.connections = [
                (next_ai_index + i - 1) if i > 0 else (_ai_node_index(append_tail) if append_tail else -1),
                -1,
                (next_ai_index + i + 1) if i < len(create_centers) - 1 else -1,
                -1,
            ]
            node.track_dist = max(0.0, total_dist - running)
            if i < len(segment_lengths):
                running += to_revolt_scale(segment_lengths[i])

            created_obj = create_ai_node_object(
                node=node,
                index=next_ai_index + i,
                collection=collection,
                name=f"AI_{next_display_number + i:03d}",
            )
            created_obj.ai_lane_width = float((right - left).length)
            created.append(created_obj)

        if append_tail and created:
            tail_connections = _ai_connections(append_tail)
            tail_connections[2] = _ai_node_index(created[0])
            _set_ai_connections(append_tail, tail_connections)

        optimized_nodes = _post_optimize_selected_ai_nodes(
            created,
            create_centers,
            route_samples,
            center_distances,
            spacing,
            half_width,
            floor_entries=floor_bvhs,
            obstacle_entries=obstacle_bvhs,
        )
        if optimized_nodes:
            total_dist = _update_created_ai_track_distances(
                scene,
                created,
                append_tail=append_tail,
                closed=False,
            )

        for obj in scene.objects:
            obj.select_set(False)
        for obj in created:
            obj.select_set(True)
        if created:
            context.view_layer.objects.active = created[0]
        rebuild_ai_route_visuals(scene)

        message = f"Created {len(created)} AI nodes from selected mesh faces."
        if data["ignored"]:
            message += f" Ignored {data['ignored']} disconnected selected face(s)."
        if append_tail:
            message += f" Continued from {append_tail.name}."
        if optimized_nodes:
            message += f" Straightened and width-refit {optimized_nodes} node(s)."
        self.report({'INFO'}, message)
        return {'FINISHED'}


class ConnectAINodesByName(bpy.types.Operator):
    bl_idname = "scene.connect_ai_nodes_by_name"
    bl_label = "Connect AI Nodes by Name"
    bl_description = "Connect AI_001 to AI_002 style nodes, including AI_003_001 branch paths"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        nodes = sorted(_ai_node_objects(scene), key=_ai_name_sort_key)
        if len(nodes) < 2:
            self.report({'WARNING'}, "At least two AI nodes are needed.")
            return {'CANCELLED'}

        old_index_to_obj = {_ai_node_index(obj): obj for obj in nodes}
        branch_start_by_obj = {}
        branch_join_by_obj = {}
        for obj in nodes:
            if getattr(obj, "ai_is_secondary_path", obj.get("ai_is_secondary_path", False)):
                old_start_index = int(getattr(obj, "ai_branch_start_index", obj.get("ai_branch_start_index", -1)))
                start_obj = old_index_to_obj.get(old_start_index)
                if start_obj is None:
                    branch_main, _ = _ai_node_name_parts(obj)
                    start_obj = next((candidate for candidate in nodes if _ai_node_name_parts(candidate) == (branch_main, 0)), None)
                branch_start_by_obj[obj] = start_obj
                old_join_index = int(getattr(obj, "ai_branch_join_index", obj.get("ai_branch_join_index", -1)))
                branch_join_by_obj[obj] = old_index_to_obj.get(old_join_index)

        for new_index, obj in enumerate(nodes):
            obj.ai_node_index = new_index
            obj["ai_node_index"] = new_index
            _clear_ai_connections(obj)

        for obj, start_obj in branch_start_by_obj.items():
            if start_obj:
                obj.ai_branch_start_index = _ai_node_index(start_obj)
                obj["ai_branch_start_index"] = _ai_node_index(start_obj)
        for obj, join_obj in branch_join_by_obj.items():
            if join_obj:
                obj.ai_branch_join_index = _ai_node_index(join_obj)
                obj["ai_branch_join_index"] = _ai_node_index(join_obj)

        primaries = _ai_primary_nodes(scene)
        closed = bool(getattr(scene, "ai_nodes_closed_loop", True))
        for idx, obj in enumerate(primaries):
            previous_obj = primaries[idx - 1] if idx > 0 else (primaries[-1] if closed and len(primaries) > 1 else None)
            next_obj = primaries[(idx + 1) % len(primaries)] if idx < len(primaries) - 1 or (closed and len(primaries) > 1) else None
            connections = _ai_connections(obj)
            connections[0] = _ai_node_index(previous_obj) if previous_obj else -1
            connections[2] = _ai_node_index(next_obj) if next_obj else -1
            _set_ai_connections(obj, connections)

        for branch_start in primaries:
            branch_nodes = _ai_branch_nodes(scene, _ai_node_index(branch_start))
            if not branch_nodes:
                continue
            _connect_ai_forward(branch_start, branch_nodes[0], alternate=True)
            for idx in range(len(branch_nodes) - 1):
                _connect_ai_forward(branch_nodes[idx], branch_nodes[idx + 1], alternate=False)

            join_index = int(getattr(branch_nodes[-1], "ai_branch_join_index", branch_nodes[-1].get("ai_branch_join_index", -1)))
            join_target = _ai_node_by_index(scene, join_index)
            if join_target:
                _connect_ai_rejoin(branch_nodes[-1], join_target)

        scene.ai_nodes_start_node = 0
        rebuild_ai_route_visuals(scene)
        self.report({'INFO'}, f"Connected {len(nodes)} AI nodes by name.")
        return {'FINISHED'}


class ConnectAIPathToTarget(bpy.types.Operator):
    bl_idname = "scene.connect_ai_path_to_target"
    bl_label = "Connect Selected"
    bl_description = "Connect exactly two selected AI nodes; the active node is the path target"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        target = context.active_object
        if not target or not (getattr(target, "is_ai_node", False) or target.get("is_ai_node")):
            self.report({'WARNING'}, "Make the target AI node active.")
            return {'CANCELLED'}

        selected_nodes = [
            obj for obj in context.selected_objects
            if getattr(obj, "is_ai_node", False) or obj.get("is_ai_node")
        ]
        if len(selected_nodes) != 2 or target not in selected_nodes:
            self.report({'WARNING'}, "Select exactly two AI nodes. The active node is the target.")
            return {'CANCELLED'}

        source = next(obj for obj in selected_nodes if obj != target)
        _connect_ai_rejoin(source, target)
        rebuild_ai_route_visuals(context.scene)
        self.report({'INFO'}, f"Connected {source.name} to {target.name}.")
        return {'FINISHED'}


class DisconnectAIPathSelected(bpy.types.Operator):
    bl_idname = "scene.disconnect_ai_path_selected"
    bl_label = "Disconnect Selected"
    bl_description = "Disconnect exactly two selected AI nodes from each other"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        active = context.active_object
        selected_nodes = [
            obj for obj in context.selected_objects
            if getattr(obj, "is_ai_node", False) or obj.get("is_ai_node")
        ]
        if len(selected_nodes) != 2 or active not in selected_nodes:
            self.report({'WARNING'}, "Select exactly two AI nodes.")
            return {'CANCELLED'}

        first, second = selected_nodes
        first_index = _ai_node_index(first)
        second_index = _ai_node_index(second)
        disconnected = 0

        first_connections = _ai_connections(first)
        second_connections = _ai_connections(second)
        for slot, value in enumerate(first_connections):
            if value == second_index:
                first_connections[slot] = -1
                disconnected += 1
        for slot, value in enumerate(second_connections):
            if value == first_index:
                second_connections[slot] = -1
                disconnected += 1

        _set_ai_connections(first, first_connections)
        _set_ai_connections(second, second_connections)

        for source, target_index in ((first, second_index), (second, first_index)):
            if int(getattr(source, "ai_branch_join_index", source.get("ai_branch_join_index", -1))) == target_index:
                source.ai_branch_join_index = -1
                source["ai_branch_join_index"] = -1

        rebuild_ai_route_visuals(context.scene)
        if disconnected:
            self.report({'INFO'}, f"Disconnected {first.name} and {second.name}.")
        else:
            self.report({'INFO'}, "Selected AI nodes were not connected.")
        return {'FINISHED'}


class NormalizeAINodeOrigins(bpy.types.Operator):
    bl_idname = "scene.normalize_ai_node_origins"
    bl_label = "Fix AI Node Origins"
    bl_description = "Move AI node object origins to their node centers while preserving visible geometry"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        nodes = _ai_node_objects(context.scene)
        fixed = 0
        for obj in nodes:
            if obj.type != "MESH" or not obj.data or len(obj.data.vertices) < 2:
                continue
            obj["_ai_suppress_geometry_update"] = True
            try:
                world_positions = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
                center = (world_positions[0] + world_positions[1]) * 0.5
                matrix = obj.matrix_world.copy()
                matrix.translation = center
                obj.matrix_world = matrix
                inverse = matrix.inverted()
                obj.data.vertices[0].co = inverse @ world_positions[0]
                obj.data.vertices[1].co = inverse @ world_positions[1]
                _rebuild_ai_node_helper_vertices(obj)
                update_ai_node_handles(obj)
                obj.data.update()
                obj["ai_lane_width"] = float((world_positions[1] - world_positions[0]).length)
            finally:
                obj["_ai_suppress_geometry_update"] = False
            fixed += 1

        rebuild_ai_route_visuals(context.scene)
        self.report({'INFO'}, f"Fixed origins for {fixed} AI nodes.")
        return {'FINISHED'}


def _ai_node_left_right_world(obj):
    if obj.type == "MESH" and obj.data and len(obj.data.vertices) >= 2:
        return (
            obj.matrix_world @ obj.data.vertices[0].co,
            obj.matrix_world @ obj.data.vertices[1].co,
        )
    center = obj.matrix_world.translation.copy()
    half_width = max(0.01, float(getattr(obj, "ai_lane_width", obj.get("ai_lane_width", 2.0)))) * 0.5
    return center + BlenderVector((-half_width, 0.0, 0.0)), center + BlenderVector((half_width, 0.0, 0.0))


def _flat_normalized(vector, fallback=None):
    result = BlenderVector((vector.x, vector.y, 0.0))
    if result.length <= 0.000001:
        return fallback.copy() if fallback is not None else BlenderVector((1.0, 0.0, 0.0))
    result.normalize()
    return result


def _ordered_ai_overtake_nodes(scene, nodes):
    by_index = {}
    for obj in nodes:
        by_index.setdefault(_ai_node_index(obj), obj)
    if not by_index:
        return []

    indices = set(by_index)
    starts = []
    for index, obj in by_index.items():
        connections = _ai_connections(obj)
        if connections[0] not in indices and connections[1] not in indices:
            starts.append(index)

    start = min(starts or indices, key=lambda index: _ai_name_sort_key(by_index[index]))
    order = []
    visited = set()
    previous = -1
    current = start
    while current in by_index and current not in visited:
        order.append(current)
        visited.add(current)
        connections = _ai_connections(by_index[current])
        next_index = -1
        for slot in (2, 3, 0, 1):
            target = connections[slot]
            if target == previous or target not in indices or target in visited:
                continue
            next_index = target
            break
        previous, current = current, next_index

    for index in sorted(indices - visited, key=lambda value: _ai_name_sort_key(by_index[value])):
        order.append(index)
    return [by_index[index] for index in order]


def _ai_nodes_form_closed_loop(nodes):
    if len(nodes) < 3:
        return False
    first_index = _ai_node_index(nodes[0])
    last_connections = _ai_connections(nodes[-1])
    first_connections = _ai_connections(nodes[0])
    return last_connections[2] == first_index or last_connections[3] == first_index or first_connections[0] == _ai_node_index(nodes[-1])


def _set_ai_overtake_ratio(obj, ratio):
    ratio = max(0.0, min(1.0, float(ratio)))
    obj["_ai_suppress_geometry_update"] = True
    try:
        obj.ai_overtake_ratio = ratio
        obj["ai_overtake_ratio"] = ratio
        _rebuild_ai_node_helper_vertices(obj)
        update_ai_node_handles(obj)
    finally:
        obj["_ai_suppress_geometry_update"] = False


def _ai_path_offset_index(index, offset, count, closed):
    target = index + offset
    if closed:
        return target % count
    if target < 0 or target >= count:
        return None
    return target


def _ai_lookahead_turn_score(centers, index, lookahead, closed):
    count = len(centers)
    if count < 3:
        return 0.0

    prev_i = _ai_path_offset_index(index, -1, count, closed)
    next_i = _ai_path_offset_index(index, 1, count, closed)
    if prev_i is None:
        prev_i = index
    if next_i is None:
        next_i = index

    tangent = _flat_normalized(centers[next_i] - centers[prev_i])
    heading = BlenderVector((0.0, 0.0, 0.0))
    max_step = min(max(1, int(lookahead)), count - 1)
    for step in range(1, max_step + 1):
        target_i = _ai_path_offset_index(index, step, count, closed)
        if target_i is None:
            break
        chord = centers[target_i] - centers[index]
        flat_chord = BlenderVector((chord.x, chord.y, 0.0))
        if flat_chord.length <= 0.000001:
            continue
        weight = step / max_step
        heading += flat_chord.normalized() * weight

    future = _flat_normalized(heading, fallback=tangent)
    cross = tangent.x * future.y - tangent.y * future.x
    dot = max(-1.0, min(1.0, tangent.dot(future)))
    return math.atan2(cross, dot)


def _ai_smoothed_overtake_sides(turn_scores, min_angle, smoothing_span, closed):
    count = len(turn_scores)
    if count == 0:
        return [], 0

    smoothing_span = max(0, int(smoothing_span))
    smoothed = []
    for i in range(count):
        total = 0.0
        weight_total = 0.0
        for offset in range(-smoothing_span, smoothing_span + 1):
            target_i = _ai_path_offset_index(i, offset, count, closed)
            if target_i is None:
                continue
            weight = smoothing_span + 1 - abs(offset)
            total += turn_scores[target_i] * weight
            weight_total += weight
        smoothed.append(total / weight_total if weight_total > 0.0 else turn_scores[i])

    threshold = max(0.001, float(min_angle))
    active_count = sum(1 for score in smoothed if abs(score) >= threshold)
    if active_count == 0:
        return [0.0 for _score in smoothed], 0

    sides = [0.0 for _score in smoothed]
    start = max(range(count), key=lambda idx: abs(smoothed[idx])) if closed else 0
    current_side = 1.0 if closed and smoothed[start] >= 0.0 else (-1.0 if closed else 0.0)
    order = [((start + step) % count) for step in range(count)] if closed else list(range(count))
    for i in order:
        if abs(smoothed[i]) >= threshold:
            current_side = 1.0 if smoothed[i] > 0.0 else -1.0
        sides[i] = current_side

    if not closed:
        first_side = next((side for side in sides if side != 0.0), 0.0)
        if first_side != 0.0:
            for i, side in enumerate(sides):
                if side != 0.0:
                    break
                sides[i] = first_side

    return sides, active_count


AI_OVERTAKE_CENTER_TO_SIDE_FRACTION = 0.20


class AutomateAIOvertakeLine(bpy.types.Operator):
    bl_idname = "scene.automate_ai_overtake_line"
    bl_label = "Automated Overtake Line"
    bl_description = "Build an overtake line that follows the centered racing line on the side suggested by upcoming path direction"
    bl_options = {'REGISTER', 'UNDO'}

    strength: FloatProperty(
        name="Strength",
        description="Scales the 20% center-to-side offset used for the generated overtake line",
        default=1.0,
        min=0.0,
        max=1.0,
        soft_min=0.0,
        soft_max=1.0,
    )
    straight_extension: IntProperty(
        name="Side Smoothing",
        description="How many nearby nodes are blended to avoid rapid left/right side changes",
        default=4,
        min=1,
        max=16,
    )
    lookahead_nodes: IntProperty(
        name="Lookahead Nodes",
        description="How many upcoming AI nodes are used to choose the overtake side",
        default=15,
        min=2,
        max=64,
    )
    corner_angle: FloatProperty(
        name="Min Direction Change",
        description="Small lookahead direction changes below this angle keep the current overtake side",
        default=12.0,
        min=1.0,
        max=89.0,
    )

    def execute(self, context):
        scene = context.scene
        selected_nodes = [
            obj for obj in context.selected_objects
            if getattr(obj, "is_ai_node", False) or obj.get("is_ai_node")
        ]
        use_selected = len(selected_nodes) >= 3
        source_nodes = selected_nodes if use_selected else _ai_primary_nodes(scene)
        nodes = _ordered_ai_overtake_nodes(scene, source_nodes)
        if len(nodes) < 3:
            self.report({'WARNING'}, "Select at least three AI nodes, or create a primary AI route first.")
            return {'CANCELLED'}

        closed = (not use_selected) and _ai_nodes_form_closed_loop(nodes)
        centers = [_ai_node_center_world(obj) for obj in nodes]
        min_angle = math.radians(float(self.corner_angle))
        lookahead = max(2, int(self.lookahead_nodes))
        smoothing_span = max(0, int(self.straight_extension))
        turn_scores = [
            _ai_lookahead_turn_score(centers, i, lookahead, closed)
            for i in range(len(nodes))
        ]
        overtake_sides, direction_count = _ai_smoothed_overtake_sides(
            turn_scores,
            min_angle,
            smoothing_span,
            closed,
        )

        if direction_count == 0:
            self.report({'WARNING'}, f"No lookahead direction changes exceeded {self.corner_angle:.1f} degrees.")
            return {'CANCELLED'}

        center_to_side_ratio_distance = 0.5
        max_ratio_offset = (
            max(0.0, min(1.0, float(self.strength)))
            * center_to_side_ratio_distance
            * AI_OVERTAKE_CENTER_TO_SIDE_FRACTION
        )
        changed = 0
        for i, obj in enumerate(nodes):
            prev_i = (i - 1) % len(nodes) if closed or i > 0 else i
            next_i = (i + 1) % len(nodes) if closed or i < len(nodes) - 1 else i
            tangent = _flat_normalized(centers[next_i] - centers[prev_i])
            geom_left = BlenderVector((-tangent.y, tangent.x, 0.0))
            left, right = _ai_node_left_right_world(obj)
            center = centers[i]
            green_side = _flat_normalized(left - center, fallback=geom_left)
            green_is_geom_left = 1.0 if green_side.dot(geom_left) >= 0.0 else -1.0
            side = overtake_sides[i]
            if side == 0.0:
                target_ratio = 0.5
            else:
                target_ratio = 0.5 - green_is_geom_left * side * max_ratio_offset
            target_ratio = max(0.03, min(0.97, target_ratio))
            old_ratio = float(getattr(obj, "ai_overtake_ratio", obj.get("ai_overtake_ratio", 0.5)))
            if abs(old_ratio - target_ratio) > 0.0001:
                changed += 1
            _set_ai_overtake_ratio(obj, target_ratio)

        rebuild_ai_route_visuals(scene)
        scope = "selected" if use_selected else "primary"
        self.report({'INFO'}, f"Automated overtake line on {len(nodes)} {scope} AI nodes using {lookahead}-node lookahead; changed {changed}.")
        return {'FINISHED'}


def _flat_angle_between(first, second):
    first = _flat_normalized(first)
    second = _flat_normalized(second)
    cross = first.x * second.y - first.y * second.x
    dot = max(-1.0, min(1.0, first.dot(second)))
    return abs(math.atan2(cross, dot))


def _automation_path_tangent(points, index, closed):
    count = len(points)
    if count < 2:
        return BlenderVector((1.0, 0.0, 0.0))

    far_prev = _ai_path_offset_index(index, -2, count, closed)
    far_next = _ai_path_offset_index(index, 2, count, closed)
    near_prev = _ai_path_offset_index(index, -1, count, closed)
    near_next = _ai_path_offset_index(index, 1, count, closed)

    if far_prev is None:
        far_prev = near_prev
    if far_next is None:
        far_next = near_next

    tangent = BlenderVector((0.0, 0.0, 0.0))
    if far_prev is not None and far_next is not None:
        tangent += (points[far_next] - points[far_prev]) * 1.35
    if near_prev is not None and near_next is not None:
        tangent += points[near_next] - points[near_prev]
    elif near_next is not None:
        tangent += points[near_next] - points[index]
    elif near_prev is not None:
        tangent += points[index] - points[near_prev]

    tangent.z = 0.0
    if tangent.length <= 0.000001:
        return BlenderVector((1.0, 0.0, 0.0))
    tangent.normalize()
    return tangent


def _set_ai_node_world_edges(obj, left, right):
    if obj.type != "MESH" or not obj.data or len(obj.data.vertices) < 2:
        return False

    center = (left + right) * 0.5
    matrix = obj.matrix_world.copy()
    matrix.translation = center

    obj["_ai_suppress_geometry_update"] = True
    try:
        obj.matrix_world = matrix
        inverse = matrix.inverted_safe()
        obj.data.vertices[0].co = inverse @ left
        obj.data.vertices[1].co = inverse @ right
        _rebuild_ai_node_helper_vertices(obj)
        obj.data.update()
        width = float((right - left).length)
        obj.ai_lane_width = width
        obj["ai_lane_width"] = width
        update_ai_node_handles(obj)
    finally:
        obj["_ai_suppress_geometry_update"] = False
    return True


def _automation_segment_fits(floor_entries, obstacle_entries, left, right):
    center = (left + right) * 0.5
    if (right - left).length <= 0.25:
        return False
    if _collision_segment_blocked(obstacle_entries, center, left, clearance=0.18):
        return False
    if _collision_segment_blocked(obstacle_entries, center, right, clearance=0.18):
        return False
    left_floor = _project_point_to_collision_floor_near(floor_entries, left, height=2.5)
    right_floor = _project_point_to_collision_floor_near(floor_entries, right, height=2.5)
    return left_floor is not None and right_floor is not None


def _post_optimize_automated_ai_nodes(
    floor_entries,
    obstacle_entries,
    created,
    centers,
    spacing,
    default_half_width,
    closed,
):
    if len(created) < 3 or len(created) != len(centers):
        return 0

    optimized_centers = [point.copy() for point in centers]
    optimized_edges = [_ai_node_left_right_world(obj) for obj in created]
    max_nudge = max(0.25, min(spacing * 0.22, default_half_width * 1.75))
    min_rotation = math.radians(1.5)
    changed = 0

    for _iteration in range(2):
        iteration_edges = list(optimized_edges)
        iteration_centers = [point.copy() for point in optimized_centers]

        for i, obj in enumerate(created):
            current_left, current_right = optimized_edges[i]
            current_center = (current_left + current_right) * 0.5
            current_side = _flat_normalized(current_left - current_center)
            tangent = _automation_path_tangent(optimized_centers, i, closed)
            target_side = BlenderVector((-tangent.y, tangent.x, 0.0))
            if target_side.dot(current_side) < 0.0:
                target_side = -target_side

            if _flat_angle_between(current_side, target_side) < min_rotation:
                continue

            best = None
            offsets = (
                0.0,
                max_nudge * 0.35,
                -max_nudge * 0.35,
                max_nudge * 0.7,
                -max_nudge * 0.7,
                max_nudge,
                -max_nudge,
            )
            for offset in offsets:
                candidate_center = optimized_centers[i] + tangent * offset
                floor_center = _project_point_to_collision_floor_near(floor_entries, candidate_center, height=3.0)
                if floor_center is None:
                    continue

                left, right = _automation_node_edges(
                    floor_entries,
                    obstacle_entries,
                    floor_center,
                    target_side,
                    default_half_width,
                    spacing,
                )
                if not _automation_segment_fits(floor_entries, obstacle_entries, left, right):
                    continue

                actual_center = (left + right) * 0.5
                movement = (actual_center - centers[i]).length
                if movement > max(spacing * 0.33, default_half_width * 2.0):
                    continue

                width = (right - left).length
                old_prev = centers[i - 1] if i > 0 else (centers[-1] if closed else None)
                old_next = centers[(i + 1) % len(centers)] if closed or i < len(centers) - 1 else None
                old_length = 0.0
                new_length = 0.0
                if old_prev is not None:
                    old_length += (centers[i] - old_prev).length
                    new_length += (actual_center - old_prev).length
                if old_next is not None:
                    old_length += (old_next - centers[i]).length
                    new_length += (old_next - actual_center).length
                length_penalty = abs(new_length - old_length)
                width_penalty = abs(width - float(getattr(obj, "ai_lane_width", obj.get("ai_lane_width", width)))) * 0.2
                score = movement * 1.35 + length_penalty * 0.45 + width_penalty + abs(offset) * 0.15
                if best is None or score < best[0]:
                    best = (score, actual_center, left, right)

            if best is None:
                continue

            _score, actual_center, left, right = best
            iteration_centers[i] = actual_center
            iteration_edges[i] = (left, right)

        optimized_centers = iteration_centers
        optimized_edges = iteration_edges

    for obj, (old_left, old_right), (new_left, new_right) in zip(created, [_ai_node_left_right_world(obj) for obj in created], optimized_edges):
        old_center = (old_left + old_right) * 0.5
        new_center = (new_left + new_right) * 0.5
        old_side = _flat_normalized(old_left - old_center)
        new_side = _flat_normalized(new_left - new_center, fallback=old_side)
        if (new_center - old_center).length <= 0.001 and _flat_angle_between(old_side, new_side) <= min_rotation:
            continue
        if _set_ai_node_world_edges(obj, new_left, new_right):
            changed += 1

    return changed


def _update_created_ai_track_distances(scene, created, append_tail=None, closed=False):
    if not created:
        scene.ai_nodes_total_dist = 0.0
        return 0.0

    segment_lengths = []
    if append_tail:
        segment_lengths.append((_ai_node_center_world(append_tail) - _ai_node_center_world(created[0])).length)

    segment_count = len(created) if closed else len(created) - 1
    for i in range(max(0, segment_count)):
        start = _ai_node_center_world(created[i])
        end = _ai_node_center_world(created[(i + 1) % len(created)])
        segment_lengths.append((end - start).length)

    total_dist = sum(to_revolt_scale(length) for length in segment_lengths)
    running = 0.0
    for i, obj in enumerate(created):
        obj.ai_track_dist = max(0.0, total_dist - running)
        obj["ai_track_dist"] = float(obj.ai_track_dist)
        if i < len(segment_lengths):
            running += to_revolt_scale(segment_lengths[i])

    scene.ai_nodes_total_dist = float(total_dist)
    return total_dist


class GenerateAINodesFromTrackZones(bpy.types.Operator):
    bl_idname = "scene.generate_ai_nodes_from_track_zones"
    bl_label = "Automated AI Nodes"
    bl_description = "Create a first-pass AI path from Track Zones projected onto imported .ncp collision meshes"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        all_zones = [
            obj for obj in scene.objects
            if getattr(obj, "is_track_zone", False) or obj.get("is_track_zone")
        ]
        all_zone_ids = {_track_zone_id(obj) for obj in all_zones}
        selected_zones = [
            obj for obj in context.selected_objects
            if getattr(obj, "is_track_zone", False) or obj.get("is_track_zone")
        ]
        selected_zone_ids = {_track_zone_id(obj) for obj in selected_zones}
        zones = sorted(
            [
                obj for obj in selected_zones
            ],
            key=lambda obj: (_track_zone_id(obj), obj.name),
        )
        collision_meshes = _collision_mesh_objects(scene)
        obstacle_meshes = _automation_obstacle_mesh_objects(scene, collision_meshes)

        missing = []
        if len(zones) < 2:
            missing.append("at least two selected TRACK ZONES")
        if not collision_meshes:
            missing.append("an imported .ncp collision mesh")
        if missing:
            self.report({'WARNING'}, "Automated AI Nodes needs " + " and ".join(missing) + ".")
            return {'CANCELLED'}

        collision_bvhs = _collision_bvh_entries(context, collision_meshes)
        if not collision_bvhs:
            self.report({'WARNING'}, "Could not build collision data from the imported .ncp meshes.")
            return {'CANCELLED'}
        obstacle_bvhs = _collision_bvh_entries(context, obstacle_meshes) or collision_bvhs

        collection = ensure_collection()
        existing_nodes = _ai_primary_nodes(scene)
        closed = bool(all_zone_ids) and selected_zone_ids == all_zone_ids and not existing_nodes
        width = max(0.01, float(getattr(scene, "ai_nodes_lane_width", 2.0)))
        spacing = AI_NODE_AUTOMATION_SPACING
        half_width = width * 0.5
        active_zone = context.view_layer.objects.active
        zone_points, missing_floor, ignored_zones = _ordered_selected_track_zone_points(
            collision_bvhs,
            obstacle_bvhs,
            zones,
            active_zone=active_zone,
        )

        if len(zone_points) < 2:
            self.report({'WARNING'}, "Automated AI Nodes could not find enough TRACK ZONES with nearby .ncp floor.")
            return {'CANCELLED'}

        zone_points = _path_corner_support_points(
            collision_bvhs,
            obstacle_bvhs,
            zone_points,
            spacing,
            closed=closed,
        )
        centers = _refine_collision_path(collision_bvhs, obstacle_bvhs, zone_points, spacing, closed=closed)
        centers = _smooth_collision_path(collision_bvhs, obstacle_bvhs, centers, spacing, closed=closed)
        if len(centers) < 2:
            self.report({'WARNING'}, "Automated AI Nodes could not create a usable collision path.")
            return {'CANCELLED'}

        append_tail, skip_first_center = _find_ai_append_tail(scene, centers[0], spacing)
        create_centers = centers[1:] if append_tail and skip_first_center and len(centers) > 1 else centers
        if len(create_centers) < 1:
            self.report({'WARNING'}, "Automated AI Nodes found only an already existing route tail.")
            return {'CANCELLED'}

        count = len(create_centers)
        segment_count = count if closed else count - 1
        blocked_segments = []
        blocked_edges = set()
        segment_lengths = []
        for i in range(segment_count):
            start = create_centers[i]
            end = create_centers[(i + 1) % count]
            if not _collision_path_segment_clear(collision_bvhs, obstacle_bvhs, start, end, spacing):
                blocked_segments.append((i + 1, ((i + 1) % count) + 1))
                blocked_edges.add(i)
            segment_lengths.append((end - start).length)
        if append_tail:
            segment_lengths.insert(0, (_ai_node_center_world(append_tail) - create_centers[0]).length)
        total_dist = sum(to_revolt_scale(length) for length in segment_lengths)

        created = []
        running = 0.0
        next_ai_index = _ai_next_index(scene)
        next_display_number = _ai_next_primary_display_number(scene)
        for i in range(count):
            prev_center = create_centers[(i - 1) % count] if closed or i > 0 else (
                _ai_node_center_world(append_tail) if append_tail else create_centers[i]
            )
            next_center = create_centers[(i + 1) % count] if closed or i < count - 1 else create_centers[i]
            tangent = next_center - prev_center
            tangent.z = 0.0
            if tangent.length <= 0.000001:
                tangent = BlenderVector((1.0, 0.0, 0.0))
            tangent.normalize()
            side = BlenderVector((-tangent.y, tangent.x, 0.0))

            left, right = _automation_node_edges(
                collision_bvhs,
                obstacle_bvhs,
                create_centers[i],
                side,
                half_width,
                spacing,
            )
            node = AiNode()
            node.left_pos = Vector(data=to_revolt_coord(left))
            node.right_pos = Vector(data=to_revolt_coord(right))
            node.racing_ratio = 0.5
            node.overtake_ratio = 0.5
            node.property_type = int(getattr(scene, "ai_nodes_default_property", 0))
            node.start_node = (i == 0 and not existing_nodes and not append_tail)
            node.left_wall_flags = 0x03 if bool(getattr(scene, "ai_nodes_default_left_wall", False)) else 0
            node.right_wall_flags = 0x03 if bool(getattr(scene, "ai_nodes_default_right_wall", False)) else 0
            node.flags = (
                (node.property_type & 0xFF)
                | (0x100 if node.start_node else 0)
                | (node.left_wall_flags << 16)
                | (node.right_wall_flags << 24)
            )
            node.green_speed = 30
            node.red_speed = 30
            node.racing_speed = 30
            node.center_speed = 30
            prev_edge = (i - 1) % count
            next_edge = i
            current_index = next_ai_index + i
            prev_index = (next_ai_index + ((i - 1) % count)) if closed or i > 0 else (
                _ai_node_index(append_tail) if append_tail else -1
            )
            next_index = (next_ai_index + ((i + 1) % count)) if closed or i < count - 1 else -1
            if prev_index >= 0 and prev_edge in blocked_edges:
                prev_index = -1
            if next_index >= 0 and next_edge in blocked_edges:
                next_index = -1
            node.connections = [
                prev_index,
                -1,
                next_index,
                -1,
            ]
            node.track_dist = max(0.0, total_dist - running)
            if i < len(segment_lengths):
                running += to_revolt_scale(segment_lengths[i])

            created_obj = create_ai_node_object(
                node=node,
                index=current_index,
                collection=collection,
                name=f"AI_{next_display_number + i:03d}",
            )
            created_obj.ai_lane_width = float((right - left).length)
            created.append(created_obj)

        if append_tail and created:
            tail_connections = _ai_connections(append_tail)
            tail_connections[2] = _ai_node_index(created[0])
            _set_ai_connections(append_tail, tail_connections)

        optimized_nodes = _post_optimize_automated_ai_nodes(
            collision_bvhs,
            obstacle_bvhs,
            created,
            create_centers,
            spacing,
            half_width,
            closed and not append_tail,
        )
        if optimized_nodes:
            total_dist = _update_created_ai_track_distances(
                scene,
                created,
                append_tail=append_tail,
                closed=closed and not append_tail,
            )

        scene.ai_nodes_start_node = 0 if not existing_nodes else int(getattr(scene, "ai_nodes_start_node", 0))
        scene.ai_nodes_total_dist = float(total_dist)
        scene.ai_nodes_start_factor = 0.5
        for obj in context.scene.objects:
            obj.select_set(False)
        for obj in created:
            obj.select_set(True)
        if created:
            context.view_layer.objects.active = created[0]
        rebuild_ai_route_visuals(scene)
        message = f"Created {len(created)} AI nodes from {len(zone_points)} usable Track Zones and .ncp collision."
        if append_tail:
            message += f" Continued from {append_tail.name}."
        if missing_floor:
            message += f" Skipped {len(missing_floor)} zone(s) without nearby .ncp floor."
        if ignored_zones:
            message += f" Ignored {ignored_zones} selected alternative/gapped zone(s)."
        if blocked_segments:
            message += f" {len(blocked_segments)} direct segment(s) may hit walls."
        if optimized_nodes:
            message += f" Straightened and width-refit {optimized_nodes} node(s)."
        self.report({'INFO'}, message)
        return {'FINISHED'}


class GeneratePosNodesFromTrackZones(bpy.types.Operator):
    bl_idname = "scene.generate_pos_nodes_from_track_zones"
    bl_label = "Automated Pos Nodes"
    bl_description = "Create a first-pass position node path from Track Zones projected onto imported .ncp collision meshes"
    bl_options = {'REGISTER', 'UNDO'}

    def _create_nodes_from_centers(self, context, centers, closed=False):
        scene = context.scene

        collection = ensure_pos_collection()
        existing_nodes = _pos_node_objects(scene)
        selected_nodes = [obj for obj in context.selected_objects if _is_pos_node_object(obj)]
        active = context.view_layer.objects.active
        append_tail = active if active in selected_nodes else (
            selected_nodes[-1] if selected_nodes else (existing_nodes[-1] if existing_nodes else None)
        )
        if not centers:
            self.report({'WARNING'}, "Automated Pos Nodes found only an already existing route tail.")
            return None, append_tail

        next_index = _pos_next_index(scene)
        created = []
        for i, center in enumerate(centers):
            obj = create_pos_node_object(
                index=next_index + i,
                location=center,
                collection=collection,
                name=f"POS_{next_index + i + 1:03d}",
            )
            created.append(obj)

        _connect_pos_chain(created, append_tail=append_tail, closed=closed)
        if created:
            scene.pos_nodes_start_node = _pos_node_index(created[0] if closed and not append_tail else created[-1])

        _update_view_layer(context)
        _recalculate_pos_node_distances(scene)
        for obj in context.scene.objects:
            obj.select_set(False)
        for obj in created:
            obj.select_set(True)
        if created:
            context.view_layer.objects.active = created[0]
        rebuild_pos_route_visuals(scene)
        _update_view_layer(context)
        return created, append_tail

    def _ai_racing_line_points(self, scene):
        points = []
        for obj in _pos_ordered_ai_primary_nodes(scene):
            if obj.type != "MESH" or not obj.data or len(obj.data.vertices) < 2:
                points.append(obj.matrix_world.translation.copy())
                continue
            left = obj.matrix_world @ obj.data.vertices[0].co
            right = obj.matrix_world @ obj.data.vertices[1].co
            ratio = _display_ai_ratio(getattr(obj, "ai_racing_ratio", obj.get("ai_racing_ratio", 0.5)))
            points.append(left.lerp(right, ratio))
        return points

    def execute(self, context):
        scene = context.scene
        ai_nodes = _pos_ordered_ai_primary_nodes(scene)
        ai_points = self._ai_racing_line_points(scene)
        if len(ai_points) >= 2:
            closed = _ai_nodes_form_closed_loop(ai_nodes)
            target_count = max(2, int(round(len(ai_points) * _pos_auto_density(scene))))
            centers = _resample_closed_path_points(ai_points, target_count) if closed else _resample_path_points(ai_points, target_count)
            created, append_tail = self._create_nodes_from_centers(context, centers, closed=closed)
            if created is None:
                return {'CANCELLED'}
            message = f"Created {len(created)} Pos Nodes from AI racing-line points."
            if append_tail:
                message += f" Continued from {append_tail.name}."
            self.report({'INFO'}, message)
            return {'FINISHED'}

        selected_zones = [
            obj for obj in context.selected_objects
            if getattr(obj, "is_track_zone", False) or obj.get("is_track_zone")
        ]
        zones = sorted(selected_zones, key=lambda obj: (_track_zone_id(obj), obj.name))
        spacing = _pos_automation_spacing_distance(scene)

        collision_meshes = _collision_mesh_objects(scene)
        obstacle_meshes = _automation_obstacle_mesh_objects(scene, collision_meshes)

        missing = []
        if len(zones) < 2:
            missing.append("at least two selected TRACK ZONES or two AI nodes")
        if not collision_meshes:
            missing.append("an imported .ncp collision mesh")
        if missing:
            self.report({'WARNING'}, "Automated Pos Nodes needs " + " and ".join(missing) + ".")
            return {'CANCELLED'}

        collision_bvhs = _collision_bvh_entries(context, collision_meshes)
        if not collision_bvhs:
            self.report({'WARNING'}, "Could not build collision data from the imported .ncp meshes.")
            return {'CANCELLED'}
        obstacle_bvhs = _collision_bvh_entries(context, obstacle_meshes) or collision_bvhs

        active_zone = context.view_layer.objects.active
        zone_points, missing_floor, ignored_zones = _ordered_selected_track_zone_points(
            collision_bvhs,
            obstacle_bvhs,
            zones,
            active_zone=active_zone,
        )
        if len(zone_points) < 2:
            self.report({'WARNING'}, "Automated Pos Nodes could not find enough TRACK ZONES with nearby .ncp floor.")
            return {'CANCELLED'}

        zone_points = _path_corner_support_points(
            collision_bvhs,
            obstacle_bvhs,
            zone_points,
            spacing,
            closed=False,
        )
        centers = _refine_collision_path(collision_bvhs, obstacle_bvhs, zone_points, spacing, closed=False)
        centers = _smooth_collision_path(collision_bvhs, obstacle_bvhs, centers, spacing, closed=False)
        if len(centers) < 2:
            self.report({'WARNING'}, "Automated Pos Nodes could not create a usable collision path.")
            return {'CANCELLED'}

        created, append_tail = self._create_nodes_from_centers(context, centers)
        if created is None:
            return {'CANCELLED'}

        message = f"Created {len(created)} Pos Nodes from {len(zone_points)} usable Track Zones and .ncp collision."
        if append_tail:
            message += f" Continued from {append_tail.name}."
        if missing_floor:
            message += f" Skipped {len(missing_floor)} zone(s) without nearby .ncp floor."
        if ignored_zones:
            message += f" Ignored {ignored_zones} selected alternative/gapped zone(s)."
        self.report({'INFO'}, message)
        return {'FINISHED'}


def _ai_node_center_world(obj):
    if obj.type == "MESH" and obj.data and len(obj.data.vertices) >= 2:
        left = obj.matrix_world @ obj.data.vertices[0].co
        right = obj.matrix_world @ obj.data.vertices[1].co
        return (left + right) * 0.5
    return obj.matrix_world.translation.copy()


def _ai_debug_unique(values):
    seen = set()
    result = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _ai_debug_walk(scene, start_index, slot_order=(2, 3, 0, 1)):
    nodes = _ai_node_objects(scene)
    by_index = {_ai_node_index(obj): obj for obj in nodes}
    if start_index not in by_index:
        return []

    order = []
    previous = -1
    current = start_index
    visited = set()
    while current in by_index and current not in visited:
        order.append(current)
        visited.add(current)
        connections = _ai_connections(by_index[current])
        next_index = -1
        for slot in slot_order:
            target = connections[slot]
            if target == previous:
                continue
            if target in by_index:
                next_index = target
                break
        previous, current = current, next_index
    return order


def _ai_debug_walk_text(scene, walk):
    by_index = {_ai_node_index(obj): obj for obj in _ai_node_objects(scene)}
    parts = []
    for index in walk:
        obj = by_index.get(index)
        if obj is None:
            parts.append(str(index))
            continue
        type_id = int(getattr(obj, "ai_property_type", obj.get("ai_property_type", 0)))
        left_wall = int(getattr(obj, "ai_left_wall_flags", obj.get("ai_left_wall_flags", 0)))
        right_wall = int(getattr(obj, "ai_right_wall_flags", obj.get("ai_right_wall_flags", 0)))
        start = "*" if bool(getattr(obj, "ai_start_node", obj.get("ai_start_node", False))) else ""
        parts.append(f"{index}{start}:{obj.name}:T{type_id}:W{left_wall:02X}/{right_wall:02X}")
    return " -> ".join(parts)


def _ai_debug_type_sequence(scene, order, label):
    by_index = {_ai_node_index(obj): obj for obj in _ai_node_objects(scene)}
    parts = []
    for index in order:
        obj = by_index.get(index)
        if obj is None:
            continue
        type_id = int(getattr(obj, "ai_property_type", obj.get("ai_property_type", 0)))
        start = "*" if bool(getattr(obj, "ai_start_node", obj.get("ai_start_node", False))) else ""
        parts.append(f"{index}{start}:T{type_id}")
    return f"  {label}: " + " -> ".join(parts)


def _ai_debug_shifted_type_sequence(scene, order, label, shift):
    by_index = {_ai_node_index(obj): obj for obj in _ai_node_objects(scene)}
    if not order:
        return f"  {label}: "
    parts = []
    count = len(order)
    for pos, index in enumerate(order):
        source_index = order[(pos + shift) % count]
        source_obj = by_index.get(source_index)
        if source_obj is None:
            continue
        type_id = int(getattr(source_obj, "ai_property_type", source_obj.get("ai_property_type", 0)))
        parts.append(f"{index}<=raw{source_index}:T{type_id}")
    return f"  {label}: " + " -> ".join(parts)


def _ai_raw_record_bytes(obj):
    raw_hex = str(obj.get("ai_raw_record_hex", "")).strip()
    if not raw_hex:
        return b""
    try:
        return bytes.fromhex(raw_hex)
    except ValueError:
        return b""


def _ai_raw_field_bytes(obj):
    raw = _ai_raw_record_bytes(obj)
    if len(raw) >= 68:
        return raw[64:68].hex(" ").upper()
    if len(raw) >= 4:
        return raw[0:4].hex(" ").upper()
    return ""


def _ai_property_source(scene, obj):
    source_index = int(obj.get("ai_property_source_index", _ai_node_index(obj)))
    source_obj = _ai_node_by_index(scene, source_index)
    return source_index, source_obj or obj


def _ai_debug_incoming(scene):
    incoming = {}
    for obj in _ai_node_objects(scene):
        source_index = _ai_node_index(obj)
        for slot, target in enumerate(_ai_connections(obj)):
            if target < 0:
                continue
            incoming.setdefault(target, []).append((source_index, slot))
    return incoming


class DumpAINodeDebug(bpy.types.Operator):
    bl_idname = "scene.dump_ai_node_debug"
    bl_label = "Dump AI Node Debug"
    bl_description = "Write a diagnostic AI node ordering table into a Blender text block"
    bl_options = {'REGISTER'}

    def execute(self, context):
        scene = context.scene
        nodes = sorted(_ai_node_objects(scene), key=lambda obj: (_ai_node_index(obj), obj.name))
        if not nodes:
            self.report({'WARNING'}, "No AI node objects found.")
            return {'CANCELLED'}

        incoming = _ai_debug_incoming(scene)
        header_start = int(getattr(scene, "ai_nodes_start_node", scene.get("ai_nodes_start_node", 0)))
        start_flag_indices = [
            _ai_node_index(obj)
            for obj in nodes
            if bool(getattr(obj, "ai_start_node", obj.get("ai_start_node", False)))
        ]
        no_previous_indices = [
            _ai_node_index(obj)
            for obj in nodes
            if not any(slot in {0, 1} for _, slot in incoming.get(_ai_node_index(obj), []))
        ]
        candidates = _ai_debug_unique(start_flag_indices + [header_start] + no_previous_indices + [_ai_node_index(nodes[0])])

        lines = []
        lines.append("AI Node Debug")
        lines.append("=" * 80)
        lines.append(f"Source file: {scene.get('ai_nodes_source_file', '')}")
        lines.append(
            "Header: "
            f"start_node={header_start} "
            f"end_node={int(getattr(scene, 'ai_nodes_end_node', scene.get('ai_nodes_end_node', 0)))} "
            f"header_flags={int(getattr(scene, 'ai_nodes_header_flags', scene.get('ai_nodes_header_flags', 0)))} "
            f"extended_header={bool(scene.get('ai_nodes_has_extended_header', True))}"
        )
        lines.append("")
        lines.append("Candidate route walks (raw file indices):")
        for candidate in candidates:
            label_bits = []
            if candidate in start_flag_indices:
                label_bits.append("start-bit")
            if candidate == header_start:
                label_bits.append("header")
            if candidate in no_previous_indices:
                label_bits.append("no-prev")
            label = ", ".join(label_bits) or "fallback"
            for name, slot_order in (
                ("forward 2/3/0/1", (2, 3, 0, 1)),
                ("forward 0/1/2/3", (0, 1, 2, 3)),
                ("normal 2/0 only", (2, 0)),
                ("normal 0/2 only", (0, 2)),
            ):
                walk = _ai_debug_walk(scene, candidate, slot_order=slot_order)
                lines.append(f"  {candidate:>4} ({label}, {name}): {_ai_debug_walk_text(scene, walk)}")

        distance_order = sorted(
            nodes,
            key=lambda obj: (
                float(getattr(obj, "ai_track_dist", obj.get("ai_track_dist", 0.0))),
                _ai_node_index(obj),
            ),
        )
        lines.append("")
        lines.append(
            "Track-distance order: "
            + " -> ".join(
                f"{_ai_node_index(obj)}({float(getattr(obj, 'ai_track_dist', obj.get('ai_track_dist', 0.0))):.2f})"
                for obj in distance_order
            )
        )

        raw_order = [_ai_node_index(obj) for obj in nodes]
        start_index = start_flag_indices[0] if start_flag_indices else header_start
        slot2_order = _ai_debug_walk(scene, start_index, slot_order=(2, 3, 0, 1))
        slot0_order = _ai_debug_walk(scene, start_index, slot_order=(0, 1, 2, 3))
        lines.append("")
        lines.append("Type order probes:")
        for label, order in (
            ("raw file order", raw_order),
            ("raw file order reversed", list(reversed(raw_order))),
            ("start slot2 order", slot2_order),
            ("start slot0 order", slot0_order),
        ):
            lines.append(_ai_debug_type_sequence(scene, order, label))
            lines.append(_ai_debug_shifted_type_sequence(scene, order, f"{label} with previous raw type", -1))
            lines.append(_ai_debug_shifted_type_sequence(scene, order, f"{label} with next raw type", 1))

        lines.append("")
        lines.append("Nodes sorted by raw ai_node_index:")
        lines.append(
            "raw  name              disp file guess start type vSrc vStart vType vReason          flags       rawField     walls  branch join  ratios(R raw/vis, N next, P pref) connections          incoming       trackDist     center(x,y,z)"
        )
        lines.append("-" * 226)
        for obj in nodes:
            index = _ai_node_index(obj)
            visual_source_index, visual_source = _ai_property_source(scene, obj)
            flags = int(getattr(obj, "ai_flags", obj.get("ai_flags", 0))) & 0xFFFFFFFF
            left_wall = int(getattr(obj, "ai_left_wall_flags", obj.get("ai_left_wall_flags", 0)))
            right_wall = int(getattr(obj, "ai_right_wall_flags", obj.get("ai_right_wall_flags", 0)))
            connections = _ai_connections(obj)
            incoming_text = ",".join(f"{src}:{slot}" for src, slot in incoming.get(index, [])) or "-"
            center = _ai_node_center_world(obj)
            visible_racing = float(getattr(obj, "ai_racing_ratio", obj.get("ai_racing_ratio", 0.5)))
            visible_overtake = float(getattr(obj, "ai_overtake_ratio", obj.get("ai_overtake_ratio", 0.5)))
            raw_racing = obj.get("ai_raw_racing_ratio", visible_racing)
            raw_next_racing = obj.get("ai_raw_next_racing_ratio", visible_overtake)
            ratio_text = f"R{raw_racing:.3f}/{visible_racing:.3f} N{raw_next_racing:.3f} O{visible_overtake:.3f}"
            source_reason = str(obj.get("ai_property_source_reason", "raw"))
            lines.append(
                f"{index:>3}  "
                f"{obj.name:<16} "
                f"{int(obj.get('ai_display_index', -1)):>4} "
                f"{int(obj.get('ai_file_index', index)):>4} "
                f"{int(obj.get('ai_route_guess_index', -1)):>5} "
                f"{'Y' if bool(getattr(obj, 'ai_start_node', obj.get('ai_start_node', False))) else 'N':>5} "
                f"{int(getattr(obj, 'ai_property_type', obj.get('ai_property_type', 0))):>4} "
                f"{visual_source_index:>4} "
                f"{'Y' if bool(getattr(visual_source, 'ai_start_node', visual_source.get('ai_start_node', False))) else 'N':>6} "
                f"{int(getattr(visual_source, 'ai_property_type', visual_source.get('ai_property_type', 0))):>5} "
                f"{source_reason:<16} "
                f"0x{flags:08X}  "
                f"{_ai_raw_field_bytes(obj):<11} "
                f"{left_wall:02X}/{right_wall:02X}  "
                f"{'Y' if bool(getattr(obj, 'ai_is_secondary_path', obj.get('ai_is_secondary_path', False))) else 'N':>6} "
                f"{int(getattr(obj, 'ai_branch_join_index', obj.get('ai_branch_join_index', -1))):>4}  "
                f"{ratio_text:<29} "
                f"{str(connections):<20} "
                f"{incoming_text:<14} "
                f"{float(getattr(obj, 'ai_track_dist', obj.get('ai_track_dist', 0.0))):>10.2f}  "
                f"({center.x:.2f}, {center.y:.2f}, {center.z:.2f})"
            )

        lines.append("")
        lines.append("Raw record bytes:")
        for obj in nodes:
            raw = str(obj.get("ai_raw_record_hex", ""))
            if raw:
                lines.append(f"  raw {_ai_node_index(obj):>3} {obj.name:<16} {raw}")

        text = bpy.data.texts.get("AI Node Debug")
        if text is None:
            text = bpy.data.texts.new("AI Node Debug")
        text.clear()
        text.write("\n".join(lines))
        print("\n".join(lines))
        self.report({'INFO'}, "Wrote AI Node Debug text block.")
        return {'FINISHED'}


def _ai_start_index_for_naming(scene, nodes):
    for obj in nodes:
        if bool(getattr(obj, "ai_start_node", obj.get("ai_start_node", False))):
            return _ai_node_index(obj)

    header_start = int(getattr(scene, "ai_nodes_start_node", scene.get("ai_nodes_start_node", -1)))
    if any(_ai_node_index(obj) == header_start for obj in nodes):
        return header_start

    return min((_ai_node_index(obj) for obj in nodes), default=0)


def _rename_ai_nodes_by_order(scene, order):
    nodes = sorted(_ai_node_objects(scene), key=lambda obj: (_ai_node_index(obj), obj.name))
    by_index = {_ai_node_index(obj): obj for obj in nodes}
    ordered_indices = []
    seen = set()
    for index in order:
        if index in by_index and index not in seen:
            ordered_indices.append(index)
            seen.add(index)
    for index in sorted(by_index):
        if index not in seen:
            ordered_indices.append(index)

    for obj in nodes:
        raw_index = _ai_node_index(obj)
        obj.name = f"AI_RENAME_{raw_index:03d}"
        if obj.data:
            obj.data.name = f"{obj.name}_Mesh"

    for display_index, raw_index in enumerate(ordered_indices):
        obj = by_index[raw_index]
        obj["ai_display_index"] = display_index
        obj["ai_file_index"] = raw_index
        obj["ai_route_guess_index"] = display_index
        obj.name = f"AI_{display_index + 1:03d}"
        if obj.data:
            obj.data.name = f"{obj.name}_Mesh"

    return len(ordered_indices)


class RenameAINodesRawOrder(bpy.types.Operator):
    bl_idname = "scene.rename_ai_nodes_raw_order"
    bl_label = "Name AI Nodes by File Order"
    bl_description = "Rename AI node objects by raw .fan record order without changing indices or export data"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        nodes = sorted(_ai_node_objects(context.scene), key=lambda obj: _ai_node_index(obj))
        if not nodes:
            self.report({'WARNING'}, "No AI node objects found.")
            return {'CANCELLED'}
        count = _rename_ai_nodes_by_order(context.scene, [_ai_node_index(obj) for obj in nodes])
        self.report({'INFO'}, f"Renamed {count} AI nodes by file order.")
        return {'FINISHED'}


class RenameAINodesSlot2Order(bpy.types.Operator):
    bl_idname = "scene.rename_ai_nodes_slot2_order"
    bl_label = "Name AI Nodes by Slot 2 Route"
    bl_description = "Rename AI node objects by walking from the start node with connection slot 2 as next"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        nodes = _ai_node_objects(context.scene)
        if not nodes:
            self.report({'WARNING'}, "No AI node objects found.")
            return {'CANCELLED'}
        start_index = _ai_start_index_for_naming(context.scene, nodes)
        order = _ai_debug_walk(context.scene, start_index, slot_order=(2, 3, 0, 1))
        count = _rename_ai_nodes_by_order(context.scene, order)
        self.report({'INFO'}, f"Renamed {count} AI nodes by slot 2 route.")
        return {'FINISHED'}


class RenameAINodesSlot0Order(bpy.types.Operator):
    bl_idname = "scene.rename_ai_nodes_slot0_order"
    bl_label = "Name AI Nodes by Slot 0 Route"
    bl_description = "Rename AI node objects by walking from the start node with connection slot 0 as next"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        nodes = _ai_node_objects(context.scene)
        if not nodes:
            self.report({'WARNING'}, "No AI node objects found.")
            return {'CANCELLED'}
        start_index = _ai_start_index_for_naming(context.scene, nodes)
        order = _ai_debug_walk(context.scene, start_index, slot_order=(0, 1, 2, 3))
        count = _rename_ai_nodes_by_order(context.scene, order)
        self.report({'INFO'}, f"Renamed {count} AI nodes by slot 0 route.")
        return {'FINISHED'}


class ReverseAINodes(bpy.types.Operator):
    bl_idname = "object.reverse_ai_nodes"
    bl_label = "Reverse AI Nodes"
    bl_description = "Reverse AI node order, links, and green/red sides for reversed tracks"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        nodes = sorted(
            [
                obj for obj in context.scene.objects
                if getattr(obj, "is_ai_node", False) or obj.get("is_ai_node")
            ],
            key=lambda obj: int(getattr(obj, "ai_node_index", obj.get("ai_node_index", 0))),
        )
        if not nodes:
            self.report({'WARNING'}, "No AI node objects found in the scene.")
            return {'CANCELLED'}

        by_index = {
            int(getattr(obj, "ai_node_index", obj.get("ai_node_index", 0))): obj
            for obj in nodes
        }
        reversed_wall_by_index = {}
        for obj in nodes:
            connections = _ai_connections(obj)
            source_index = _ai_node_index(obj)
            wall_target = connections[2] if connections[2] in by_index else connections[3]
            if wall_target not in by_index or wall_target == source_index:
                continue

            left_wall = bool(getattr(obj, "ai_left_wall", obj.get("ai_left_wall", False)))
            right_wall = bool(getattr(obj, "ai_right_wall", obj.get("ai_right_wall", False)))
            left_wall_flags = int(getattr(obj, "ai_left_wall_flags", obj.get("ai_left_wall_flags", 0)))
            right_wall_flags = int(getattr(obj, "ai_right_wall_flags", obj.get("ai_right_wall_flags", 0)))
            reversed_wall_by_index[wall_target] = (right_wall, left_wall, right_wall_flags, left_wall_flags)

        for obj in nodes:
            connections = list(getattr(obj, "ai_connections", obj.get("ai_connections", [-1, -1, -1, -1])))
            while len(connections) < 4:
                connections.append(-1)
            reversed_connections = [connections[2], connections[3], connections[0], connections[1]]
            obj.ai_connections = reversed_connections
            obj["ai_connections"] = reversed_connections

            left_wall, right_wall, left_wall_flags, right_wall_flags = reversed_wall_by_index.get(
                _ai_node_index(obj),
                (False, False, 0, 0),
            )
            obj.ai_left_wall = left_wall
            obj.ai_right_wall = right_wall
            obj.ai_left_wall_flags = left_wall_flags
            obj.ai_right_wall_flags = right_wall_flags
            obj["ai_left_wall_flags"] = left_wall_flags
            obj["ai_right_wall_flags"] = right_wall_flags

            if obj.type == "MESH" and len(obj.data.vertices) >= 2:
                v0 = obj.data.vertices[0].co.copy()
                obj.data.vertices[0].co = obj.data.vertices[1].co
                obj.data.vertices[1].co = v0
                obj.data.update()
                update_ai_node_handles(obj)

            obj.ai_racing_ratio = 1.0 - float(getattr(obj, "ai_racing_ratio", obj.get("ai_racing_ratio", 0.5)))
            obj.ai_overtake_ratio = 1.0 - float(getattr(obj, "ai_overtake_ratio", obj.get("ai_overtake_ratio", 0.5)))

        rebuild_ai_route_visuals(context.scene)
        self.report({'INFO'}, f"Reversed direction for {len(nodes)} AI node segments.")
        return {'FINISHED'}


class ReverseTrackZone(bpy.types.Operator):
    bl_idname = "object.reverse_track_zones"
    bl_label = "Reverse Track Zone IDs"
    bl_description = "Reverse the Track Zone IDs for all objects in the scene flagged as Track Zones"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # Gather all track zone IDs
        track_zone_objects = [obj for obj in context.scene.objects if obj.is_track_zone]
        if not track_zone_objects:
            self.report({'WARNING'}, "No Track Zone objects found in the scene.")
            return {'CANCELLED'}

        track_zone_ids = [obj.track_zone_id for obj in track_zone_objects]
        if not track_zone_ids:
            self.report({'WARNING'}, "No Track Zone IDs found.")
            return {'CANCELLED'}

        min_id = min(track_zone_ids)
        max_id = max(track_zone_ids)

        # Reverse the track zone IDs
        id_map = {}  # To track renaming
        for obj in track_zone_objects:
            original_id = obj.track_zone_id
            reversed_id = max_id - (original_id - min_id)
            obj.track_zone_id = reversed_id

            # Prepare name
            base_name = f"TZ{reversed_id}"
            if reversed_id not in id_map:
                id_map[reversed_id] = 0
            else:
                id_map[reversed_id] += 1

            # Suffix handling
            suffix = string.ascii_lowercase[id_map[reversed_id]] if id_map[reversed_id] > 0 else ""
            new_name = f"{base_name}{suffix}"

            obj.name = new_name

        # Remove any unwanted ".001", ".002", etc., suffixes
        self.remove_numeric_suffixes(track_zone_objects)

        self.report({'INFO'}, f"Reversed and renamed {len(track_zone_objects)} Track Zone objects.")
        return {'FINISHED'}

    def remove_numeric_suffixes(self, objects):
        for obj in objects:
            original_name = obj.name
            # Check and remove Blender's automatic numeric suffix (like ".001")
            if obj.name.endswith(".001") or obj.name.endswith(".002") or obj.name.endswith(".003"):  # and so on
                base_name = obj.name.rsplit(".", 1)[0]
                # Ensure the new name isn't already taken by another object
                if not bpy.data.objects.get(base_name):
                    obj.name = base_name

class DuplicateTrackZone(bpy.types.Operator):
    bl_idname = "object.duplicate_track_zone"
    bl_label = "Duplicate Track Zone"
    bl_description = "Duplicate the selected Track Zone and copy its properties"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.object

        # Accept either ID-prop or RNA bool (your codebase uses both styles in different places)
        if not obj or not (obj.get("is_track_zone") or getattr(obj, "is_track_zone", False)):
            self.report({'WARNING'}, "No Track Zone object selected")
            return {'CANCELLED'}

        # Duplicate object + mesh data
        new_obj = obj.copy()
        if obj.data:
            new_obj.data = obj.data.copy()
        context.collection.objects.link(new_obj)

        # Copy core props
        tz_id = int(getattr(obj, "track_zone_id", obj.get("track_zone_id", 0)))
        new_obj.track_zone_id = tz_id
        new_obj["track_zone_id"] = tz_id

        new_obj.is_track_zone = True
        new_obj["is_track_zone"] = True

        # Nudge so it's visible (matches the style you used in DuplicateFobObject)
        new_obj.location = obj.location + BlenderVector((1, 1, 0))

        # Ensure TRACK_ZONES collection exists
        zones_collection_name = 'TRACK_ZONES'
        if zones_collection_name not in bpy.data.collections:
            zones_collection = bpy.data.collections.new(zones_collection_name)
            bpy.context.scene.collection.children.link(zones_collection)
        else:
            zones_collection = bpy.data.collections[zones_collection_name]

        # Link to TRACK_ZONES (avoid double-linking)
        if new_obj.name not in zones_collection.objects:
            zones_collection.objects.link(new_obj)

        # Unlink from the current context collection to avoid duplicates in main collection
        if new_obj.name in context.collection.objects:
            context.collection.objects.unlink(new_obj)

        # Select + activate new object
        bpy.ops.object.select_all(action='DESELECT')
        new_obj.select_set(True)
        context.view_layer.objects.active = new_obj

        self.report({'INFO'}, f"Duplicated Track Zone: {new_obj.name}")
        return {'FINISHED'}
    
class CreateTrigger(bpy.types.Operator):
    bl_idname = "mesh.create_trigger"
    bl_label = "Create Trigger"

    def execute(self, context):
        scene = context.scene
        trigger_type = int(scene.new_trigger_type)
        
        # Logic to create the trigger using the selected trigger type
        trigger_obj = create_trigger(trigger_type=trigger_type)

        # Ensure the TRIGGERS collection exists
        triggers_collection_name = 'TRIGGERS'
        if triggers_collection_name not in bpy.data.collections:
            triggers_collection = bpy.data.collections.new(triggers_collection_name)
            bpy.context.scene.collection.children.link(triggers_collection)
        else:
            triggers_collection = bpy.data.collections[triggers_collection_name]

        # Check if the object is already linked to the collection
        if trigger_obj.name not in triggers_collection.objects:
            # Add the created trigger object to the TRIGGERS collection
            triggers_collection.objects.link(trigger_obj)

        # Unlink from the main scene collection if it is linked there
        if trigger_obj.name in bpy.context.scene.collection.objects:
            bpy.context.scene.collection.objects.unlink(trigger_obj)
        
        return {'FINISHED'}

class DuplicateTrigger(bpy.types.Operator):
    bl_idname = "object.duplicate_trigger"
    bl_label = "Duplicate Trigger"
    bl_description = "Duplicate the selected trigger object and copy its custom properties"

    def execute(self, context):
        obj = context.object
        
        if not obj or not obj.get("is_trigger"):
            self.report({'WARNING'}, "No trigger object selected")
            return {'CANCELLED'}
        
        # Duplicate the object
        new_obj = obj.copy()
        new_obj.data = obj.data.copy()
        context.collection.objects.link(new_obj)

        # Copy custom properties
        new_obj.trigger_type_enum = obj.trigger_type_enum
        new_obj.flag_low = obj.flag_low
        new_obj.flag_high = obj.flag_high

        # Ensure the TRIGGERS collection exists
        triggers_collection_name = 'TRIGGERS'
        if triggers_collection_name not in bpy.data.collections:
            triggers_collection = bpy.data.collections.new(triggers_collection_name)
            bpy.context.scene.collection.children.link(triggers_collection)
        else:
            triggers_collection = bpy.data.collections[triggers_collection_name]

        # Add the duplicated trigger object to the TRIGGERS collection
        triggers_collection.objects.link(new_obj)

        # Ensure the object is unlinked from the main scene collection to avoid duplication
        context.collection.objects.unlink(new_obj)
        
        # Select the new object and make it active
        bpy.ops.object.select_all(action='DESELECT')
        new_obj.select_set(True)
        context.view_layer.objects.active = new_obj

        self.report({'INFO'}, f"Duplicated Trigger: {new_obj.name}")
        return {'FINISHED'}

class CopyTrigger(bpy.types.Operator):
    bl_idname = "object.copy_trigger"
    bl_label = "Copy Trigger Properties"
    bl_description = "Copy the trigger properties (type, flag low, flag high) from the selected object"

    def execute(self, context):
        obj = context.object
        
        if not obj or not obj.get("is_trigger"):
            self.report({'WARNING'}, "No trigger object selected")
            return {'CANCELLED'}
        
        # Store the properties in a temporary storage on the scene as a dictionary
        context.scene['copied_trigger_properties'] = {
            'trigger_type': obj.get("trigger_type"),
            'flag_low': obj.get("flag_low"),
            'flag_high': obj.get("flag_high"),
        }

        self.report({'INFO'}, "Trigger properties copied")
        return {'FINISHED'}
    
class PasteTrigger(bpy.types.Operator):
    bl_idname = "object.paste_trigger"
    bl_label = "Paste Trigger Properties"
    bl_description = "Paste the copied trigger properties (type, flag low, flag high) to the selected object"

    def execute(self, context):
        obj = context.object
        
        if not obj or not obj.get("is_trigger"):
            self.report({'WARNING'}, "No trigger object selected")
            return {'CANCELLED'}
        
        # Retrieve the stored properties from the scene
        copied_properties = context.scene.get('copied_trigger_properties', None)
        
        if not copied_properties:
            self.report({'WARNING'}, "No copied trigger properties found")
            return {'CANCELLED'}
        
        # Paste the properties to the selected object
        obj["trigger_type"] = copied_properties.get('trigger_type', obj.get("trigger_type"))
        obj["flag_low"] = copied_properties.get('flag_low', obj.get("flag_low"))
        obj["flag_high"] = copied_properties.get('flag_high', obj.get("flag_high"))
        
        # Optionally, you can trigger an update or redraw if necessary
        context.area.tag_redraw()

        self.report({'INFO'}, "Trigger properties pasted")
        return {'FINISHED'}



def _safe_fob_type_name(obj_id):
    name = OBJECT_TYPE_NAMES.get(int(obj_id), f"Unknown_{int(obj_id)}")
    return "_".join(name.replace("/", "_").split())


def _unique_object_name(base_name):
    existing = {obj.name for obj in bpy.data.objects}
    if base_name not in existing:
        return base_name
    index = 1
    while f"{base_name}_{index}" in existing:
        index += 1
    return f"{base_name}_{index}"


def make_fob_object_display_name(creation_index, obj_id):
    base_name = f"FOB_{int(creation_index):03d}_{int(obj_id):03d}_{_safe_fob_type_name(obj_id)}"
    return _unique_object_name(base_name)

class CreateFobObject(bpy.types.Operator):
    bl_idname = "object.create_fob"
    bl_label = "Create FOB Object"
    bl_description = "Create a new FOB game object with editable properties"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj_id = int(context.scene.selected_fob_object_id)
        subinfos = [0, 0, 0, 0]
        _name, creation_index = generate_fob_name(obj_id)
        name = make_fob_object_display_name(creation_index, obj_id)

        fob_obj = create_directional_fob_mesh_ui(name)

        # Set position at cursor
        fob_obj.location = context.scene.cursor.location

        # Assign properties
        fob_obj.is_fob_object = True
        fob_obj["is_fob_object"] = True
        fob_obj["fob_creation_index"] = creation_index
        fob_obj["fob_type"] = obj_id
        fob_obj.fob_type = obj_id
        for i in range(4):
            setattr(fob_obj, f"fob_subtype_{i+1}", subinfos[i])
        apply_fob_range_scale(fob_obj)

        # Ensure the FOB_OBJECTS collection exists
        objects_collection_name = 'FOB_OBJECTS'
        if objects_collection_name not in bpy.data.collections:
            objects_collection = bpy.data.collections.new(objects_collection_name)
            bpy.context.scene.collection.children.link(objects_collection)
        else:
            objects_collection = bpy.data.collections[objects_collection_name]

        # Check if the object is already linked to the collection
        if fob_obj.name not in objects_collection.objects:
            # Add the created trigger object to the TRIGGERS collection
            objects_collection.objects.link(fob_obj)

        # Unlink from the main scene collection if it is linked there
        if fob_obj.name in bpy.context.scene.collection.objects:
            bpy.context.scene.collection.objects.unlink(fob_obj)

        return {'FINISHED'}

class DuplicateFobObject(bpy.types.Operator):
    bl_idname = "object.duplicate_fob"
    bl_label = "Duplicate FOB Object"
    bl_description = "Duplicate the selected FOB object, assigns new creation index"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        if not obj or not obj.get("is_fob_object"):
            self.report({'WARNING'}, "No valid FOB object selected")
            return {'CANCELLED'}

        obj_id = int(obj.get("fob_type", 0))
        _name, creation_index = generate_fob_name(obj_id)
        name = make_fob_object_display_name(creation_index, obj_id)

        new_obj = create_directional_fob_mesh_ui(name)
        new_obj.location = obj.location + BlenderVector((1, 1, 0))

        new_obj.is_fob_object = True
        new_obj["is_fob_object"] = True
        new_obj["fob_creation_index"] = creation_index
        new_obj["fob_type"] = obj_id
        new_obj.fob_type = obj_id
        for i in range(4):
            setattr(new_obj, f"fob_subtype_{i+1}", int(obj.get(f"fob_subtype_{i+1}", 0)))
        apply_fob_range_scale(new_obj)

        # Ensure the FOB_OBJECTS collection exists
        objects_collection_name = 'FOB_OBJECTS'
        if objects_collection_name not in bpy.data.collections:
            objects_collection = bpy.data.collections.new(objects_collection_name)
            bpy.context.scene.collection.children.link(objects_collection)
        else:
            objects_collection = bpy.data.collections[objects_collection_name]

        # Add the duplicated FOB object to the FOB_OBJECTS collection
        objects_collection.objects.link(new_obj)

        # Select the new object and make it active
        bpy.ops.object.select_all(action='DESELECT')
        new_obj.select_set(True)
        context.view_layer.objects.active = new_obj

        return {'FINISHED'}

class CreateVisibox(bpy.types.Operator):
    bl_idname = "object.create_visibox"
    bl_label = "Create Visibox"
    bl_description = "Creates a new Visibox cube without faces"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene

        collection = bpy.data.collections.get("VISIBOXES")
        if not collection:
            collection = bpy.data.collections.new("VISIBOXES")
            scene.collection.children.link(collection)

        mesh = bpy.data.meshes.new("VisiboxMesh")
        obj = bpy.data.objects.new(self.generate_name(), mesh)

        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        bmesh.ops.delete(bm, geom=bm.faces[:], context='FACES_ONLY')
        bm.to_mesh(mesh)
        bm.free()

        obj.location = scene.cursor.location
        obj.display_type = 'WIRE'
        obj.show_in_front = True

        # Assign core properties
        obj["is_visibox"] = True
        obj["visibox_type"] = scene.visibox_create_type
        obj["visibox_id"] = scene.visibox_create_id

        # If using defined properties
        obj.visibox_type = scene.visibox_create_type
        obj.visibox_id = scene.visibox_create_id

        collection.objects.link(obj)
        context.view_layer.objects.active = obj
        obj.select_set(True)

        return {'FINISHED'}

    def generate_name(self):
        vid = bpy.context.scene.visibox_create_id
        return f"Visibox_{vid}"
    
class ButtonZoneHide(bpy.types.Operator):
    bl_idname = "scene.zone_hide"
    bl_label = "Show / Hide Track Zones"
    bl_description = "Temporarily shows or hides all track zones in viewport"

    def execute(self, context):
        track_zone_collection = bpy.data.collections.get('TRACK_ZONES')
        if track_zone_collection:
            any_visible = any(not obj.hide_get() for obj in track_zone_collection.objects if obj.get("is_track_zone"))
            for obj in track_zone_collection.objects:
                if obj.get("is_track_zone"):
                    obj.hide_set(any_visible)
        return {"FINISHED"}


class ToggleAINodeVisibility(bpy.types.Operator):
    """Temporarily toggle visibility for all AI node objects."""
    bl_idname = "object.toggle_ai_node_visibility"
    bl_label = "Hide / Show AI Nodes"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        collection = bpy.data.collections.get('AI_NODES')
        objs = list(collection.objects) if collection else [
            obj for obj in context.scene.objects
            if (
                getattr(obj, "is_ai_node", False)
                or obj.get("is_ai_node")
                or obj.get("is_ai_route_visual")
                or obj.get("is_ai_node_handle")
            )
        ]
        any_visible = any(not obj.hide_get() for obj in objs)
        for obj in objs:
            obj.hide_set(any_visible)
        self.report({'INFO'}, f"{'Hid' if any_visible else 'Showed'} all AI Nodes")
        return {'FINISHED'}


class TogglePosNodeVisibility(bpy.types.Operator):
    """Temporarily toggle visibility for all position node objects."""
    bl_idname = "object.toggle_pos_node_visibility"
    bl_label = "Hide / Show Pos Nodes"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        collection = bpy.data.collections.get("POS_NODES")
        objs = list(collection.objects) if collection else [
            obj for obj in context.scene.objects
            if (
                getattr(obj, "is_pos_node", False)
                or obj.get("is_pos_node")
                or obj.get("is_pos_route_visual")
            )
        ]
        any_visible = any(not obj.hide_get() for obj in objs)
        for obj in objs:
            obj.hide_set(any_visible)
        self.report({'INFO'}, f"{'Hid' if any_visible else 'Showed'} all Pos Nodes")
        return {'FINISHED'}


class ButtonTriggerHide(bpy.types.Operator):
    bl_idname = "scene.trigger_hide"
    bl_label = "Show / Hide Triggers"
    bl_description = "Temporarily shows or hides all triggers in viewport"

    def execute(self, context):
        trigger_collection = bpy.data.collections.get('TRIGGERS')
        if trigger_collection:
            any_visible = any(not obj.hide_get() for obj in trigger_collection.objects)
            for obj in trigger_collection.objects:
                obj.hide_set(any_visible)
        return {"FINISHED"}

class ToggleFOBVisibility(bpy.types.Operator):
    """Temporarily toggle visibility for all FOB Objects (eye icon)"""
    bl_idname = "object.toggle_fob_visibility"
    bl_label = "Hide / Show FOB Objects"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        objs = [obj for obj in context.scene.objects if obj.get("is_fob_object")]
        any_visible = any(not obj.hide_get() for obj in objs)
        for obj in objs:
            obj.hide_set(any_visible)
        self.report({'INFO'}, f"{'Hid' if any_visible else 'Showed'} all FOB Objects")
        return {'FINISHED'}

class ToggleVisiboxVisibility(bpy.types.Operator):
    """Temporarily toggle visibility for all Visiboxes (eye icon)"""
    bl_idname = "object.toggle_visibox_visibility"
    bl_label = "Hide / Show Visiboxes"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        objs = [obj for obj in context.scene.objects if obj.get("is_visibox")]
        any_visible = any(not obj.hide_get() for obj in objs)
        for obj in objs:
            obj.hide_set(any_visible)
        self.report({'INFO'}, f"{'Hid' if any_visible else 'Showed'} all Visiboxes")
        return {'FINISHED'}


class ToggleInstanceNCPVisibility(bpy.types.Operator):
    """Temporarily toggle visibility for imported FIN instance collision meshes."""
    bl_idname = "object.toggle_instance_ncp_visibility"
    bl_label = "Hide / Show Instance NCP"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        collection = bpy.data.collections.get("INSTANCE_NCP")
        objs = list(collection.objects) if collection else [
            obj for obj in context.scene.objects
            if obj.get("is_ncp_collision") and obj.get("fin_instance_collision_source")
        ]
        any_visible = any(not obj.hide_get() for obj in objs)
        for obj in objs:
            obj.hide_set(any_visible)
        self.report({'INFO'}, f"{'Hid' if any_visible else 'Showed'} Instance NCP")
        return {'FINISHED'}
    
class ButtonHullSphere(bpy.types.Operator):
    bl_idname = "scene.add_hull_sphere"
    bl_label = "Add Hull Sphere"
    bl_description = "Creates a hull sphere at the 3D cursor's location"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        center = scene.cursor.location
        radius = to_revolt_scale(0.1)
        filename = "Hull_Sphere"

        ob = create_sphere(scene, center, radius, "Hull_Sphere")

        # Link only if it is not linked anywhere yet
        if not ob.users_collection:
            context.collection.objects.link(ob)
        else:
            self.report({'WARNING'}, f"'{ob.name}' is already linked")
            return {'CANCELLED'}

        ob["is_hull_sphere"] = True
        ob.is_hull_sphere = True
        scene.is_hull_sphere = True  # Mark scene property

        ob.select_set(True)
        context.view_layer.objects.active = ob
        return {'FINISHED'}

class FindSpecialFile(bpy.types.Operator):
    bl_idname = "object.find_special_file"
    bl_label = "Find Special Object"
    bl_options = {'REGISTER', 'UNDO'}

    light_type_items = [
        ("ANY", "Any", "Find any Re-Volt light"),
        ("OMNI", "Omni", "Omni light"),
        ("OMNI_NORMAL", "Omni Normal", "Omni normal light"),
        ("SPOT", "Spot", "Spot light"),
        ("SPOT_NORMAL", "Spot Normal", "Spot normal light"),
        ("SQUARE_SHADOW", "Square Shadow", "Square shadow light"),
    ]

    ai_node_type_items = [("ANY", "Any", "Find any AI node")] + list(AI_NODE_PROPERTY_ITEMS)

    category: EnumProperty(
        name="Category",
        items=[
            ('AI_NODE', "AI Node", ""),
            ('TRIGGER', "Trigger", ""),
            ('FOB', "FOB Object", ""),
            ('LIGHT', "Light", ""),
            ('FORCE_FIELD', "Force Field", ""),
            ('VISIBOX', "Visibox", ""),
        ]
    )

    trigger_type: EnumProperty(name="Trigger Type", items=trigger_type_items)
    fob_type: EnumProperty(name="FOB Object Type", items=fob_type_items)
    ai_node_type: EnumProperty(name="AI Node Type", items=ai_node_type_items)
    light_type: EnumProperty(name="Light Type", items=light_type_items)
    force_field_type: EnumProperty(
        name="Force Field Type",
        items=[
            ("LINEAR", "Linear", ""),
            ("ORIENTATION_UP", "Orientation Up", ""),
            ("VELOCITY", "Velocity", ""),
            ("SPHERICAL", "Spherical", ""),
            ("WIND", "Wind", ""),
            ("ANGULAR", "Angular", ""),
            ("ANGULAR_VELOCITY", "Angular Velocity", ""),
            ("ORIENTATION_FWD", "Orientation Fwd", ""),
        ],
    )
    visibox_type: EnumProperty(name="Visibox Type", items=visibox_type_items)

    select_all_matches: BoolProperty(
        name="Select All Matches",
        description="Select all matching objects instead of just one",
        default=False
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "category")

        if self.category == 'TRIGGER':
            layout.prop(self, "trigger_type")
        elif self.category == 'FOB':
            layout.prop(self, "fob_type")
        elif self.category == 'AI_NODE':
            layout.prop(self, "ai_node_type")
        elif self.category == 'LIGHT':
            layout.prop(self, "light_type")
        elif self.category == 'FORCE_FIELD':
            layout.prop(self, "force_field_type")
        elif self.category == 'VISIBOX':
            layout.prop(self, "visibox_type")

        layout.prop(self, "select_all_matches")

    def execute(self, context):
        found_any = False
        bpy.ops.object.select_all(action='DESELECT')

        for obj in context.scene.objects:
            if self.category == 'AI_NODE' and self._flag(obj, "is_ai_node"):
                if self.ai_node_type != "ANY":
                    obj_type = int(getattr(obj, "ai_property_type", obj.get("ai_property_type", -1)))
                    if obj_type != int(self.ai_node_type):
                        continue
                self.select_object(obj, context)
                found_any = True
                if not self.select_all_matches:
                    break

            elif self.category == 'TRIGGER' and self._flag(obj, "is_trigger"):
                if int(getattr(obj, "trigger_type_enum", obj.get("trigger_type_enum", -1))) != int(self.trigger_type):
                    continue
                self.select_object(obj, context)
                found_any = True
                if not self.select_all_matches:
                    break

            elif self.category == 'FOB' and self._flag(obj, "is_fob_object"):
                if int(getattr(obj, "fob_type", obj.get("fob_type", -1))) != int(self.fob_type):
                    continue
                self.select_object(obj, context)
                found_any = True
                if not self.select_all_matches:
                    break

            elif self.category == 'LIGHT' and self._flag(obj, "is_light"):
                obj_type = getattr(obj, "light_type", obj.get("light_type", "OMNI"))
                if self.light_type != "ANY" and obj_type != self.light_type:
                    continue
                self.select_object(obj, context)
                found_any = True
                if not self.select_all_matches:
                    break

            elif self.category == 'FORCE_FIELD' and self._flag(obj, "is_force_field"):
                obj_type = getattr(obj, "force_field_type", obj.get("force_field_type", "LINEAR"))
                if obj_type != self.force_field_type:
                    continue
                self.select_object(obj, context)
                found_any = True
                if not self.select_all_matches:
                    break

            elif self.category == 'VISIBOX' and self._flag(obj, "is_visibox"):
                if getattr(obj, "visibox_type", obj.get("visibox_type", "")) != self.visibox_type:
                    continue
                self.select_object(obj, context)
                found_any = True
                if not self.select_all_matches:
                    break

        if found_any:
            return {'FINISHED'}
        else:
            self.report({'WARNING'}, "No matching object found.")
            return {'CANCELLED'}

    def select_object(self, obj, context):
        obj.select_set(True)
        context.view_layer.objects.active = obj
        return True

    def _flag(self, obj, name):
        return bool(getattr(obj, name, False) or obj.get(name, False))

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
    
class CreateLight(bpy.types.Operator):
    bl_idname = "object.create_light"
    bl_label = "Create Light"
    bl_description = "Create a new Re-Volt light"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        light_type = scene.new_light_type

        # generate name
        index = max((o.get("light_creation_index", -1) for o in bpy.data.objects if o.get("is_light")), default=-1) + 1
        name = f"Light_{index}"

        # Placeholder meshes
        if light_type == "SQUARE_SHADOW":
            mesh = bpy.data.meshes.new(name + "_Mesh")
            obj = bpy.data.objects.new(name, mesh)
            bm = bmesh.new()
            bmesh.ops.create_cube(bm, size=1.0)
            bmesh.ops.delete(bm, geom=bm.faces[:], context='FACES_ONLY')
            bm.to_mesh(mesh)
            bm.free()
            mesh.update()
            obj.display_type = 'WIRE'
            obj.show_in_front = True
        elif light_type in {"SPOT", "SPOT_NORMAL"}:
            mesh = bpy.data.meshes.new(name + "_Mesh")
            obj = bpy.data.objects.new(name, mesh)
            bm = bmesh.new()
            bmesh.ops.create_cone(bm, segments=16, radius1=0.5, radius2=0.0, depth=1.5)
            bmesh.ops.delete(bm, geom=bm.faces[:], context='FACES_ONLY')
            bm.to_mesh(mesh)
            bm.free()
            mesh.update()
            obj.display_type = 'WIRE'
            obj.show_in_front = True
        else:
            obj = bpy.data.objects.new(name, None)
            obj.empty_display_type = 'SPHERE'
            obj.empty_display_size = 0.2

        obj.location = scene.cursor.location
        obj["is_light"] = True
        obj["light_creation_index"] = index
        obj.is_light = True
        obj.light_type = light_type
        obj.light_world_mode = "WORLD_OBJECTS"
        obj.light_rgb = (0, 0, 0)
        obj.light_reach = 512.0
        obj.light_flicker = False
        obj.light_flicker_speed = 1
        obj.light_cone = 90

        if light_type == "SQUARE_SHADOW":
            obj.scale = (0.32, 0.32, 0.32)
            obj.light_size = (32.0, 32.0, 32.0)

        # Ensure the LIGHTS collection exists
        lights_collection_name = 'LIGHTS'
        if lights_collection_name not in bpy.data.collections:
            lights_collection = bpy.data.collections.new(lights_collection_name)
            bpy.context.scene.collection.children.link(lights_collection)
        else:
            lights_collection = bpy.data.collections[lights_collection_name]

        # Check if the object is already linked to the collection
        if obj.name not in lights_collection.objects:
            # Add the created light object to the LIGHTS collection
            lights_collection.objects.link(obj)

        # Unlink from the main scene collection if it is linked there
        if obj.name in bpy.context.scene.collection.objects:
            bpy.context.scene.collection.objects.unlink(obj)

        context.view_layer.objects.active = obj
        obj.select_set(True)
        return {'FINISHED'}

class CreateForceField(bpy.types.Operator):
    bl_idname = "object.create_force_field"
    bl_label = "Create Force Field"
    bl_description = "Create a new Re-Volt force field"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        field_type = scene.new_force_field_type
        shape = scene.new_force_field_shape
        index = max(
            (o.get("force_field_index", -1) for o in bpy.data.objects if o.get("is_force_field")),
            default=-1
        ) + 1
        name = f"ForceField_{index}_{field_type}"

        mesh = bpy.data.meshes.new(name + "_Mesh")
        obj = bpy.data.objects.new(name, mesh)
        if shape == "SPHERE":
            segments = 13
            verts = []
            edges = []

            def add_ring(axis):
                start = len(verts)
                for i in range(segments):
                    angle = 2.0 * math.pi * i / segments
                    c = math.cos(angle)
                    s = math.sin(angle)
                    if axis == "Z":
                        verts.append((c, s, 0.0))
                    elif axis == "Y":
                        verts.append((c, 0.0, s))
                    else:
                        verts.append((0.0, c, s))
                for i in range(segments):
                    edges.append((start + i, start + ((i + 1) % segments)))

            add_ring("Z")
            add_ring("Y")
            add_ring("X")
            mesh.from_pydata(verts, edges, [])
        else:
            bm = bmesh.new()
            bmesh.ops.create_cube(bm, size=2.0)
            bmesh.ops.delete(bm, geom=bm.faces[:], context='FACES_ONLY')
            bm.to_mesh(mesh)
            bm.free()
        mesh.update()

        obj.location = scene.cursor.location
        obj.scale = (1.28, 1.28, 1.28)
        obj.display_type = 'WIRE'
        obj.show_in_front = True
        obj["is_force_field"] = True
        obj["force_field_index"] = index
        obj["force_field_raw_type"] = 0x10000000
        obj.is_force_field = True
        obj.force_field_type = field_type
        obj.force_field_shape = shape
        obj.force_field_apply = "FORCE"
        obj.force_field_direction_mode = "LINEAR"
        obj.force_field_distribution = "UNIFORM"
        obj.force_field_magnitude = 0.0
        obj.force_field_damping = 0.0
        obj.force_field_mag_start = 0.0
        obj.force_field_mag_end = 0.0
        obj.force_field_radius_start = 256.0
        obj.force_field_radius_end = 512.0
        obj.force_field_direction = (0.0, -1.0, 0.0)
        obj.force_field_option = 0x10000000

        collection_name = "FORCE_FIELDS"
        if collection_name not in bpy.data.collections:
            fields_collection = bpy.data.collections.new(collection_name)
            bpy.context.scene.collection.children.link(fields_collection)
        else:
            fields_collection = bpy.data.collections[collection_name]

        fields_collection.objects.link(obj)
        context.view_layer.objects.active = obj
        obj.select_set(True)
        return {'FINISHED'}


class DuplicateForceField(bpy.types.Operator):
    bl_idname = "object.duplicate_force_field"
    bl_label = "Duplicate Force Field"
    bl_description = "Duplicate the selected Re-Volt force field"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.object
        if not obj or not (getattr(obj, "is_force_field", False) or obj.get("is_force_field", False)):
            self.report({'WARNING'}, "No Re-Volt force field selected")
            return {'CANCELLED'}

        index = max(
            (
                o.get("force_field_index", -1)
                for o in context.scene.objects
                if getattr(o, "is_force_field", False) or o.get("is_force_field", False)
            ),
            default=-1
        ) + 1

        new_obj = obj.copy()
        if obj.data:
            new_obj.data = obj.data.copy()

        new_obj.location = obj.location + BlenderVector((1, 1, 0))
        new_obj["is_force_field"] = True
        new_obj["force_field_index"] = index
        new_obj.is_force_field = True

        collection_name = "FORCE_FIELDS"
        if collection_name not in bpy.data.collections:
            fields_collection = bpy.data.collections.new(collection_name)
            bpy.context.scene.collection.children.link(fields_collection)
        else:
            fields_collection = bpy.data.collections[collection_name]

        fields_collection.objects.link(new_obj)
        bpy.ops.object.select_all(action='DESELECT')
        new_obj.select_set(True)
        context.view_layer.objects.active = new_obj
        return {'FINISHED'}


class ToggleForceFieldVisibility(bpy.types.Operator):
    bl_idname = "object.toggle_force_field_visibility"
    bl_label = "Hide / Show Force Fields"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        objs = [
            obj
            for obj in context.scene.objects
            if getattr(obj, "is_force_field", False) or obj.get("is_force_field", False)
        ]
        if not objs:
            self.report({'INFO'}, "No Re-Volt force fields found.")
            return {'CANCELLED'}

        any_visible = any(not obj.hide_get() for obj in objs)
        for obj in objs:
            obj.hide_set(any_visible)

        self.report({'INFO'}, f"{'Hid' if any_visible else 'Showed'} all Re-Volt force fields")
        return {'FINISHED'}

class DuplicateLight(bpy.types.Operator):
    bl_idname = "object.duplicate_light"
    bl_label = "Duplicate Light"
    bl_description = "Duplicate the selected Re-Volt light"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.object
        if not obj or not (getattr(obj, "is_light", False) or obj.get("is_light", False)):
            self.report({'WARNING'}, "No Re-Volt light selected")
            return {'CANCELLED'}

        index = max(
            (
                o.get("light_creation_index", -1)
                for o in context.scene.objects
                if getattr(o, "is_light", False) or o.get("is_light", False)
            ),
            default=-1
        ) + 1

        new_obj = obj.copy()
        if obj.data:
            new_obj.data = obj.data.copy()

        new_obj.location = obj.location + BlenderVector((1, 1, 0))
        new_obj["is_light"] = True
        new_obj.is_light = True
        new_obj["light_creation_index"] = index
        try:
            new_obj.light_creation_index = index
        except AttributeError:
            pass

        # Ensure the LIGHTS collection exists
        lights_collection_name = 'LIGHTS'
        if lights_collection_name not in bpy.data.collections:
            lights_collection = bpy.data.collections.new(lights_collection_name)
            bpy.context.scene.collection.children.link(lights_collection)
        else:
            lights_collection = bpy.data.collections[lights_collection_name]

        # Add the duplicated trigger object to the LIGHTS collection
        lights_collection.objects.link(new_obj)

        # Select the new object and make it active
        bpy.ops.object.select_all(action='DESELECT')
        new_obj.select_set(True)
        context.view_layer.objects.active = new_obj

        self.report({'INFO'}, f"Duplicated light: {new_obj.name}")
        return {'FINISHED'}

class ToggleLightVisibility(bpy.types.Operator):
    """Temporarily toggle visibility for all Re-Volt lights"""
    bl_idname = "object.toggle_light_visibility"
    bl_label = "Hide / Show Lights"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        objs = [
            obj
            for obj in context.scene.objects
            if getattr(obj, "is_light", False) or obj.get("is_light", False)
        ]
        if not objs:
            self.report({'INFO'}, "No Re-Volt lights found.")
            return {'CANCELLED'}

        any_visible = any(not obj.hide_get() for obj in objs)
        for obj in objs:
            obj.hide_set(any_visible)

        self.report({'INFO'}, f"{'Hid' if any_visible else 'Showed'} all Re-Volt lights")
        return {'FINISHED'}

"""
MATERIALS & TEXTURES ---------------------------------------------------------
"""

# -------------------------------------------------------------------------
# Debug helpers (high-signal, low-noise)
# -------------------------------------------------------------------------

RV_MAT_DEBUG = False

def _d(msg: str):
    if RV_MAT_DEBUG:
        print(msg)

def mat_name(m):
    """Safe material name getter for slots that might contain Material / None / str."""
    if m is None:
        return None
    if isinstance(m, str):
        return m
    return getattr(m, "name", None)

def _mat_label(m):
    """Return a readable label for material slot entries, even if corrupted."""
    try:
        if m is None:
            return "None"
        if isinstance(m, str):
            return f"STR:'{m}'"
        return f"MAT:'{m.name}'"
    except Exception as e:
        return f"<bad-mat {type(m).__name__}: {e}>"

def sanitize_material_slots(obj, *, create_missing=True):
    """
    Repairs obj.data.materials if it contains strings (names) instead of Material datablocks.
    Prints what it fixed, so you can find where corruption originates.
    """
    if not obj or obj.type != 'MESH':
        return

    mesh = obj.data
    changed = False

    for i in range(len(mesh.materials)):
        m = mesh.materials[i]

        if isinstance(m, str):
            name = m.strip()
            _d(f"[SANITIZE] {obj.name} slot#{i} is STR '{name}' -> resolving to Material datablock")

            mat = bpy.data.materials.get(name)
            if not mat and create_missing and name:
                _d(f"[SANITIZE] creating missing material datablock '{name}'")
                mat = bpy.data.materials.new(name=name)
                mat.use_nodes = True

            if mat:
                mesh.materials[i] = mat
                changed = True
            else:
                _d(f"[SANITIZE] could not resolve '{name}' -> leaving slot as-is (will likely fail later)")

        elif m is not None and not hasattr(m, "name"):
            _d(f"[SANITIZE] {obj.name} slot#{i} has unexpected type: {type(m)} value={repr(m)}")

    if changed:
        mesh.update()
        _d(f"[SANITIZE] {obj.name} material slots repaired.")

def _scene_str(scene, key: str, default: str) -> str:
    """Get a scene string value; treat None/''/'   ' as missing and return default."""
    try:
        v = get_scene_value(scene, key, default)
    except Exception:
        v = default
    if v is None:
        return default
    if isinstance(v, str) and not v.strip():
        return default
    return v

def _d_obj_header(obj, tag="OBJ"):
    if not RV_MAT_DEBUG:
        return
    # MaterialAssignmentHelper._is_car_part() exists, but this debug helper is global.
    # We report only generic flags here; the per-class header can add more.
    _d(
        f"[{tag}] name='{obj.name}' type={obj.type} mode={obj.mode} "
        f"is_editmode={getattr(obj.data, 'is_editmode', None)} "
        f"is_instance={obj.get('is_instance', False)} is_model={obj.get('is_model', False)}"
    )

def _d_scene_tex(scene):
    if not RV_MAT_DEBUG:
        return
    _d(
        f"[SCENE] material_choice={getattr(scene, 'material_choice', None)} "
        f"level_texture_base='{get_scene_value(scene, 'level_texture_base', '')}' "
        f"selected_car_texture='{get_scene_value(scene, 'selected_car_texture', 'car.bmp')}'"
    )

def _d_slots(obj, tag="SLOTS"):
    if not RV_MAT_DEBUG:
        return
    mats = []
    for i, m in enumerate(obj.data.materials):
        mats.append(f"{i}:{_mat_label(m)}")
    _d(f"[{tag}] {obj.name} materials({len(obj.data.materials)}): " + ", ".join(mats))

def _d_face_stats(mesh, tag="FACES"):
    if not RV_MAT_DEBUG or not hasattr(mesh, "polygons"):
        return
    if len(mesh.polygons) == 0:
        _d(f"[{tag}] mesh has 0 polygons")
        return
    idxs = [p.material_index for p in mesh.polygons]
    _d(f"[{tag}] poly material_index range: min={min(idxs)} max={max(idxs)} unique={len(set(idxs))}")


# -------------------------------------------------------------------------
# Slot pruning
# -------------------------------------------------------------------------

def prune_unused_material_slots(obj, keep_names=None):
    """Remove unreferenced material slots, optionally preserving named entries."""
    if not obj or obj.type != 'MESH':
        return

    keep_names = keep_names or set()
    mesh = obj.data

    referenced = {poly.material_index for poly in mesh.polygons}

    if RV_MAT_DEBUG:
        _d(f"[PRUNE] {obj.name} referenced slot indices: {sorted(referenced)}")
        if keep_names:
            _d(f"[PRUNE] {obj.name} keep_names: {sorted(keep_names)}")

    for idx in range(len(mesh.materials) - 1, -1, -1):
        mat = mesh.materials[idx]
        nm = mat_name(mat)

        # IMPORTANT: never touch .name on unknown types here
        if idx not in referenced and (not nm or nm not in keep_names):
            if RV_MAT_DEBUG:
                _d(f"[PRUNE] {obj.name} POP slot {idx} '{nm}' (unreferenced)")
            mesh.materials.pop(index=idx)


# -------------------------------------------------------------------------
# Ensure a material exists for an image name (car.bmp etc.)
# -------------------------------------------------------------------------

def ensure_material_for_image(image_name: str):
    """Return a material mapped to the given image name, creating one if needed."""
    if not image_name or (isinstance(image_name, str) and not image_name.strip()):
        _d("[CAR] ensure_material_for_image: image_name is empty -> None")
        return None

    candidates = [image_name]
    if image_name.lower().endswith('.bmp'):
        candidates.append(image_name[:-4])
    else:
        candidates.append(f"{image_name}.bmp")

    _d(f"[CAR] ensure_material_for_image: image_name='{image_name}' candidates={candidates}")

    # 1) Reuse existing material datablock
    for cand in candidates:
        mat = bpy.data.materials.get(cand)
        if mat:
            _d(f"[CAR] FOUND MATERIAL '{mat.name}' (candidate='{cand}')")
            return mat

    # 2) Create if image datablock exists
    for cand in candidates:
        image = bpy.data.images.get(cand)
        if not image and cand.lower().endswith('.bmp'):
            image = bpy.data.images.get(cand[:-4])

        if image:
            _d(f"[CAR] FOUND IMAGE '{image.name}' filepath='{image.filepath}' (candidate='{cand}') -> creating material")

            mat = bpy.data.materials.new(name=cand)
            mat.use_nodes = True
            nodes = mat.node_tree.nodes
            links = mat.node_tree.links
            nodes.clear()

            out_node = nodes.new("ShaderNodeOutputMaterial")
            bsdf = nodes.new("ShaderNodeBsdfPrincipled")
            img_node = nodes.new("ShaderNodeTexImage")
            img_node.image = image
            img_node.interpolation = 'Linear'

            links.new(img_node.outputs["Color"], bsdf.inputs["Base Color"])
            links.new(bsdf.outputs["BSDF"], out_node.inputs["Surface"])

            _d(f"[CAR] CREATED MATERIAL '{mat.name}' using image '{image.name}'")
            return mat
        else:
            _d(f"[CAR] no image datablock for candidate '{cand}'")

    _d("[CAR] FAILED: no material + no image datablock matched")
    return None

def ensure_vertex_layer_material(name: str, kind: str = 'COL'):
    """
    Create (or reuse) a simple material for Vertex Color (Col) or Vertex Alpha (Alpha) preview.
    - COL: Base Color = Attribute 'Col', opaque.
    - ALPHA: Base Color = grayscale from Attribute 'Alpha', opaque (no real transparency).
    """
    mat = bpy.data.materials.get(name)
    if not mat:
        mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    out = nodes.new('ShaderNodeOutputMaterial')
    links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])

    if kind.upper() == 'ALPHA':
        # Read 'Alpha' vertex attribute (often stored as RGB), convert to grayscale,
        # and show it as Base Color. Keep the material opaque.
        attr_a = nodes.new('ShaderNodeAttribute')
        attr_a.attribute_name = 'Alpha'

        rgb2bw = nodes.new('ShaderNodeRGBToBW')
        links.new(attr_a.outputs['Color'], rgb2bw.inputs['Color'])

        ramp = nodes.new('ShaderNodeValToRGB')  # black->white ramp
        # Defaults are already black to white; leave as-is or adjust if needed.
        links.new(rgb2bw.outputs['Val'], ramp.inputs['Fac'])

        links.new(ramp.outputs['Color'], bsdf.inputs['Base Color'])

        bsdf.inputs['Alpha'].default_value = 1.0
        if hasattr(mat, 'blend_method'):
            mat.blend_method = 'OPAQUE'
        if hasattr(mat, 'shadow_method'):
            mat.shadow_method = 'OPAQUE'
    else:
        # COL preview: use 'Col' attribute as Base Color, keep opaque.
        attr_col = nodes.new('ShaderNodeAttribute')
        attr_col.attribute_name = 'Col'
        links.new(attr_col.outputs['Color'], bsdf.inputs['Base Color'])

        bsdf.inputs['Alpha'].default_value = 1.0
        if hasattr(mat, 'blend_method'):
            mat.blend_method = 'OPAQUE'
        if hasattr(mat, 'shadow_method'):
            mat.shadow_method = 'OPAQUE'

    return mat

# -------------------------------------------------------------------------
# Material assignment core
# -------------------------------------------------------------------------

class MaterialAssignmentHelper:
    car_parts_prefixes = ["body", "wheel", "axle", "spring", "pin", "spinner"]

    def _is_car_part(self, obj):
        return getattr(obj, "is_car_part", False) or any(
            prefix in obj.name.lower() for prefix in self.car_parts_prefixes
        )

    def _is_hull_part(self, obj):
        # 1) Blender custom properties / attributes (your hull operators set these)
        if getattr(obj, "is_hull_sphere", False) or getattr(obj, "is_hull_convex", False):
            return True

        # 2) ID properties (obj["is_hull_sphere"] style)
        try:
            if obj.get("is_hull_sphere", False) or obj.get("is_hull_convex", False):
                return True
        except Exception:
            pass

        # 3) Name heuristics (covers Hull_Sphere.001 etc.)
        n = obj.name.lower()
        return ("hull_sphere" in n) or ("convex_hull" in n) or n.startswith("hull_")

    # -------------------------------------------------------------------------
    # High-level loop
    # -------------------------------------------------------------------------

    def assign_materials_to_all(self, mesh_objects, existing_textures, material_choice):
        _d(f"[AUTO] Assigning materials to {len(mesh_objects)} mesh objects (choice={material_choice})")

        for obj in mesh_objects:
            try:
                if obj.type != 'MESH':
                    continue

                if self._is_hull_part(obj):
                    _d(f"[AUTO] Skipping hull object: {obj.name}")
                    continue

                # MUST run before any .name access on slots
                sanitize_material_slots(obj)

                _d_obj_header(obj, "AUTOOBJ")
                _d(f"[AUTOOBJ] is_car_part={self._is_car_part(obj)}")
                _d_slots(obj, "BEFORE_SLOTS")
                _d_face_stats(obj.data, "BEFORE_FACES")

                keep_names = set()
                if material_choice == 'TEX_VC':
                    # SAFE: do NOT use m.name directly
                    keep_names = {
                        mat_name(m) for m in obj.data.materials
                        if mat_name(m) and not self._is_tex_vc_mat(m)
                    }
                    _d(f"[AUTO] {obj.name} keep_names (TEX_VC) = {sorted(keep_names)}")

                self.update_material_assignment(obj, existing_textures, material_choice)

                _d_slots(obj, "AFTER_ASSIGN_SLOTS")
                _d_face_stats(obj.data, "AFTER_ASSIGN_FACES")

                prune_unused_material_slots(obj, keep_names=keep_names)

                _d_slots(obj, "AFTER_PRUNE_SLOTS")
                _d_face_stats(obj.data, "AFTER_PRUNE_FACES")

            except Exception as e:
                _d(f"[ERROR] Exception while processing {obj.name}: {e}")

    # -------------------------------------------------------------------------
    # Helpers to detect existing textures / base names
    # -------------------------------------------------------------------------

    def get_existing_textures(self):
        textures = {}
        for image in bpy.data.images:
            name_parts = image.name.rsplit('.', 1)
            if len(name_parts) > 1 and name_parts[-1].isalpha():
                textures[image.name] = name_parts[0]
        return textures

    def get_base_name_for_layers(self, obj):
        # Blender-side material matching must NOT truncate
        return clean_model_base_name(obj.name, truncate=False)

    def get_current_base_name(self, obj):
        if obj.get("is_instance") and "fin_texture_base" in obj:
            _d(f"[BASE] Using fin_texture_base: {obj['fin_texture_base']} for {obj.name}")
            return obj["fin_texture_base"]

        if self._is_car_part(obj):
            scene = bpy.context.scene
            car_tex = _scene_str(scene, "selected_car_texture", "car.bmp")
            base = clean_model_base_name(car_tex)
            _d(f"[BASE] Car part {obj.name}: selected_car_texture='{car_tex}' -> base='{base}'")
            return base

        model_name = clean_model_base_name(obj.name, truncate=False)
        _d(f"[BASE] obj={obj.name} model_name={model_name}, is_model={obj.get('is_model', False)}")

        if obj.get("is_model", False):
            scene = bpy.context.scene
            for i in range(MAX_MODEL_SLOTS):
                slot_name = get_scene_value(scene, f"m_model_name_{i}", "")
                tex_mode = get_scene_value(scene, f"m_texture_mode_{i}", "")
                tex_path = get_scene_value(scene, f"m_texture_path_{i}", "")
                _d(f"[BASE] Slot {i}: m_model_name='{slot_name}', mode='{tex_mode}', path='{tex_path}'")

                if clean_model_base_name(slot_name, truncate=False) == model_name:
                    if tex_mode == "LEVEL_TEXTURES":
                        return os.path.basename(tex_path.rstrip("/\\")).lower()
                    elif tex_mode == "TEXTURE_NAME":
                        return os.path.splitext(os.path.basename(tex_path))[0].lower()
                    else:
                        return model_name

        return self.get_base_name_for_layers(obj)

    # -------------------------------------------------------------------------
    # TEX+VC material creation (REQUIRED for material_choice == 'TEX_VC')
    # -------------------------------------------------------------------------

    def assign_tex_vc_materials(self, obj, existing_textures=None):
        _d(f"[TEXVC] assign_tex_vc_materials: {obj.name}")

        import bmesh

        # Safety first: prevent slot type weirdness from crashing the run
        sanitize_material_slots(obj)

        # 0) Make sure UV texture materials exist & are assigned first
        try:
            if existing_textures is not None:
                self.assign_uv_textures(obj, existing_textures)
            else:
                # if your signature always requires existing_textures, you can remove this branch
                self.assign_uv_textures(obj, self.get_existing_textures())
        except Exception as e:
            _d(f"[TEXVC][ERROR] UV assignment failed for {obj.name}: {e}")
            return

        # 1) Clean up any stale *_TexVC slots that are now unreferenced
        self._remove_unreferenced_tex_vc_slots(obj)

        mesh = obj.data
        bm = bmesh.new()
        bm.from_mesh(mesh)

        blended_cache = {}

        for face in bm.faces:
            idx = face.material_index
            if idx < 0 or idx >= len(mesh.materials):
                continue

            orig_mat = mesh.materials[idx]

            # orig_mat can be None; sanitize_material_slots should prevent STR,
            # but keep it defensive anyway:
            if not orig_mat or isinstance(orig_mat, str):
                continue

            # If face already uses TexVC, leave it
            if self._is_tex_vc_mat(orig_mat):
                continue

            # Base name from the texture material
            base_name = orig_mat.name or ""
            if base_name.lower().endswith(".bmp"):
                base_name = base_name[:-4]
            if base_name.endswith("_Col"):
                base_name = base_name[:-4]

            if not base_name:
                base_name = self.get_current_base_name(obj)

            new_name = f"{base_name}_TexVC"

            new_mat = blended_cache.get(new_name)
            if not new_mat:
                new_mat = bpy.data.materials.get(new_name)
                if not new_mat:
                    new_mat = bpy.data.materials.new(name=new_name)

                new_mat.use_nodes = True
                nodes = new_mat.node_tree.nodes
                links = new_mat.node_tree.links

                # Clear old nodes
                for node in list(nodes):
                    nodes.remove(node)

                # Opaque in viewport
                if hasattr(new_mat, "blend_method"):
                    new_mat.blend_method = "OPAQUE"
                if hasattr(new_mat, "shadow_method"):
                    new_mat.shadow_method = "OPAQUE"

                # --------------------------------------------------------------
                # Texture node: reuse image from original material if possible
                # --------------------------------------------------------------
                tex_node = nodes.new("ShaderNodeTexImage")
                tex_node.image = None
                tex_node.interpolation = "Linear"
                has_texture = False

                if getattr(orig_mat, "use_nodes", False) and orig_mat.node_tree:
                    for n in orig_mat.node_tree.nodes:
                        if n.type == "TEX_IMAGE" and getattr(n, "image", None):
                            tex_node.image = n.image
                            has_texture = True
                            break

                # --------------------------------------------------------------
                # Vertex Color attributes: Col & Alpha
                # --------------------------------------------------------------
                col_attr = nodes.new("ShaderNodeAttribute")
                col_attr.attribute_name = "Col"

                alpha_attr = nodes.new("ShaderNodeAttribute")
                alpha_attr.attribute_name = "Alpha"

                rgb2bw = nodes.new("ShaderNodeRGBToBW")
                links.new(alpha_attr.outputs["Color"], rgb2bw.inputs["Color"])

                mul = nodes.new("ShaderNodeMath")
                mul.operation = "MULTIPLY"
                mul.inputs[1].default_value = 0.5
                links.new(rgb2bw.outputs["Val"], mul.inputs[0])

                add = nodes.new("ShaderNodeMath")
                add.operation = "ADD"
                add.inputs[1].default_value = 0.5
                links.new(mul.outputs["Value"], add.inputs[0])

                # --------------------------------------------------------------
                # Fac shaping (make VC stronger)
                # Current add outputs 0.5..1.0
                # Scale to 0.75..1.0 by multiplying 1.5 and clamping to 0..1
                # --------------------------------------------------------------
                strength = 1.5

                fac_boost = nodes.new("ShaderNodeMath")
                fac_boost.operation = "MULTIPLY"
                fac_boost.inputs[1].default_value = strength
                fac_boost.use_clamp = True
                links.new(add.outputs["Value"], fac_boost.inputs[0])

                # --------------------------------------------------------------
                # Mix: texture base + VC overlay in OVERLAY mode
                # --------------------------------------------------------------
                mix = nodes.new("ShaderNodeMixRGB")
                mix.blend_type = "OVERLAY"
                links.new(fac_boost.outputs["Value"], mix.inputs["Fac"])

                if has_texture:
                    links.new(tex_node.outputs["Color"], mix.inputs[1])
                else:
                    links.new(col_attr.outputs["Color"], mix.inputs[1])

                links.new(col_attr.outputs["Color"], mix.inputs[2])

                # --------------------------------------------------------------
                # BSDF + Output
                # --------------------------------------------------------------
                bsdf = nodes.new("ShaderNodeBsdfPrincipled")
                output = nodes.new("ShaderNodeOutputMaterial")

                links.new(mix.outputs["Color"], bsdf.inputs["Base Color"])
                bsdf.inputs["Alpha"].default_value = 1.0
                links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])

                blended_cache[new_name] = new_mat
                _d(f"[TEXVC] created/updated material '{new_name}' (has_texture={has_texture})")

            # Ensure TexVC material exists in mesh slots
            if new_mat.name not in mesh.materials:
                mesh.materials.append(new_mat)
                _d(f"[TEXVC] {obj.name} appended slot '{new_mat.name}'")

            face.material_index = mesh.materials.find(new_mat.name)

        bm.to_mesh(mesh)
        bm.free()
        mesh.update()

        # Activate one TexVC material
        for blended in blended_cache.values():
            if blended and blended.name in mesh.materials:
                idx = mesh.materials.find(blended.name)
                if idx >= 0:
                    obj.active_material_index = idx
                    _d(f"[TEXVC] {obj.name} active_material_index set -> {idx} '{blended.name}'")
                    break

    # -------------------------------------------------------------------------
    # TexVC helpers / cleanup
    # -------------------------------------------------------------------------

    def _is_tex_vc_mat(self, mat):
        nm = mat_name(mat)
        return bool(nm and isinstance(nm, str) and nm.endswith("_TexVC"))

    def _remove_unreferenced_tex_vc_slots(self, obj):
        mesh = obj.data
        bm = bmesh.new()
        bm.from_mesh(mesh)
        referenced = {f.material_index for f in bm.faces}
        bm.free()

        for idx in range(len(mesh.materials) - 1, -1, -1):
            mat = mesh.materials[idx]
            if idx not in referenced and self._is_tex_vc_mat(mat):
                _d(f"[TEXVC] removing unreferenced TexVC slot {idx} '{mat_name(mat)}' on {obj.name}")
                mesh.materials.pop(index=idx)

    def _set_active_texture_material(self, obj):
        mesh = obj.data

        if len(mesh.polygons) > 0:
            idx = mesh.polygons[0].material_index
            if 0 <= idx < len(mesh.materials) and not self._is_tex_vc_mat(mesh.materials[idx]):
                obj.active_material_index = idx
                _d(f"[ACTIVE] {obj.name} active_material_index set from first poly -> {idx}")
                return

        for i, m in enumerate(mesh.materials):
            if not m or self._is_tex_vc_mat(m):
                continue
            nm = mat_name(m) or ""
            if nm.lower().endswith(".bmp"):
                obj.active_material_index = i
                _d(f"[ACTIVE] {obj.name} active_material_index set to .bmp slot -> {i} '{nm}'")
                return
            if getattr(m, "use_nodes", False) and any(n.type == 'TEX_IMAGE' for n in m.node_tree.nodes):
                obj.active_material_index = i
                _d(f"[ACTIVE] {obj.name} active_material_index set to TEX_IMAGE slot -> {i} '{nm}'")
                return

        for i, m in enumerate(mesh.materials):
            if not self._is_tex_vc_mat(m):
                obj.active_material_index = i
                _d(f"[ACTIVE] {obj.name} active_material_index fallback -> {i} '{mat_name(m)}'")
                return

    def _find_level_texture_material(self, base_name, tex_num):
        mat = None

        try:
            letter_name = int_to_texture(tex_num, name=base_name)
        except Exception:
            letter_name = None

        if letter_name:
            mat = self.find_material_loose(letter_name)
            if mat:
                return mat

        num = str(tex_num)
        candidates = []
        if base_name:
            candidates.extend([f"{base_name}{num}", f"{base_name}{num}.bmp"])
        candidates.extend([num, f"{num}.bmp"])

        for cand in candidates:
            mat = self.find_material_loose(cand)
            if mat:
                return mat

        return None

    def _reassign_faces_off_tex_vc(self, obj):
        mesh = obj.data

        is_edit_mode = obj.mode == 'EDIT'
        if is_edit_mode:
            bm = bmesh.from_edit_mesh(mesh)
        else:
            bm = bmesh.new()
            bm.from_mesh(mesh)

        texnum_layer = bm.faces.layers.int.get("Texture Number")
        if not texnum_layer:
            if not is_edit_mode:
                bm.free()
            _d(f"[TEXVC] {obj.name} no 'Texture Number' layer -> skip reassign")
            return

        scene = bpy.context.scene
        base_name = ""
        source_mode = ""
        matched = False

        if obj.get("is_model", False):
            for i in range(MAX_MODEL_SLOTS):
                nm = get_scene_value(scene, f"m_model_name_{i}", "")
                if not nm:
                    continue
                if clean_model_base_name(nm) in clean_model_base_name(obj.name):
                    source_mode = get_scene_value(scene, f"m_texture_mode_{i}", "VERTEX_COLOR")
                    p = get_scene_value(scene, f"m_texture_path_{i}", "")
                    if source_mode == "TEXTURE_NAME":
                        base_name = os.path.splitext(os.path.basename(p))[0].lower()
                    elif source_mode == "LEVEL_TEXTURES":
                        base_name = os.path.basename(p.rstrip("/\\")).lower()
                    matched = True
                    break

        is_car_part = self._is_car_part(obj)
        if not matched and not is_car_part:
            if obj.get("is_instance") and "fin_texture_base" in obj:
                base_name = obj["fin_texture_base"]
            else:
                base_prop = get_scene_value(scene, "level_texture_base", "")
                if base_prop:
                    base_name = os.path.splitext(base_prop.strip().lower())[0]
                else:
                    base_name = clean_model_base_name(obj.name, truncate=False)
            source_mode = "LEVEL_TEXTURES"

        if not matched and is_car_part:
            selected_car = _scene_str(scene, "selected_car_texture", "car.bmp")
            base_name = clean_model_base_name(selected_car)
            source_mode = "TEXTURE_NAME"

        touched = 0
        for face in bm.faces:
            cur = mesh.materials[face.material_index] if 0 <= face.material_index < len(mesh.materials) else None
            if not self._is_tex_vc_mat(cur):
                continue

            tex_num = face[texnum_layer]
            mat = None

            if source_mode == "TEXTURE_NAME":
                mat = self.find_material_loose(f"{base_name}.bmp")
            elif source_mode == "LEVEL_TEXTURES" and tex_num >= 0:
                mat = self._find_level_texture_material(base_name, tex_num)
            else:
                continue

            if not mat:
                continue
            if mat.name not in mesh.materials:
                mesh.materials.append(mat)

            face.material_index = mesh.materials.find(mat.name)
            touched += 1

        _d(f"[TEXVC] {obj.name} reassigned {touched} faces off TexVC (mode={source_mode} base='{base_name}')")

        if is_edit_mode:
            bmesh.update_edit_mesh(mesh, loop_triangles=False, destructive=False)
        else:
            bm.to_mesh(mesh)
            bm.free()
            mesh.update()

    # -------------------------------------------------------------------------
    # Main dispatcher per object
    # -------------------------------------------------------------------------

    def update_material_assignment(self, obj, existing_textures, material_choice):
        material_map = {
            'UV_TEX': '_UVTex',
            'COL': '_Col',
            'TEX_VC': '_TexVC',
            'ALPHA': '_Alpha',
            'ENV': '_Env',
            'RGB': '_RGBModelColor',
            'NCP': '_NCP'
        }

        material_suffix = material_map.get(material_choice, '_Col')

        _d(f"[DISPATCH] {obj.name} material_choice={material_choice} suffix={material_suffix}")
        _d_slots(obj, "DISPATCH_CUR")

        if material_choice == 'UV_TEX':
            _d(f"[DISPATCH] -> assign_uv_textures({obj.name})")
            self.assign_uv_textures(obj, existing_textures)
            self._reassign_faces_off_tex_vc(obj)
            self._remove_unreferenced_tex_vc_slots(obj)
            self._set_active_texture_material(obj)
            obj.data.update()
            obj.update_tag(refresh={'DATA'})

        elif material_choice == 'TEX_VC':
            _d(f"[DISPATCH] -> assign_tex_vc_materials({obj.name})")
            try:
                self.assign_tex_vc_materials(obj, existing_textures)
            except TypeError:
                self.assign_tex_vc_materials(obj)

        elif material_choice == 'RGB':
            _d(f"[DISPATCH] -> assign_rgb_modelcolor_materials({obj.name})")
            self.assign_rgb_modelcolor_materials(obj)

        elif material_choice == 'NCP':
            _d(f"[DISPATCH] -> assign_ncp_materials({obj.name})")
            self.assign_ncp_materials(obj)

        else:
            _d(f"[DISPATCH] -> assign_regular_materials({obj.name}, {material_suffix})")
            self.assign_regular_materials(obj, material_suffix)

        _d_slots(obj, "DISPATCH_AFTER")
        _d(f"[DISPATCH] {obj.name} active_material_index={obj.active_material_index} active='{obj.active_material.name if obj.active_material else None}'")

    # -------------------------------------------------------------------------
    # UV texture assignment (Texture Number layer)
    # -------------------------------------------------------------------------

    def assign_uv_textures(self, obj, existing_textures):
        _d(f"[UV] assign_uv_textures: {obj.name}")

        # Safety: in case something re-injects strings later
        sanitize_material_slots(obj)

        bm = bmesh.new()
        bm.from_mesh(obj.data)

        texnum_layer = bm.faces.layers.int.get("Texture Number")
        if not texnum_layer:
            texnum_layer = bm.faces.layers.int.new("Texture Number")
            for face in bm.faces:
                face[texnum_layer] = 0
            _d(f"[UV] {obj.name} created missing 'Texture Number' layer with default 0")

        scene = bpy.context.scene
        base_name = ""
        source_mode = ""
        matched = False

        if obj.get("is_model", False):
            for i in range(MAX_MODEL_SLOTS):
                slot_model_name = get_scene_value(scene, f"m_model_name_{i}", "")
                if not slot_model_name:
                    continue

                if clean_model_base_name(slot_model_name) in clean_model_base_name(obj.name):
                    source_mode = get_scene_value(scene, f"m_texture_mode_{i}", "VERTEX_COLOR")
                    texture_path = get_scene_value(scene, f"m_texture_path_{i}", "")

                    if source_mode == "TEXTURE_NAME":
                        base_name = os.path.splitext(os.path.basename(texture_path))[0].lower()
                    elif source_mode == "LEVEL_TEXTURES":
                        base_name = os.path.basename(texture_path.rstrip("/\\")).lower()

                    matched = True
                    _d(f"[UV] {obj.name} matched model slot {i}: mode={source_mode} base='{base_name}' path='{texture_path}'")
                    break

        is_car_part = self._is_car_part(obj)
        selected_car = _scene_str(scene, "selected_car_texture", "car.bmp")  # FIX: '' -> 'car.bmp'
        car_material = ensure_material_for_image(selected_car) if is_car_part else None

        if not matched and not is_car_part:
            if obj.get("is_instance") and "fin_texture_base" in obj:
                base_name = obj["fin_texture_base"]
            else:
                base_prop = get_scene_value(scene, "level_texture_base", "")
                if base_prop:
                    base_name = os.path.splitext(base_prop.strip().lower())[0]
                else:
                    base_name = clean_model_base_name(obj.name, truncate=False)
            source_mode = "LEVEL_TEXTURES"

        if not matched and is_car_part:
            base_name = clean_model_base_name(selected_car)
            source_mode = "TEXTURE_NAME"

        _d(
            f"[UV] {obj.name} is_car_part={is_car_part} matched={matched} "
            f"source_mode='{source_mode}' base_name='{base_name}' "
            f"selected_car='{selected_car}' car_material='{car_material.name if car_material else None}'"
        )

        for fi, face in enumerate(bm.faces):
            tex_num = face[texnum_layer]
            mat = None

            if source_mode == 'TEXTURE_NAME':
                want = f"{base_name}.bmp"
                mat = self.find_material_loose(want)
                if fi < 5:
                    _d(f"[UV] {obj.name} face#{fi} tex_num={tex_num} TEXTURE_NAME want='{want}' -> mat='{mat.name if mat else None}'")
            elif source_mode == 'LEVEL_TEXTURES' and tex_num >= 0:
                mat = self._find_level_texture_material(base_name, tex_num)
                if fi < 5:
                    _d(f"[UV] {obj.name} face#{fi} tex_num={tex_num} LEVEL_TEXTURES base='{base_name}' -> mat='{mat.name if mat else None}'")
            else:
                if fi < 5:
                    _d(f"[UV] {obj.name} face#{fi} SKIP source_mode='{source_mode}' tex_num={tex_num}")
                continue

            if not mat:
                if car_material:
                    mat = car_material
                    if fi < 5:
                        _d(f"[UV] {obj.name} face#{fi} fallback -> car_material='{mat.name}'")
                else:
                    if fi < 5:
                        _d(f"[UV] {obj.name} face#{fi} mat=None and no car_material -> continue")
                    continue

            if mat.name not in obj.data.materials:
                obj.data.materials.append(mat)
                _d(f"[UV] {obj.name} appended slot '{mat.name}'")

            face.material_index = obj.data.materials.find(mat.name)

        bm.to_mesh(obj.data)
        bm.free()
        obj.data.update()

    # -------------------------------------------------------------------------
    # Regular suffix-based material assignment
    # -------------------------------------------------------------------------

    def assign_regular_materials(self, obj, material_suffix):
        _d(f"[REG] assign_regular_materials: {obj.name} suffix={material_suffix}")

        base_name = self.get_current_base_name(obj)
        potential_names = [
            f"{base_name}{material_suffix}",
            f"{base_name}.prm{material_suffix}",
            f"{base_name}.w{material_suffix}",
            f"{base_name}.m{material_suffix}",
        ]

        _d(f"[REG] {obj.name} base_name='{base_name}' candidates={potential_names}")

        material = next((bpy.data.materials.get(n) for n in potential_names if bpy.data.materials.get(n)), None)
        if not material:
            material = bpy.data.materials.get(material_suffix)

        # NEW: if still not found, create one for COL or ALPHA
        if not material and material_suffix in {'_Col', '_Alpha'}:
            target_name = potential_names[0]  # e.g. 'car_Col' or 'car_Alpha'
            kind = 'COL' if material_suffix == '_Col' else 'ALPHA'
            material = ensure_vertex_layer_material(target_name, kind)
            _d(f"[REG] created '{material.name}' for kind={kind}")

        if not material:
            _d(f"[REG][WARN] {obj.name} material not found for suffix {material_suffix}")
            return

        if material.name not in obj.data.materials:
            obj.data.materials.append(material)
            _d(f"[REG] {obj.name} appended slot '{material.name}'")

        index = obj.data.materials.find(material.name)
        if index >= 0:
            obj.active_material_index = index
            _d(f"[REG] {obj.name} active_material_index={index} '{material.name}'")

        import bmesh
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        for face in bm.faces:
            face.material_index = index
        bm.to_mesh(obj.data)
        bm.free()
        obj.data.update()

    # -------------------------------------------------------------------------
    # Material lookup helper (+ debug)
    # -------------------------------------------------------------------------

    def find_material_loose(self, name):
        """Try to find a material with or without .bmp suffix (case-insensitive)."""
        if not name:
            _d("[MATFIND] name is empty")
            return None

        if name in bpy.data.materials:
            _d(f"[MATFIND] HIT exact '{name}'")
            return bpy.data.materials[name]
        if name.lower().endswith('.bmp') and name[:-4] in bpy.data.materials:
            _d(f"[MATFIND] HIT no-suffix '{name[:-4]}' (requested '{name}')")
            return bpy.data.materials[name[:-4]]
        if f"{name}.bmp" in bpy.data.materials:
            _d(f"[MATFIND] HIT add-suffix '{name}.bmp' (requested '{name}')")
            return bpy.data.materials[f"{name}.bmp"]

        target_lower = name.lower()
        target_base = target_lower[:-4] if target_lower.endswith('.bmp') else target_lower

        for mat in bpy.data.materials:
            m_lower = mat.name.lower()
            m_base = m_lower[:-4] if m_lower.endswith('.bmp') else m_lower
            if m_lower == target_lower or m_lower == f"{target_base}.bmp" or m_base == target_base:
                _d(f"[MATFIND] HIT case-insensitive requested='{name}' -> found='{mat.name}'")
                return mat

        _d(f"[MATFIND] MISS '{name}' (base='{target_base}')")
        return None

    # -------------------------------------------------------------------------
    # RGB Model Color material assignment
    # -------------------------------------------------------------------------

    def assign_rgb_modelcolor_materials(self, obj):
        print(f"[FAST] assign_rgb_modelcolor_materials: {obj.name}")

        mesh = obj.data

        # Both “roots”: raw object name and cleaned RV-style base
        raw_root = obj.name
        base_root = clean_model_base_name(obj.name)

        # Try both spellings just in case (Color / Colour)
        suffixes = ["_RGBModelColor", "_RGBModelColour"]

        mat = None

        # ------------------------------------------------------------------ #
        # 0) Prefer an existing RGBModelColor material already in the slots
        # ------------------------------------------------------------------ #
        for slot_mat in mesh.materials:
            if not slot_mat:
                continue
            if any(slot_mat.name.endswith(suf) for suf in suffixes):
                mat = slot_mat
                print(f"[DEBUG] Reusing existing RGB Model Color material from slot: "
                        f"'{slot_mat.name}' for {obj.name}")
                break

        # ------------------------------------------------------------------ #
        # 1) If not found, search by candidate names in bpy.data.materials
        # ------------------------------------------------------------------ #
        if not mat:
            candidate_names = []

            # Helper: strip known extensions (.prm, .w, .m) from raw_root for one variant
            def strip_known_ext(name):
                for ext in (".prm", ".w", ".m"):
                    if name.lower().endswith(ext):
                        return name[:-len(ext)]
                return name

            raw_no_ext = strip_known_ext(raw_root)

            roots = []
            if raw_no_ext:
                roots.append(raw_no_ext)
            if raw_root not in roots:
                roots.append(raw_root)
            if base_root and base_root not in roots:
                roots.append(base_root)

            for root in roots:
                for suf in suffixes:
                    candidate_names.extend([
                        f"{root}{suf}",        # tins_g_row_RGBModelColor or tins_g_r_RGBModelColor
                        f"{root}.prm{suf}",    # tins_g_row.prm_RGBModelColor, tins_g_r.prm_RGBModelColor
                        f"{root}.w{suf}",
                        f"{root}.m{suf}",
                    ])

            # Generic fallbacks
            candidate_names.extend([
                "RGBModelColor",
                "RGBModelColour",
                "_RGBModelColor",
                "_RGBModelColour",
            ])

            # Deduplicate while preserving order
            seen = set()
            ordered_candidates = []
            for name in candidate_names:
                if name not in seen:
                    seen.add(name)
                    ordered_candidates.append(name)

            for name in ordered_candidates:
                mat = bpy.data.materials.get(name)
                if mat:
                    print(f"[DEBUG] Reusing existing RGB Model Color material '{name}' for {obj.name}")
                    break

        # ------------------------------------------------------------------ #
        # 2) If still not found, create a new one (use raw_no_ext as base)
        # ------------------------------------------------------------------ #
        if not mat:
            # For new names, use the non-extended raw base so we get e.g. tins_g_row.prm_RGBModelColor
            def strip_known_ext(name):
                for ext in (".prm", ".w", ".m"):
                    if name.lower().endswith(ext):
                        return name[:-len(ext)]
                return name

            raw_no_ext = strip_known_ext(raw_root) or base_root or raw_root
            new_name = f"{raw_no_ext}.prm_RGBModelColor"

            print(f"[DEBUG] Creating new RGB Model Color material '{new_name}' for {obj.name}")
            mat = bpy.data.materials.new(name=new_name)
            mat.use_nodes = True

            nodes = mat.node_tree.nodes
            links = mat.node_tree.links

            # Clear default nodes
            for n in list(nodes):
                nodes.remove(n)

            # Attribute node reading the 'RGBModelColor' vcol layer
            attr_node = nodes.new(type='ShaderNodeAttribute')
            attr_node.attribute_name = "RGBModelColor"
            attr_node.attribute_type = 'GEOMETRY'

            # Principled BSDF + Output
            bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
            output = nodes.new(type='ShaderNodeOutputMaterial')

            links.new(attr_node.outputs['Color'], bsdf.inputs['Base Color'])
            bsdf.inputs['Alpha'].default_value = 1.0  # keep fully opaque
            links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

            if hasattr(mat, "blend_method"):
                mat.blend_method = 'OPAQUE'
            if hasattr(mat, "shadow_method"):
                mat.shadow_method = 'OPAQUE'

        # ------------------------------------------------------------------ #
        # 3) Make sure it is in the object material slots
        # ------------------------------------------------------------------ #
        if mat.name not in mesh.materials:
            mesh.materials.append(mat)

        index = mesh.materials.find(mat.name)
        if index < 0:
            print(f"[WARN] Could not find RGB Model Color material slot for {obj.name}")
            return

        # ------------------------------------------------------------------ #
        # 4) Assign it to all faces & make active
        # ------------------------------------------------------------------ #
        bm = bmesh.new()
        bm.from_mesh(mesh)
        for face in bm.faces:
            face.material_index = index
        bm.to_mesh(mesh)
        bm.free()
        mesh.update()

        obj.active_material_index = index
        print(f"[DEBUG] RGB Model Color material '{mat.name}' assigned to all faces on {obj.name}")


# -------------------------------------------------------------------------
# Auto operator
# -------------------------------------------------------------------------

class MaterialAssignmentAuto(MaterialAssignmentHelper, bpy.types.Operator):
    """Assign Materials to All Meshes Automatically"""
    bl_idname = "object.assign_materials_auto"
    bl_label = "Assign Materials Automatically"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        _d("[AUTO] Starting MaterialAssignmentAuto")

        if bpy.context.mode != 'OBJECT':
            _d("[AUTO] Switching to OBJECT mode")
            bpy.ops.object.mode_set(mode='OBJECT')

        mesh_objects = [obj for obj in bpy.data.objects if obj.type == 'MESH']
        _d(f"[AUTO] Found {len(mesh_objects)} mesh objects")

        if not mesh_objects:
            self.report({'WARNING'}, "No mesh objects found in the scene.")
            return {'CANCELLED'}

        scene = context.scene
        _d_scene_tex(scene)

        original_active_object = context.view_layer.objects.active

        material_choice = getattr(scene, "material_choice", None) or 'UV_TEX'
        _d(f"[AUTO] Scene material_choice={material_choice}")

        if material_choice in {"UV_TEX", "TEX_VC", "ENV", "ALPHA"}:
            base = get_scene_value(scene, "level_texture_base", "").strip()
            _d(f"[AUTO] level_texture_base check: base='{base}'")
            if not base:
                _d("[AUTO] CANCELLED: level_texture_base not set -> prompting")
                bpy.ops.scene.prompt_texture_base('INVOKE_DEFAULT')
                return {'CANCELLED'}

        existing_textures = self.get_existing_textures()
        _d(f"[AUTO] Found {len(existing_textures)} existing textures")

        for obj in mesh_objects:
            if hasattr(obj.data, "material_choice"):
                obj.data.material_choice = material_choice

        self.assign_materials_to_all(mesh_objects, existing_textures, material_choice)

        _d("[AUTO] Material assignment done, restoring selection")
        bpy.ops.object.select_all(action='DESELECT')
        for obj in mesh_objects:
            obj.select_set(True)

        if original_active_object and original_active_object.name in bpy.data.objects:
            context.view_layer.objects.active = original_active_object

        _d("[AUTO] MaterialAssignmentAuto finished successfully")
        return {'FINISHED'}

class MaterialAssignment(bpy.types.Operator):
    """Assign Materials to Selected Meshes Based on Material Choice"""
    bl_idname = "object.assign_materials"
    bl_label = "Assign Materials to Selected Meshes"
    bl_options = {'REGISTER', 'UNDO'}

    car_parts_prefixes = ["body", "wheel", "axle", "spring", "pin", "spinner"]

    def _is_car_part(self, obj):
        return getattr(obj, "is_car_part", False) or any(
            prefix in obj.name.lower() for prefix in self.car_parts_prefixes
        )

    def _find_level_texture_material(self, base_name, tex_num):
        """
        Local copy of the helper: resolve a level texture material for tex_num,
        supporting both letter and numeric naming.
        """
        mat = None

        # 1) Letter suffix (existing behaviour)
        try:
            letter_name = int_to_texture(tex_num, name=base_name)
        except Exception:
            letter_name = None

        if letter_name:
            mat = self.find_material_loose(letter_name)
            if mat:
                return mat

        # 2) Numeric variants
        num = str(tex_num)
        candidates = []
        if base_name:
            candidates.extend([
                f"{base_name}{num}",
                f"{base_name}{num}.bmp",
            ])
        candidates.extend([
            num,
            f"{num}.bmp",
        ])

        for cand in candidates:
            mat = self.find_material_loose(cand)
            if mat:
                return mat

        return None

    def execute(self, context):
        scene = context.scene

        # Prompt for level_texture_base if not set
        if not get_scene_value(scene, "level_texture_base", "").strip():
            bpy.ops.scene.prompt_texture_base('INVOKE_DEFAULT')
            return {'CANCELLED'}

        obj = context.active_object

        if obj is None:
            self.report({'WARNING'}, "No active object")
            return {'CANCELLED'}

        if obj.mode != 'EDIT':
            self.report({'WARNING'}, "Switch to Edit Mode.")
            return {'CANCELLED'}

        if obj.type != 'MESH':
            self.report({'WARNING'}, "Active object is not a mesh")
            return {'CANCELLED'}

        # ✔ FIXED: Use SCENE-LEVEL property, not mesh-level
        active_material_choice = scene.material_choice

        existing_textures = self.get_existing_textures()

        for obj in context.selected_objects:
            if obj.type == 'MESH':
                # No mesh-level property anymore — assignment comes from scene
                self.update_material_assignment(obj, existing_textures)

        return {'FINISHED'}

    def get_existing_textures(self):
        textures = {}
        for image in bpy.data.images:
            name_parts = image.name.rsplit('.', 1)
            if len(name_parts) > 1 and name_parts[-1].isalpha():
                textures[image.name] = name_parts[0]
        return textures

    def get_base_name_for_layers(self, obj):
        return clean_model_base_name(obj.name)

    def get_current_base_name(self, obj):
        if obj.get("is_instance") and "fin_texture_base" in obj:
            return obj["fin_texture_base"]

        if self._is_car_part(obj):
            scene = bpy.context.scene
            car_tex = _scene_str(scene, "selected_car_texture", "car.bmp")
            return clean_model_base_name(car_tex)

        model_name = clean_model_base_name(obj.name, truncate=False)

        if obj.get("is_model", False):
            scene = bpy.context.scene
            for i in range(MAX_MODEL_SLOTS):
                slot_name = get_scene_value(scene, f"m_model_name_{i}", "")
                tex_mode = get_scene_value(scene, f"m_texture_mode_{i}", "")
                tex_path = get_scene_value(scene, f"m_texture_path_{i}", "")

                if clean_model_base_name(slot_name, truncate=False) == model_name:
                    if tex_mode == "LEVEL_TEXTURES":
                        return os.path.basename(tex_path.rstrip("/\\")).lower()
                    elif tex_mode == "TEXTURE_NAME":
                        return os.path.splitext(os.path.basename(tex_path))[0].lower()
                    else:
                        return model_name

        return self.get_base_name_for_layers(obj)

    def update_material_assignment(self, obj, existing_textures):
        scene = bpy.context.scene

        material_map = {
            'UV_TEX': '_UVTex',
            'COL': '_Col',
            'TEX_VC': '_TexVC',
            'ALPHA': '_Alpha',
            'ENV': '_Env',
            'RGB': '_RGBModelColor',
            'NCP': '_NCP'
        }

        # ✔ FIXED: read scene-level choice
        material_choice = scene.material_choice
        material_suffix = material_map.get(material_choice, '_Col')

        if material_choice == 'UV_TEX':
            self.assign_uv_textures(obj, existing_textures)

        # Block TEX+VC for this operator (Selected)
        elif material_choice == 'TEX_VC':   # ← was active_material_choice
            self.report({'INFO'}, "TEX+VC can only be assigned via Set to All.")
            return {'CANCELLED'}

        elif material_choice == 'RGB':
            self.assign_rgb_modelcolor_materials(obj)

        elif material_choice == 'NCP':
            self.assign_ncp_materials(obj)

        else:
            self.assign_regular_materials(obj, material_suffix)

    # --- FIX 1: allow any selected mesh that's in EDIT mode (multi-object edit) ---

    def assign_uv_textures(self, obj, existing_textures):
        # Operate if this specific object is in EDIT mode (multi-object edit supported)
        if not obj.data.is_editmode:
            return
        bm = bmesh.from_edit_mesh(obj.data)
        if not bm:
            return

        texnum_layer = bm.faces.layers.int.get("Texture Number") or bm.faces.layers.int.new("Texture Number")
        scene = bpy.context.scene
        base_name_for_texture = ""
        source_mode = ""

        matched = False
        model_slot_index = -1

        if "is_model" in obj and obj["is_model"]:
            for i in range(MAX_MODEL_SLOTS):
                slot_model_name = get_scene_value(scene, f"m_model_name_{i}", "")
                if not slot_model_name:
                    continue

                if clean_model_base_name(slot_model_name) in clean_model_base_name(obj.name):
                    source_mode = get_scene_value(scene, f"m_texture_mode_{i}", "VERTEX_COLOR")
                    texture_path = get_scene_value(scene, f"m_texture_path_{i}", "")
                    model_slot_index = i

                    if source_mode == "TEXTURE_NAME":
                        base_name_for_texture = os.path.splitext(os.path.basename(texture_path))[0].lower()
                    elif source_mode == "LEVEL_TEXTURES":
                        base_name_for_texture = os.path.basename(texture_path.rstrip("/\\")).lower()

                    matched = True
                    break

        is_car_part = self._is_car_part(obj)
        car_material = ensure_material_for_image(get_scene_value(scene, "selected_car_texture", "car.bmp")) if is_car_part else None
        if not matched and not is_car_part:
            if obj.get("is_instance") and "fin_texture_base" in obj:
                base_name_for_texture = obj["fin_texture_base"]
            else:
                base_prop = get_scene_value(scene, "level_texture_base", "")
                if base_prop:
                    base_name_for_texture = os.path.splitext(base_prop.strip().lower())[0]
                else:
                    base_name_for_texture = clean_model_base_name(obj.name)
            source_mode = "LEVEL_TEXTURES"

        if not matched and is_car_part:
            fallback_name = get_scene_value(scene, "selected_car_texture", "car.bmp")
            base_name_for_texture = clean_model_base_name(fallback_name)
            source_mode = "TEXTURE_NAME"

        for face in bm.faces:
            if not face.select:
                continue

            tex_num = face[texnum_layer]
            mat = None

            if source_mode == 'TEXTURE_NAME':
                mat = self.find_material_loose(f"{base_name_for_texture}.bmp")
            elif source_mode == 'LEVEL_TEXTURES':
                if tex_num == -1:
                    continue
                # NEW: supports track1 / track0 / 1 / 0 patterns
                mat = self._find_level_texture_material(base_name_for_texture, tex_num)
            else:
                continue

            # Existing fallback: try current material slot if direct lookup failed
            if not mat:
                try:
                    slot_index = face.material_index
                    if slot_index < len(obj.data.materials):
                        candidate = obj.data.materials[slot_index].name
                        mat = bpy.data.materials.get(candidate) \
                            or bpy.data.materials.get(f"{candidate}.bmp") \
                            or (bpy.data.materials.get(candidate[:-4]) if candidate.endswith('.bmp') else None)
                except Exception:
                    pass

            if not mat and car_material:
                mat = car_material

            if not mat and is_car_part:
                fallback_name = get_scene_value(scene, "selected_car_texture", "car.bmp")
                mat = car_material or ensure_material_for_image(fallback_name)

            if not mat:
                continue

            if mat.name not in obj.data.materials:
                obj.data.materials.append(mat)

            face.material_index = obj.data.materials.find(mat.name)

        bmesh.update_edit_mesh(obj.data)
        obj.data.update()

# --- FIX 2: same idea for NCP materials ---

    def assign_ncp_materials(self, obj):
        if not obj.data.is_editmode:
            return
        bm = bmesh.from_edit_mesh(obj.data)
        if not bm:
            return

        material_layer = bm.faces.layers.int.get("Material") or bm.faces.layers.int.new("Material")

        for face in bm.faces:
            if not face.select:
                continue
            material_index = face[material_layer]
            if 0 <= material_index < len(MATERIALS):
                material_info = MATERIALS[material_index]
                material_name = material_info[1]

                mat = self.find_material_loose(material_name)
                if not mat:
                    mat = bpy.data.materials.new(name=material_name)
                    mat.use_nodes = True

                if mat.name not in obj.data.materials:
                    obj.data.materials.append(mat)

                face.material_index = obj.data.materials.find(mat.name)

        bmesh.update_edit_mesh(obj.data)
        obj.data.update()

    def assign_regular_materials(self, obj, material_suffix):
        base_name = self.get_current_base_name(obj)

        potential_names = [
            f"{base_name}{material_suffix}",
            f"{base_name}.prm{material_suffix}",
            f"{base_name}.w{material_suffix}",
            f"{base_name}.m{material_suffix}",
        ]

        material = None
        for mat_name in potential_names:
            material = bpy.data.materials.get(mat_name)
            if material:
                break
        if not material:
            material = bpy.data.materials.get(material_suffix)

        # NEW: create when missing for COL/ALPHA
        if not material and material_suffix in {'_Col', '_Alpha'}:
            target_name = potential_names[0]
            kind = 'COL' if material_suffix == '_Col' else 'ALPHA'
            material = ensure_vertex_layer_material(target_name, kind)

        if not material:
            return

        if material.name not in obj.data.materials:
            obj.data.materials.append(material)

        if obj.data.is_editmode:
            import bmesh
            bm = bmesh.from_edit_mesh(obj.data)
            idx = obj.data.materials.find(material.name)
            for face in bm.faces:
                if face.select:
                    face.material_index = idx
            bmesh.update_edit_mesh(obj.data, loop_triangles=False, destructive=False)
            obj.data.update()
        else:
            return

    def find_material_loose(self, name):
        """Try to find a material with or without .bmp suffix."""
        if name in bpy.data.materials:
            return bpy.data.materials[name]
        elif name.endswith('.bmp') and name[:-4] in bpy.data.materials:
            return bpy.data.materials[name[:-4]]
        elif f"{name}.bmp" in bpy.data.materials:
            return bpy.data.materials[f"{name}.bmp"]
        else:
            # Case-insensitive lookup to catch variants like CAR.bmp vs car.bmp
            target_lower = name.lower()
            target_base = target_lower[:-4] if target_lower.endswith('.bmp') else target_lower

            for mat in bpy.data.materials:
                m_lower = mat.name.lower()
                m_base = m_lower[:-4] if m_lower.endswith('.bmp') else m_lower

                if m_lower == target_lower or m_lower == f"{target_base}.bmp" or m_base == target_base:
                    return mat

        return None

class MaterialAssignmentImportExport(MaterialAssignmentHelper, bpy.types.Operator):
    """Assign Materials to All Meshes during Import / Export"""
    bl_idname = "object.assign_materials_impexp"
    bl_label = "Assign Materials Automatically"
    bl_options = {'REGISTER', 'UNDO'}

    car_parts_prefixes = ["body", "wheel", "axle", "spring", "pin", "spinner"]

    def _is_car_part(self, obj):
        return getattr(obj, "is_car_part", False) or any(
            prefix in obj.name.lower() for prefix in self.car_parts_prefixes
        )

    def _find_level_texture_material(self, base_name, tex_num):
        """
        Resolve a level texture material for tex_num using both
        classic letter suffixes and numeric variants.
        """
        mat = None

        try:
            letter_name = int_to_texture(tex_num, name=base_name)
        except Exception:
            letter_name = None

        if letter_name:
            mat = self.find_material_loose(letter_name)
            if mat:
                return mat

        num = str(tex_num)
        candidates = []
        if base_name:
            candidates.extend([
                f"{base_name}{num}",
                f"{base_name}{num}.bmp",
            ])
        candidates.extend([
            num,
            f"{num}.bmp",
        ])

        for cand in candidates:
            mat = self.find_material_loose(cand)
            if mat:
                return mat

        return None

    def execute(self, context):
        if bpy.context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        mesh_objects = [obj for obj in bpy.data.objects if obj.type == 'MESH']
        if not mesh_objects:
            self.report({'WARNING'}, "No mesh objects found in the scene.")
            return {'CANCELLED'}

        scene = context.scene

        # --- NEW: read the Scene-level enum you registered ---
        # You said you now have: bpy.types.Scene.material_choice = EnumProperty(...)
        material_choice = getattr(scene, "material_choice", None)
        if not material_choice:
            material_choice = 'UV_TEX'  # safe default
        print(f"[DEBUG][IMPEXP] Global material choice: {material_choice}")

        existing_textures = self.get_existing_textures()
        print(f"[DEBUG][IMPEXP] Found {len(existing_textures)} existing textures")

        # Optional: remember active object to restore later
        original_active_object = context.view_layer.objects.active

        # Run the actual assignment logic, now passing the choice through
        self.assign_materials_to_all(mesh_objects, existing_textures, material_choice)

        # Restore selection & active object as before
        bpy.ops.object.select_all(action='DESELECT')
        for obj in mesh_objects:
            obj.select_set(True)

        if original_active_object and original_active_object.name in bpy.data.objects:
            context.view_layer.objects.active = original_active_object

        return {'FINISHED'}

    def get_existing_textures(self):
        textures = {}
        for image in bpy.data.images:
            name_parts = image.name.rsplit('.', 1)
            if len(name_parts) > 1 and name_parts[-1].isalpha():
                textures[image.name] = name_parts[0]
        return textures

    def get_base_name_for_layers(self, obj):
        return clean_model_base_name(obj.name)

    def get_current_base_name(self, obj):
        if obj.get("is_instance") and "fin_texture_base" in obj:
            print(f"[DEBUG] Using fin_texture_base: {obj['fin_texture_base']} for {obj.name}")
            return obj["fin_texture_base"]

        if self._is_car_part(obj):
            scene = bpy.context.scene
            car_tex = get_scene_value(scene, "selected_car_texture", "car.bmp")
            return clean_model_base_name(car_tex)

        model_name = clean_model_base_name(obj.name, truncate=False)
        print(f"[DEBUG] checking model_name={model_name}, obj['is_model']={obj.get('is_model', False)}")

        if obj.get("is_model", False):
            scene = bpy.context.scene
            for i in range(MAX_MODEL_SLOTS):
                slot_name = get_scene_value(scene, f"m_model_name_{i}", "")
                tex_mode = get_scene_value(scene, f"m_texture_mode_{i}", "")
                tex_path = get_scene_value(scene, f"m_texture_path_{i}", "")
                print(f"[DEBUG] Slot {i}: m_model_name = '{slot_name}', mode = '{tex_mode}', path = '{tex_path}'")

                if clean_model_base_name(slot_name, truncate=False) == model_name:
                    if tex_mode == "LEVEL_TEXTURES":
                        return os.path.basename(tex_path.rstrip("/\\")).lower()
                    elif tex_mode == "TEXTURE_NAME":
                        return os.path.splitext(os.path.basename(tex_path))[0].lower()
                    else:
                        return model_name

        return self.get_base_name_for_layers(obj)

    # --- CHANGED SIGNATURE: pass material_choice through ---
    def assign_materials_to_all(self, mesh_objects, existing_textures, material_choice):
        original_mode = bpy.context.mode
        original_active = bpy.context.view_layer.objects.active

        # Ensure we start from Object mode to safely enter/exit Edit mode per object
        if original_mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        for obj in mesh_objects:
            if obj.type != 'MESH':
                continue

            if self._is_hull_part(obj):
                _d(f"[AUTO] Skipping hull object: {obj.name}")
                continue

            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj

            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')

            self.update_material_assignment(obj, existing_textures, material_choice)

            bpy.ops.object.mode_set(mode='OBJECT')

        # Restore the original active object and mode when possible
        if original_active and original_active.name in bpy.data.objects:
            bpy.context.view_layer.objects.active = original_active

        if original_mode != 'OBJECT':
            try:
                bpy.ops.object.mode_set(mode=original_mode)
            except Exception:
                pass

    # --- CHANGED SIGNATURE: material_choice comes from Scene, not obj.data ---
    def update_material_assignment(self, obj, existing_textures, material_choice):
        material_map = {
            'UV_TEX': '_UVTex',
            'COL': '_Col',
            'TEX_VC': '_TexVC',
            'ALPHA': '_Alpha',
            'ENV': '_Env',
            'RGB': '_RGBModelColor',
            'NCP': '_NCP'
        }

        # previously: material_choice = obj.data.material_choice
        # now: material_choice is given from Scene
        material_suffix = material_map.get(material_choice, '_Col')

        if material_choice == 'UV_TEX':
            self.assign_uv_textures(obj, existing_textures)
        elif material_choice == 'TEX_VC':
            auto_assigner = MaterialAssignmentHelper()

            try:
                auto_assigner.assign_tex_vc_materials(obj, existing_textures)
            except TypeError:
                auto_assigner.assign_tex_vc_materials(obj)

            auto_assigner._reassign_faces_off_tex_vc(obj)
            auto_assigner._remove_unreferenced_tex_vc_slots(obj)
            auto_assigner._set_active_texture_material(obj)

            obj.data.update()
            obj.update_tag(refresh={'DATA'})
        elif material_choice == 'NCP':
            self.assign_ncp_materials(obj)
        else:
            self.assign_regular_materials(obj, material_suffix)

    def assign_uv_textures(self, obj, existing_textures):
        mesh = obj.data

        # Defensive: repair slot corruption (strings instead of datablocks)
        sanitize_material_slots(obj)

        is_edit_mode = obj.mode == 'EDIT'
        if is_edit_mode:
            bm = bmesh.from_edit_mesh(mesh)
        else:
            bm = bmesh.new()
            bm.from_mesh(mesh)

        texnum_layer = bm.faces.layers.int.get("Texture Number") or bm.faces.layers.int.new("Texture Number")
        scene = bpy.context.scene
        base_name_for_texture = ""
        source_mode = ""

        matched = False
        model_slot_index = -1

        if "is_model" in obj and obj["is_model"]:
            for i in range(MAX_MODEL_SLOTS):
                slot_model_name = get_scene_value(scene, f"m_model_name_{i}", "")
                if not slot_model_name:
                    continue

                if clean_model_base_name(slot_model_name) in clean_model_base_name(obj.name):
                    source_mode = get_scene_value(scene, f"m_texture_mode_{i}", "VERTEX_COLOR")
                    texture_path = get_scene_value(scene, f"m_texture_path_{i}", "")
                    model_slot_index = i

                    if source_mode == "TEXTURE_NAME":
                        base_name_for_texture = os.path.splitext(os.path.basename(texture_path))[0].lower()
                    elif source_mode == "LEVEL_TEXTURES":
                        base_name_for_texture = os.path.basename(texture_path.rstrip("/\\")).lower()

                    matched = True
                    print(f"[IMPEXP][UV] Matched .m model slot {i} → name={slot_model_name}, base={base_name_for_texture}")
                    break

        is_car_part = self._is_car_part(obj)

        # IMPORTANT: treat '' / None / whitespace as missing and force a default
        selected_car = _scene_str(scene, "selected_car_texture", "car.bmp")
        car_material = ensure_material_for_image(selected_car) if is_car_part else None

        if not matched and not is_car_part:
            if obj.get("is_instance") and "fin_texture_base" in obj:
                base_name_for_texture = obj["fin_texture_base"]
            else:
                base_prop = get_scene_value(scene, "level_texture_base", "")
                if base_prop:
                    base_name_for_texture = os.path.splitext(base_prop.strip().lower())[0]
                else:
                    base_name_for_texture = clean_model_base_name(obj.name)
            source_mode = "LEVEL_TEXTURES"

        if not matched and is_car_part:
            base_name_for_texture = clean_model_base_name(selected_car)
            source_mode = "TEXTURE_NAME"

        print(
            f"[IMPEXP][UV] {obj.name} is_car_part={is_car_part} matched={matched} "
            f"source_mode='{source_mode}' base='{base_name_for_texture}' selected_car='{selected_car}' "
            f"car_mat={'None' if not car_material else car_material.name}"
        )

        for face in bm.faces:
            tex_num = face[texnum_layer]
            mat = None

            if source_mode == 'TEXTURE_NAME':
                mat = self.find_material_loose(f"{base_name_for_texture}.bmp")
            elif source_mode == 'LEVEL_TEXTURES':
                if tex_num == -1:
                    continue
                mat = self._find_level_texture_material(base_name_for_texture, tex_num)
            else:
                continue

            if not mat:
                # Existing “infer from slot” fallback
                slot_index = face.material_index
                if slot_index < len(mesh.materials):
                    candidate = mesh.materials[slot_index]
                    # candidate can be None
                    if candidate:
                        candidate_name = candidate.name
                        mat = bpy.data.materials.get(candidate_name)
                        if not mat and not candidate_name.endswith('.bmp'):
                            mat = bpy.data.materials.get(f"{candidate_name}.bmp")
                        elif not mat and candidate_name.endswith('.bmp'):
                            mat = bpy.data.materials.get(candidate_name[:-4])

            if not mat and car_material:
                mat = car_material

            if not mat and is_car_part:
                # hard fallback: still guarantee something if possible
                mat = ensure_material_for_image("car.bmp")

            if not mat:
                continue

            if mat.name not in mesh.materials:
                mesh.materials.append(mat)

            face.material_index = mesh.materials.find(mat.name)

        if is_edit_mode:
            bmesh.update_edit_mesh(mesh)
        else:
            bm.to_mesh(mesh)
            bm.free()
            mesh.update()

        if mesh.polygons:
            obj.active_material_index = mesh.polygons[0].material_index

    def assign_ncp_materials(self, obj):
        if not (bpy.context.view_layer.objects.active == obj and obj.mode == 'EDIT'):
            return

        bm = bmesh.from_edit_mesh(obj.data)
        if not bm:
            return

        material_layer = bm.faces.layers.int.get("Material") or bm.faces.layers.int.new("Material")

        for face in bm.faces:
            if face.select:
                material_index = face[material_layer]
                if 0 <= material_index < len(MATERIALS):
                    material_info = MATERIALS[material_index]
                    material_name = material_info[1]

                    mat = self.find_material_loose(material_name)
                    if not mat:
                        mat = bpy.data.materials.new(name=material_name)
                        mat.use_nodes = True

                    if mat.name not in obj.data.materials:
                        obj.data.materials.append(mat)

                    face.material_index = obj.data.materials.find(mat.name)

        bmesh.update_edit_mesh(obj.data)
        obj.data.update()

    def assign_regular_materials(self, obj, material_suffix):
        base_name = self.get_current_base_name(obj)

        potential_names = [
            f"{base_name}{material_suffix}",
            f"{base_name}.prm{material_suffix}",
            f"{base_name}.w{material_suffix}",
            f"{base_name}.m{material_suffix}"
        ]

        material = None
        for mat_name in potential_names:
            material = bpy.data.materials.get(mat_name)
            if material:
                break

        if not material:
            material = bpy.data.materials.get(material_suffix)

        # NEW: create when missing for COL/ALPHA
        if not material and material_suffix in {'_Col', '_Alpha'}:
            target_name = potential_names[0]
            kind = 'COL' if material_suffix == '_Col' else 'ALPHA'
            material = ensure_vertex_layer_material(target_name, kind)

        if not material:
            return

        if material.name not in obj.data.materials:
            obj.data.materials.append(material)

        if bpy.context.view_layer.objects.active == obj and obj.mode == 'EDIT':
            import bmesh
            bm = bmesh.from_edit_mesh(obj.data)
            material_index = obj.data.materials.find(material.name)
            for face in bm.faces:
                if face.select:
                    face.material_index = material_index
            bmesh.update_edit_mesh(obj.data)

    def find_material_loose(self, name):
        """Try to find a material with or without .bmp suffix."""
        if name in bpy.data.materials:
            return bpy.data.materials[name]
        elif name.endswith('.bmp') and name[:-4] in bpy.data.materials:
            return bpy.data.materials[name[:-4]]
        elif f"{name}.bmp" in bpy.data.materials:
            return bpy.data.materials[f"{name}.bmp"]
        else:
            # Case-insensitive lookup to catch variants like CAR.bmp vs car.bmp
            target_lower = name.lower()
            target_base = target_lower[:-4] if target_lower.endswith('.bmp') else target_lower

            for mat in bpy.data.materials:
                m_lower = mat.name.lower()
                m_base = m_lower[:-4] if m_lower.endswith('.bmp') else m_lower

                if m_lower == target_lower or m_lower == f"{target_base}.bmp" or m_base == target_base:
                    return mat

        return None

class TextureAssigner(bpy.types.Operator):
    """Assign selected texture to all selected mesh objects"""
    bl_idname = "object.assign_texture"
    bl_label = "Assign Texture to Meshes"
    bl_options = {'REGISTER', 'UNDO'}

    def get_texture_items(self, context):
        # Update the exclusion filter to check for partial names like 'carbox' and 'shadow' in the image name
        excluded_keywords = ["Render Result", "Viewer Node", "carbox", "shadow"]
    
        items = [
            (img.name, img.name, "") 
            for img in bpy.data.images 
            if not any(keyword in img.name for keyword in excluded_keywords)
        ]
    
        if not items:
            items.append(('None', 'No Textures Available', ''))
    
        return items

    texture_name: bpy.props.EnumProperty(
        name="Texture",
        description="Select a texture to assign",
        items=get_texture_items
    )

    def execute(self, context):
        selected_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
        
        if not selected_objects:
            # Display the message box if no mesh objects are selected
            msg_box("Select the car parts to apply skin", icon="ERROR")
            return {'CANCELLED'}

        image = bpy.data.images.get(self.texture_name)
        if not image:
            msg_box(f"Texture {self.texture_name} not found.", icon="ERROR")
            return {'CANCELLED'}

        for obj in selected_objects:
            if obj.type == 'MESH':
                self.assign_texture_to_object(obj, image)

        return {'FINISHED'}

    def assign_texture_to_object(self, obj, image):
        if obj.data.materials:
            mat = obj.data.materials[0]  # Assuming first material is the one to modify
        else:
            mat = bpy.data.materials.new(name="Material")
            obj.data.materials.append(mat)

        if not mat.use_nodes:
            mat.use_nodes = True
        
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links

        # Remove any existing texture nodes
        for node in nodes:
            if node.type == 'TEX_IMAGE':
                nodes.remove(node)

        # Add new texture node
        tex_image_node = nodes.new(type='ShaderNodeTexImage')
        tex_image_node.image = image
        tex_image_node.label = "Assigned Texture"

        # Connect to the principled BSDF node
        bsdf_node = nodes.get("Principled BSDF")
        if bsdf_node:
            links.new(tex_image_node.outputs['Color'], bsdf_node.inputs['Base Color'])

        print(f"Assigned texture {image.name} to {obj.name}")

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

class TexturesLoadFromDisk(bpy.types.Operator, ImportHelper):
    bl_idname = "helpers.textures_load_from_disk"
    bl_label = "Load Textures From Disk"
    bl_description = "Load all .bmp textures from a folder into Blender"
    bl_options = {'REGISTER', 'UNDO'}

    # We only care about the directory; this just helps the file browser
    filename_ext = ""

    filter_glob: bpy.props.StringProperty(
        default="*.bmp",
        options={'HIDDEN'},
    )

    def execute(self, context):
        import os
        import bpy

        # User picks any .bmp in the folder → we take the folder
        directory = os.path.dirname(self.filepath)
        if not os.path.isdir(directory):
            self.report({'ERROR'}, "Invalid directory selected.")
            return {'CANCELLED'}

        loaded = 0
        skipped = 0

        # Load all .bmp textures in that folder
        for name in sorted(os.listdir(directory)):
            if not name.lower().endswith(".bmp"):
                continue

            full_path = os.path.join(directory, name)
            if not os.path.isfile(full_path):
                continue

            try:
                # check_existing=True avoids duplicates if already loaded
                bpy.data.images.load(full_path, check_existing=True)
                loaded += 1
            except RuntimeError as e:
                print(f"[ERROR] Failed to load '{full_path}': {e}")
                skipped += 1

        msg = f"Loaded {loaded} texture(s) from '{directory}'."
        if skipped:
            msg += f" Skipped {skipped} file(s) that failed to load."
        self.report({'INFO'}, msg)

        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class SetFaceTextureNumber(bpy.types.Operator):
    bl_idname = "mesh.set_face_texnum"
    bl_label = "Set Face Texture Numbers From Materials"
    bl_description = (
        "Sets each face's 'Texture Number' based on the material's image suffix "
        "(base + letters). Also supports numeric names (e.g. '0', '12', '0.bmp'). "
        "Does not create or assign materials."
    )

    texture_base: bpy.props.StringProperty(
        name="Texture Base",
        description="Prefix for textures (e.g. 'box', 'kit_hexcity'). "
                    "Leave empty if textures are just 'a.bmp', 'aa.bmp', or '0.bmp', '12', etc.",
        default=""
    )

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        import bpy
        import bmesh

        try:
            from .common import TEX_PAGES_MAX
        except Exception:
            TEX_PAGES_MAX = 64  # fallback if not available

        base = self.texture_base.lower().strip()

        # Convert a base+suffix into a texture number (0..TEX_PAGES_MAX-1).
        # Supports:
        # - Alphabetic suffixes: a..z => 0..25, aa..zz => 26..701 (clamped)
        # - Numeric suffixes: "0", "12", "0.bmp", etc. => corresponding integer (clamped)
        # If base is empty, the entire name (minus extension) is treated as the suffix.
        def suffix_to_texnum(image_name: str) -> int:
            name = image_name.lower()

            # Strip common extensions (bmp, png, jpg, jpeg, tga, dds)
            for ext in (".bmp", ".png", ".jpg", ".jpeg", ".tga", ".dds"):
                if name.endswith(ext):
                    name = name[: -len(ext)]
                    break

            # Separate base and suffix
            if base:
                if not name.startswith(base):
                    return -1
                suffix = name[len(base):]
            else:
                suffix = name

            suffix = suffix.strip()
            if not suffix:
                return -1

            # First, try alphabetic mapping
            if suffix.isalpha():
                if len(suffix) == 1:
                    index = ord(suffix) - ord('a')
                else:
                    # 2+ letters; map like base-26 (aa=26, ab=27, ..., ba=52, ...)
                    index = 0
                    for ch in suffix:
                        v = ord(ch) - ord('a')
                        if v < 0 or v > 25:
                            return -1
                        index = index * 26 + (v + 1)
                    index -= 1  # convert from 1-based to 0-based

                return index if 0 <= index < TEX_PAGES_MAX else -1

            # Fallback: numeric mapping (e.g., "0", "12")
            if suffix.isdigit():
                try:
                    index = int(suffix)
                except ValueError:
                    return -1
                return index if 0 <= index < TEX_PAGES_MAX else -1

            # Unsupported suffix format
            return -1

        faces_updated = 0
        faces_set_invalid = 0

        for obj in context.scene.objects:
            if obj.type != 'MESH':
                continue

            is_edit = (obj.mode == 'EDIT')
            if is_edit:
                bm = bmesh.from_edit_mesh(obj.data)
            else:
                bm = bmesh.new()
                bm.from_mesh(obj.data)

            texnum_layer = bm.faces.layers.int.get("Texture Number")
            if not texnum_layer:
                texnum_layer = bm.faces.layers.int.new("Texture Number")

            obj_mats = list(obj.material_slots)

            for face in bm.faces:
                # Respect selected faces in Edit Mode
                if is_edit and not face.select:
                    continue

                tex_num = -1

                # Use the face's assigned material (material_index) to find an Image Texture
                mat_index = face.material_index
                if 0 <= mat_index < len(obj_mats):
                    mat_slot = obj_mats[mat_index]
                    mat = mat_slot.material if mat_slot else None
                    if mat and mat.use_nodes and mat.node_tree:
                        image = None
                        for node in mat.node_tree.nodes:
                            if node.type == 'TEX_IMAGE' and node.image:
                                image = node.image
                                break
                        if image:
                            tex_num = suffix_to_texnum(image.name)

                face[texnum_layer] = tex_num
                if tex_num >= 0:
                    faces_updated += 1
                else:
                    faces_set_invalid += 1

            if is_edit:
                bmesh.update_edit_mesh(obj.data)
            else:
                bm.to_mesh(obj.data)
                bm.free()

        self.report(
            {'INFO'},
            f"Updated Texture Number for {faces_updated} faces; {faces_set_invalid} faces set to -1."
        )
        return {'FINISHED'}

class ClearExtraAssignments(bpy.types.Operator):
    bl_idname = "mesh.clear_extra_assignments"
    bl_label = "Clear Extra Material Assignments"
    bl_description = "Assigns correct materials per face based on texture number (does not remove material slots)"

    texture_base: bpy.props.StringProperty(
        name="Texture Base",
        description="Base name for textures (e.g. 'track')",
        default=""
    )

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        base = self.texture_base.lower()
        special_names = {
            "_col", "_alpha", "_env", "_rgbmodelcolor",
            "none", "default", "marble", "stone", "wood", "sand", "plastic", "carpettile", "carpetshag",
            "boundary", "glass", "ice1", "metal", "grass", "bumpmetal", "pebbles", "gravel",
            "conveyor1", "conveyor2", "dirt1", "dirt2", "dirt3",
            "ice2", "ice3", "wood2", "conveyor_market1", "conveyor_market2", "paving"
        }

        for obj in context.scene.objects:
            if obj.type != 'MESH':
                continue

            is_edit = (obj.mode == 'EDIT' and obj == context.view_layer.objects.active)
            bm = bmesh.from_edit_mesh(obj.data) if is_edit else bmesh.new()
            if not is_edit:
                bm.from_mesh(obj.data)

            tex_layer = bm.faces.layers.int.get("Texture Number")
            if not tex_layer:
                if not is_edit:
                    bm.free()
                continue

            slot_map = {
                (slot.name.lower() if slot and slot.name else ""): i
                for i, slot in enumerate(obj.data.materials)
            }

            for face in bm.faces:
                tex_num = face[tex_layer]
                suffix = common.int_to_texture(tex_num, "")[:-4] if 0 <= tex_num <= 63 else None
                expected_name = f"{base}{suffix}.bmp" if suffix else None

                mat_index = face.material_index
                current_mat = obj.data.materials[mat_index] if mat_index < len(obj.data.materials) else None
                current_name = current_mat.name.lower() if current_mat else ""

                if current_name in special_names or current_name == expected_name:
                    continue

                if expected_name and expected_name in slot_map:
                    face.material_index = slot_map[expected_name]

            if is_edit:
                bmesh.update_edit_mesh(obj.data, destructive=False)
            else:
                bm.to_mesh(obj.data)
                bm.free()

        self.report({'INFO'}, "Face assignments adjusted to match texture numbers.")
        return {'FINISHED'}

class SetFaceTextureDropdown(bpy.types.Operator):
    bl_idname = "mesh.set_face_texture_dropdown"
    bl_label = "Set Texture and Assign"
    bl_description = "Set texture page number and assign material based on it"
    bl_options = {'REGISTER', 'UNDO'}

    def _assign_uv_materials_to_selected_faces(self, context, obj, texnum_layer):
        helper = MaterialAssignmentHelper()
        scene = context.scene

        base_name_for_texture = ""
        source_mode = ""
        matched = False

        if "is_model" in obj and obj["is_model"]:
            for i in range(MAX_MODEL_SLOTS):
                slot_model_name = get_scene_value(scene, f"m_model_name_{i}", "")
                if not slot_model_name:
                    continue

                if clean_model_base_name(slot_model_name) in clean_model_base_name(obj.name):
                    source_mode = get_scene_value(scene, f"m_texture_mode_{i}", "VERTEX_COLOR")
                    texture_path = get_scene_value(scene, f"m_texture_path_{i}", "")

                    if source_mode == "TEXTURE_NAME":
                        base_name_for_texture = os.path.splitext(os.path.basename(texture_path))[0].lower()
                    elif source_mode == "LEVEL_TEXTURES":
                        base_name_for_texture = os.path.basename(texture_path.rstrip("/\\")).lower()

                    matched = True
                    break

        is_car_part = helper._is_car_part(obj)
        car_material = ensure_material_for_image(get_scene_value(scene, "selected_car_texture", "car.bmp")) if is_car_part else None

        if not matched and not is_car_part:
            if obj.get("is_instance") and "fin_texture_base" in obj:
                base_name_for_texture = obj["fin_texture_base"]
            else:
                base_prop = get_scene_value(scene, "level_texture_base", "")
                if base_prop:
                    base_name_for_texture = os.path.splitext(base_prop.strip().lower())[0]
                else:
                    base_name_for_texture = clean_model_base_name(obj.name)
            source_mode = "LEVEL_TEXTURES"

        if not matched and is_car_part:
            fallback_name = get_scene_value(scene, "selected_car_texture", "car.bmp")
            base_name_for_texture = clean_model_base_name(fallback_name)
            source_mode = "TEXTURE_NAME"

        bm = bmesh.from_edit_mesh(obj.data)
        if not bm:
            return False

        updated = False
        for face in bm.faces:
            if not face.select:
                continue

            tex_num = face[texnum_layer]
            mat = None

            if source_mode == 'TEXTURE_NAME':
                mat = helper.find_material_loose(f"{base_name_for_texture}.bmp")
            elif source_mode == 'LEVEL_TEXTURES':
                if tex_num == -1:
                    continue
                mat = helper._find_level_texture_material(base_name_for_texture, tex_num)
            else:
                continue

            if not mat:
                try:
                    slot_index = face.material_index
                    if slot_index < len(obj.data.materials):
                        candidate = obj.data.materials[slot_index].name
                        mat = bpy.data.materials.get(candidate) \
                            or bpy.data.materials.get(f"{candidate}.bmp") \
                            or (bpy.data.materials.get(candidate[:-4]) if candidate.endswith('.bmp') else None)
                except Exception:
                    pass

            if not mat and car_material:
                mat = car_material

            if not mat and is_car_part:
                fallback_name = get_scene_value(scene, "selected_car_texture", "car.bmp")
                mat = car_material or ensure_material_for_image(fallback_name)

            if not mat:
                continue

            if mat.name not in obj.data.materials:
                obj.data.materials.append(mat)

            face.material_index = obj.data.materials.find(mat.name)
            updated = True

        bmesh.update_edit_mesh(obj.data)
        obj.data.update()
        return updated

    texture_page: bpy.props.EnumProperty(
        name="Texture Page",
        items=lambda self, context: [
            ("-1", "Texture Page (NONE) (-1)", ""),
            *[
                (str(i), f"Texture Page {i + 1} ({int_to_texture(i)[:-4].upper()})", "")
                for i in range(TEX_PAGES_MAX)
            ]
        ]
    )

    def find_material_loose(self, name):
        if name in bpy.data.materials:
            return bpy.data.materials[name]
        elif name.endswith('.bmp') and name[:-4] in bpy.data.materials:
            return bpy.data.materials[name[:-4]]
        elif f"{name}.bmp" in bpy.data.materials:
            return bpy.data.materials[f"{name}.bmp"]
        else:
            # Case-insensitive lookup to catch variants like CAR.bmp vs car.bmp
            target_lower = name.lower()
            target_base = target_lower[:-4] if target_lower.endswith('.bmp') else target_lower

            for mat in bpy.data.materials:
                m_lower = mat.name.lower()
                m_base = m_lower[:-4] if m_lower.endswith('.bmp') else m_lower

                if m_lower == target_lower or m_lower == f"{target_base}.bmp" or m_base == target_base:
                    return mat

        return None

    def invoke(self, context, event):
        obj = context.active_object
        if obj and obj.type == 'MESH' and obj.mode == 'EDIT':
            bm = bmesh.from_edit_mesh(obj.data)
            tex_layer = bm.faces.layers.int.get("Texture Number")
            if not tex_layer:
                tex_layer = bm.faces.layers.int.new("Texture Number")
                # Initialize all face values to -1 by default
                for face in bm.faces:
                    face[tex_layer] = -1

            selected = [f for f in bm.faces if f.select]
            if selected:
                tex = selected[0][tex_layer]
                if all(f[tex_layer] == tex for f in selected):
                    self.texture_page = str(tex if tex >= 0 else -1)

        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        tex_num = int(self.texture_page)
        obj = context.active_object
        if not obj or obj.type != 'MESH' or obj.mode != 'EDIT':
            self.report({'WARNING'}, "Select a mesh in Edit mode.")
            return {'CANCELLED'}

        bm = bmesh.from_edit_mesh(obj.data)
        tex_layer = bm.faces.layers.int.get("Texture Number")
        if not tex_layer:
            tex_layer = bm.faces.layers.int.new("Texture Number")
            for face in bm.faces:
                face[tex_layer] = -1

        for face in bm.faces:
            if face.select:
                face[tex_layer] = tex_num

        bmesh.update_edit_mesh(obj.data)
        obj.data.update()

        if tex_num == -1:
            self.report({'INFO'}, "Texture set to NONE (-1), no material assignment.")
            return {'FINISHED'}

        scene = context.scene
        material_choice = getattr(scene, "material_choice", "UV_TEX")
        if material_choice == "TEX_VC":
            updated = self._assign_uv_materials_to_selected_faces(context, obj, tex_layer)
            helper = MaterialAssignmentHelper()
            existing_textures = helper.get_existing_textures()
            helper.assign_tex_vc_materials(obj, existing_textures)
            if updated:
                self.report({'INFO'}, "Texture page updated and TEX+VC materials refreshed.")
            else:
                self.report({'INFO'}, "Texture page updated. TEX+VC materials refreshed.")
            return {'FINISHED'}

        guessed_base = get_scene_value(scene, "level_texture_base", "")
        material_name = int_to_texture(tex_num, name=guessed_base)

        # Use loose material lookup instead of direct get
        mat = self.find_material_loose(material_name)
        if not mat:
            bpy.ops.scene.prompt_texture_base('INVOKE_DEFAULT')
            self.report({'WARNING'}, f"Material '{material_name}' not found. Prompting for level texture base.")
            return {'FINISHED'}

        bpy.ops.object.assign_materials()
        return {'FINISHED'}

class SetLevelTexturePrefix(bpy.types.Operator):
    bl_idname = "scene.prompt_texture_base"
    bl_label = "Enter Texture Base Name"

    texture_base: bpy.props.StringProperty(
        name="Texture Base",
        description="Prefix for textures (e.g. 'box', 'arena')",
        default=""
    )

    use_car_texture: bpy.props.BoolProperty(
        name="Use Car Texture",
        description="If checked, sets 'car' as the texture base (used for cars)",
        default=False
    )

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "use_car_texture")
        if not self.use_car_texture:
            layout.prop(self, "texture_base")

    def execute(self, context):
        if self.use_car_texture:
            set_scene_value(context.scene, "level_texture_base", "car")
            self.report({'INFO'}, "Set level texture base to: car")
        else:
            set_scene_value(context.scene, "level_texture_base", self.texture_base.strip().lower())
            self.report({'INFO'}, f"Set level texture base to: {self.texture_base}")
        return {'FINISHED'}

"""
OBJECTS -----------------------------------------------------------------------
"""
    
class SetBCubeMeshIndices(bpy.types.Operator):
    bl_idname = "object.set_bcube_mesh_indices"
    bl_label = "Set BCube Mesh Indices"
    
    def execute(self, context):
        obj = context.object
        
        # Initialize the bcube_mesh_indices property with an empty string
        obj.bcube_mesh_indices = ""
        
        # Iterate through child meshes and concatenate their names
        for child_obj in obj.children:
            if child_obj.type == 'MESH':
                if obj.bcube_mesh_indices:
                    obj.bcube_mesh_indices += ","
                # Append the mesh name or another unique identifier
                obj.bcube_mesh_indices += child_obj.data.name
        
        self.report({'INFO'}, f"BCube mesh indices set for {obj.name}.")
        return {'FINISHED'}
  
class ButtonHullGenerate(bpy.types.Operator):
    bl_idname = "hull.generate"
    bl_label = "Generate Convex Hull"
    bl_description = "Generates a convex hull from the selected object"
    
    @classmethod
    def poll(cls, context):
        return context.active_object is not None and context.active_object.type == 'MESH'

    def execute(self, context):
        hull_object = generate_chull(context)
        if hull_object:
            self.report({'INFO'}, "Convex hull generated successfully.")
        else:
            self.report({'ERROR'}, "Convex hull generation failed. Check the console for details.")
        return {'FINISHED'}    

class MarkAsModel(bpy.types.Operator):
    bl_idname = "object.mark_as_model"
    bl_label = "Mark as .m Model"
    bl_description = "Marks this object as a .m model and sets texture slot info"
    bl_options = {'REGISTER', 'UNDO'}

    model_name: bpy.props.StringProperty(
        name="Model Name",
        description="Internal name to register this model as (max 8 characters)",
        default=""
    )

    texture_source: bpy.props.EnumProperty(
        name="Texture Source",
        items=[
            ('LEVEL_TEXTURES', "Level Textures", "Uses suffix-based level textures like toy2a.bmp"),
            ('TEXTURE_NAME', "Texture Name", "Uses exact texture like fxpage1.bmp or car.bmp")
        ],
        default='LEVEL_TEXTURES'
    )

    source_name: bpy.props.StringProperty(
        name="Source Name",
        description="Level base name (e.g. 'toy2') or texture filename (e.g. 'car.bmp')",
        default=""
    )

    def invoke(self, context, event):
        obj = context.active_object
        if not obj:
            return {'CANCELLED'}

        if getattr(obj, "is_model", False):
            return self.execute(context)

        self.model_name = obj.name.split('.')[0].lower()
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "model_name")
        layout.prop(self, "texture_source")
        layout.prop(self, "source_name")

    def execute(self, context):
        obj = context.active_object
        scene = context.scene
        # Store full logical name in the editor
        base_name = clean_model_base_name(self.model_name.strip().lower(), truncate=False)

        if not base_name:
            self.report({'ERROR'}, "Model name cannot be empty")
            return {'CANCELLED'}

        # Unmark if already marked
        if getattr(obj, "is_model", False):
            obj.is_model = False
            for i in range(MAX_MODEL_SLOTS):
                if clean_model_base_name(get_scene_value(scene, f"m_model_name_{i}", "").lower()) == base_name:
                    set_scene_value(scene, f"m_model_name_{i}", "")
                    set_scene_value(scene, f"m_texture_mode_{i}", "")
                    set_scene_value(scene, f"m_texture_path_{i}", "")
                    self.report({'INFO'}, f"Unmarked {obj.name} and cleared texture slot {i}")
                    return {'FINISHED'}

        # Mark as model
        obj.is_model = True

        cleaned_source = self.source_name.strip().lower()
        if self.texture_source == 'TEXTURE_NAME':
            texture_path = f"{os.path.splitext(cleaned_source)[0]}.bmp"
        else:  # LEVEL_TEXTURES
            texture_path = os.path.splitext(cleaned_source)[0]  # remove .bmp if present

        for i in range(MAX_MODEL_SLOTS):
            if not get_scene_value(scene, f"m_model_name_{i}", ""):
                set_scene_value(scene, f"m_model_name_{i}", base_name)
                set_scene_value(scene, f"m_texture_mode_{i}", self.texture_source)
                set_scene_value(scene, f"m_texture_path_{i}", texture_path)
                self.report({'INFO'}, f"Marked {obj.name} as '{base_name}' in slot {i}")
                return {'FINISHED'}

        self.report({'WARNING'}, "No free texture slots available.")
        return {'CANCELLED'}
