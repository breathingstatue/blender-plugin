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
import subprocess
import shutil
import bmesh
import math
import mathutils
from mathutils import Vector as BlenderVector
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
from .common import FORMAT_TAZ, FORMAT_TRI, FORMAT_UNK, MATERIALS, COLORS, FORMAT_FOB, FORMAT_FAN, FORMAT_PAN, FORMAT_LIT, FORMAT_VIS
from .common import get_model_materials, get_errors, msg_box, FORMATS, to_revolt_scale, FORMAT_CAR, TEX_PAGES_MAX, int_to_texture
from .common import to_revolt_coord, clean_model_base_name, set_level_texture_base_from_filepath, create_directional_fob_mesh
from .common import get_scene_value, set_scene_value
from .common import generate_fob_name, create_directional_fob_mesh_ui
from .layers import set_face_env, create_or_assign_env_material
from .parameters_out_redux import append_aerial_info, append_axle_info, append_back_left_wheel, append_back_right_wheel
from .parameters_out_redux import append_front_left_wheel, append_front_right_wheel, append_pin_info, append_spring_info
from .parameters_out_redux import compare_and_adjust_axle_lengths, remove_imported_axles, compare_and_adjust_spring_lengths
from .parameters_out_redux import remove_imported_springs, compare_and_adjust_pin_lengths, remove_imported_pins
from .taz_in import create_zone
from .texanim import copy_frame_to_uv, copy_uv_to_frame
from .tools import trigger_type_items, fob_type_items, visibox_type_items, get_rig_objects, get_rig_root, rig_world_bbox_center
from .tri_in import create_trigger

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

def update_file_extension(operator_instance):
    # Mapping from format type to extension
    ext_mapping = {
        'CAR': '.txt',
        'FIN': '.fin',
        'FOB': '.fob',
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
    ext = ext_mapping.get(operator_instance.format_type, "")
    operator_instance.filename_ext = ext
    operator_instance.filter_glob = f"*{ext}"
    
"""
BUTTONS ------------------------------------------------------------------------
"""

class RVIO_OT_SelectRevoltDirectory(bpy.types.Operator):
    bl_idname = "rvio.select_rvgl_dir"
    bl_label = "Select Re-Volt Directory"
    bl_description = "Select the directory where RVGL is located"

    directory: bpy.props.StringProperty(subtype='DIR_PATH')

    def execute(self, context):
        context.scene.rvgl_dir = self.directory
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
    

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

            elif frmt == FORMAT_HUL:
                from . import hul_in
                hul_in.import_file(self.filepath, scene)

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
            ('HUL',  "HUL (.hul)", "Hull file"),
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
            ".fin": "FIN", ".fob": "FOB", ".hul": "HUL",
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
            "FIN", "FOB", "HUL", "NCP", "PRM", "RIM",
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
        layout.label(text="Car Texture:")
        layout.prop(self, "texture_name")
        layout.separator()
        layout.label(text="Level Texture Base:")
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
    bl_description = "Read car parameters from parameters.txt file"

    # Filepath handler
    filepath: bpy.props.StringProperty(subtype="FILE_PATH")
    directory: bpy.props.StringProperty(subtype="DIR_PATH")

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
        formatted_str = ""
        for key, value in parameters.items():
            if key == 'model':
                formatted_str += f"{key}:\n"
                for model_key, model_value in value.items():
                    formatted_str += f"  {model_key}: {model_value}\n"
            elif key in ['wheel', 'spring', 'pin', 'axle', 'spinner', 'aerial', 'body']:
                formatted_str += f"{key}:\n"
                if isinstance(value, dict):
                    for sub_key, sub_value in value.items():
                        formatted_str += f"  {sub_key}:\n"
                        if isinstance(sub_value, dict):
                            for sub_sub_key, sub_sub_value in sub_value.items():
                                formatted_str += f"    {sub_sub_key}: {sub_sub_value}\n"
                        else:
                            formatted_str += f"    {sub_value}\n"
                elif isinstance(value, list):
                    for item in value:
                        formatted_str += f"  - {item}\n"
            else:
                formatted_str += f"{key}: {value}\n"
        return formatted_str

    def invoke(self, context, event):
        rvgl_dir = context.scene.rvgl_dir
        # Use the RVGL directory if set, otherwise start in the default directory
        if rvgl_dir and os.path.isdir(rvgl_dir):
            cars_folder = os.path.join(rvgl_dir, "cars")
            if os.path.isdir(cars_folder):
                self.directory = cars_folder
            else:
                self.report({'INFO'}, "RVGL '/cars' subfolder not found. Browse to locate parameters.txt.")
        else:
            self.report({'INFO'}, "RVGL directory not set. Browse to locate parameters.txt.")

        # Open the file browser
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

class LaunchRV(bpy.types.Operator):
    bl_idname = "helpers.launch_rv"
    bl_label = "Launch RVGL"
    bl_description = "Launches the game"

    def execute(self, context):
        rvgl_dir = context.scene.rvgl_dir  # Assuming rvgl_dir is properly set from the scene
        if not rvgl_dir or not os.path.isdir(rvgl_dir):
            self.report({'WARNING'}, f"RVGL directory '{rvgl_dir}' is not set or invalid.")
            return {'CANCELLED'}

        executable_path = None
        if "rvgl.exe" in os.listdir(rvgl_dir):
            executable_path = os.path.join(rvgl_dir, "rvgl.exe")
        elif "rvgl" in os.listdir(rvgl_dir):
            executable_path = os.path.join(rvgl_dir, "rvgl")

        if executable_path and os.path.isfile(executable_path):
            subprocess.Popen([executable_path], cwd=rvgl_dir)
            return {'FINISHED'}
        else:
            self.report({'WARNING'}, f"RVGL executable not found in '{rvgl_dir}'.")
            return {'CANCELLED'}

        # Default return statement as a fallback
        return {'CANCELLED'}

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
        description="Automatically rename materials to match texture names (.bmp)",
        default=True
    )

    def execute(self, context):
        import shutil

        directory = os.path.dirname(self.filepath)
        if not os.path.isdir(directory):
            self.report({'ERROR'}, "Invalid directory selected.")
            return {'CANCELLED'}

        renamed = 0
        saved = 0

        # 1. Fix mismatched material names
        for mat in bpy.data.materials:
            if not mat.use_nodes:
                continue
            for node in mat.node_tree.nodes:
                if node.type == 'TEX_IMAGE' and node.image:
                    expected_name = f"{node.image.name}.bmp"
                    if mat.name != expected_name:
                        if self.auto_fix:
                            print(f"[INFO] Renaming material '{mat.name}' → '{expected_name}'")
                            mat.name = expected_name
                            renamed += 1
                        else:
                            self.report({'WARNING'}, f"Material '{mat.name}' mismatch. Enable Auto-Rename to fix.")
                            return {'CANCELLED'}

        if renamed:
            self.report({'INFO'}, f"Renamed {renamed} materials to match texture names.")

        # 2. Save each image as .bmp
        for image in bpy.data.images:
            if image.source != 'FILE' or image.users == 0:
                continue

            base_name = os.path.splitext(image.name)[0][:8]
            if self.texture_base:
                base_name = self.texture_base[:8]

            filename = f"{base_name}.bmp"
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
    bl_idname = "helpers.texture_rename"
    bl_label = "Rename Texture"
    bl_description = "Rename texture(s) and materials based on tex_num assignments, fallback to order"
    bl_options = {'REGISTER', 'UNDO'}

    base_name: bpy.props.StringProperty(
        name="Base Name",
        description="Base name for textures and materials (e.g. 'track')",
        maxlen=64
    )

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def split_name_suffix(self, name):
        """Splits name like 'trackaa' into ('track', 'aa')"""
        name = name.lower().strip().removesuffix(".bmp")
        match = re.match(r"^(.*?)([a-z]{1,2})$", name)
        if match:
            return match.group(1), match.group(2)
        return name, ""

    def valid_suffix_for(self, tex_num, suffix):
        return suffix == int_to_texture(tex_num, "")[:-4]

    def execute(self, context):
        if not self.base_name:
            self.report({'WARNING'}, "No base name provided")
            return {'CANCELLED'}

        texnum_map = {}
        used_images = set()
        used_suffixes = set()
        used_material_names = set()

        # 1. Scan tex_num from selected mesh faces
        for obj in context.selected_objects:
            if obj.type != 'MESH':
                continue

            bm = bmesh.new()
            bm.from_mesh(obj.data)
            tex_layer = bm.faces.layers.int.get("Texture Number")
            if not tex_layer:
                bm.free()
                continue

            for face in bm.faces:
                tex_num = face[tex_layer]
                if tex_num < 0:
                    continue

                mat_idx = face.material_index
                if mat_idx >= len(obj.data.materials):
                    continue
                mat = obj.data.materials[mat_idx]
                if not mat or not mat.use_nodes:
                    continue

                for node in mat.node_tree.nodes:
                    if node.type == 'TEX_IMAGE' and node.image:
                        if tex_num not in texnum_map:
                            texnum_map[tex_num] = node.image
                        used_images.add(node.image)
                        suffix = int_to_texture(tex_num, "")[:-4]
                        used_suffixes.add(suffix)
                        break
            bm.free()

        # 2. Rename tex_num-mapped textures and materials
        for tex_num, image in texnum_map.items():
            suffix = int_to_texture(tex_num, "")[:-4]
            new_name = f"{self.base_name}{suffix}"
            expected_mat_name = f"{new_name}.bmp"

            base_candidate, suffix_candidate = self.split_name_suffix(image.name)
            if base_candidate != self.base_name.lower() or not self.valid_suffix_for(tex_num, suffix_candidate):
                print(f"[RENAME] tex_num {tex_num} → {image.name} → {new_name}")
                image.name = new_name
            used_suffixes.add(suffix)

            for mat in bpy.data.materials:
                if not mat.use_nodes:
                    continue
                for node in mat.node_tree.nodes:
                    if node.type == 'TEX_IMAGE' and node.image == image:
                        base_mat, suff_mat = self.split_name_suffix(mat.name)
                        if base_mat != self.base_name.lower() or not self.valid_suffix_for(tex_num, suff_mat):
                            if expected_mat_name not in used_material_names:
                                print(f"[RENAME] Material {mat.name} → {expected_mat_name}")
                                mat.name = expected_mat_name
                                used_material_names.add(expected_mat_name)

        # 3. Gather fallback images
        available_images = [
            img for img in bpy.data.images
            if img.source == 'FILE' and img.users > 0 and
            img not in used_images and 'Viewer Node' not in img.name and 'Render Result' not in img.name
        ]
        available_images.sort(key=lambda x: x.name)

        # 4. Pre-reserve suffixes found in existing images (regardless of base)
        image_suffix_map = {}
        for image in available_images:
            _, suffix_candidate = self.split_name_suffix(image.name)
            if (
                1 <= len(suffix_candidate) <= 2
                and suffix_candidate.isalpha()
                and suffix_candidate not in used_suffixes
            ):
                print(f"[RESERVE] Suffix '{suffix_candidate}' found in {image.name}")
                used_suffixes.add(suffix_candidate)
                image_suffix_map[image] = suffix_candidate

        # 5. Rename fallback textures and materials
        index = 0
        for image in available_images:
            if image in texnum_map.values():
                continue  # already handled via tex_num

            # a) Reuse existing suffix if reserved earlier
            if image in image_suffix_map:
                suffix = image_suffix_map[image]
                new_name = f"{self.base_name}{suffix}"
                expected_mat_name = f"{new_name}.bmp"
                print(f"[BASE CHANGE] {image.name} → {new_name}")
                image.name = new_name
                used_suffixes.add(suffix)
                used_images.add(image)

                for mat in bpy.data.materials:
                    if not mat.use_nodes:
                        continue
                    for node in mat.node_tree.nodes:
                        if node.type == 'TEX_IMAGE' and node.image == image:
                            print(f"[BASE CHANGE] Material {mat.name} → {expected_mat_name}")
                            mat.name = expected_mat_name
                            used_material_names.add(expected_mat_name)
                continue

            # b) Assign next available suffix
            while True:
                suffix = int_to_texture(index, "")[:-4]
                new_name = f"{self.base_name}{suffix}"
                expected_mat_name = f"{new_name}.bmp"
                if suffix not in used_suffixes and expected_mat_name not in used_material_names:
                    break
                index += 1

            print(f"[FALLBACK] {image.name} → {new_name}")
            image.name = new_name
            used_suffixes.add(suffix)
            used_images.add(image)

            for mat in bpy.data.materials:
                if not mat.use_nodes:
                    continue
                for node in mat.node_tree.nodes:
                    if node.type == 'TEX_IMAGE' and node.image == image:
                        print(f"[FALLBACK] Material {mat.name} → {expected_mat_name}")
                        mat.name = expected_mat_name
                        used_material_names.add(expected_mat_name)
            index += 1

        self.report({'INFO'}, f"Textures renamed using base '{self.base_name}'")
        return {'FINISHED'}
    
class CopyWheelParams(bpy.types.Operator):
    bl_idname = "headers.copy_wheel_params"
    bl_label = "Copy Wheel Parameters"
    bl_description = "Copies wheel parameters into clipboard"

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
    bl_description = "Copies aerial parameters into clipboard"

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
    
"""
MAKEITGOOD SECTOR & HULL SPHERE -------------------------------------------------------
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

class CreateFobObject(bpy.types.Operator):
    bl_idname = "object.create_fob"
    bl_label = "Create FOB Object"
    bl_description = "Create a new FOB game object with editable properties"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj_id = int(context.scene.selected_fob_object_id)
        subinfos = [0, 0, 0, 0]
        name, creation_index = generate_fob_name(obj_id)

        fob_obj = create_directional_fob_mesh(name)

        # Apply -90 degrees X rotation
        rot_x_minus_90 = mathutils.Matrix.Rotation(math.radians(-90), 4, 'X')
        fob_obj.matrix_world = rot_x_minus_90 @ fob_obj.matrix_world

        # Set position at cursor
        fob_obj.location = context.scene.cursor.location

        # Assign properties
        fob_obj["is_fob_object"] = True
        fob_obj["fob_type"] = obj_id
        fob_obj["fob_creation_index"] = creation_index
        for i in range(4):
            fob_obj[f"fob_subtype_{i+1}"] = subinfos[i]

        # Link to collection
        collection = bpy.data.collections.get("FOB_OBJECTS")
        if collection:
            collection.objects.link(fob_obj)
        else:
            context.collection.objects.link(fob_obj)

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
        name, creation_index = generate_fob_name(obj_id)

        new_obj = create_directional_fob_mesh_ui(name)
        # Rotate the object 90 degrees in X
        rot_x_90 = mathutils.Matrix.Rotation(math.radians(90), 4, 'X')
        new_obj.matrix_world = rot_x_90 @ new_obj.matrix_world
        new_obj.location = obj.location + BlenderVector((1, 1, 0))

        new_obj["is_fob_object"] = True
        new_obj["fob_type"] = obj_id
        new_obj["fob_creation_index"] = creation_index
        for i in range(4):
            new_obj[f"fob_subtype_{i+1}"] = int(obj.get(f"fob_subtype_{i+1}", 0))

        collection = bpy.data.collections.get("FOB_OBJECTS")
        if collection:
            collection.objects.link(new_obj)
        else:
            context.collection.objects.link(new_obj)

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
        index = 1
        while f"Visibox_{index:02d}" in bpy.data.objects:
            index += 1
        return f"Visibox_{index:02d}"
    
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

    category: EnumProperty(
        name="Category",
        items=[
            ('TRIGGER', "Trigger", ""),
            ('FOB', "FOB Object", ""),
            ('TRACK_ZONE', "Track Zone", ""),
            ('VISIBOX', "Visibox", ""),
        ],
        update=lambda self, context: self._update_subtype_items(context)
    )

    trigger_type: EnumProperty(name="Trigger Type", items=trigger_type_items)
    fob_type: EnumProperty(name="FOB Object Type", items=fob_type_items)
    visibox_type: EnumProperty(name="Visibox Type", items=visibox_type_items)

    object_id: IntProperty(
        name="ID",
        description="Track Zone or Visibox ID",
        default=-1
    )

    select_all_matches: BoolProperty(
        name="Select All Matches",
        description="Select all matching objects instead of just one",
        default=False
    )

    def _update_subtype_items(self, context):
        pass  # UI updates are handled in draw

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "category")

        if self.category == 'TRIGGER':
            layout.prop(self, "trigger_type")
        elif self.category == 'FOB':
            layout.prop(self, "fob_type")
        elif self.category == 'VISIBOX':
            layout.prop(self, "visibox_type")

        if self.category in {'VISIBOX', 'TRACK_ZONE'}:
            layout.prop(self, "object_id")

        layout.prop(self, "select_all_matches")

    def execute(self, context):
        found_any = False
        bpy.ops.object.select_all(action='DESELECT')

        for obj in context.scene.objects:
            if self.category == 'TRIGGER' and obj.get("is_trigger"):
                if int(obj.get("trigger_type_enum", -1)) != int(self.trigger_type):
                    continue
                self.select_object(obj, context)
                found_any = True
                if not self.select_all_matches:
                    break

            elif self.category == 'FOB' and obj.get("is_fob_object"):
                if int(obj.get("fob_type", -1)) != int(self.fob_type):
                    continue
                self.select_object(obj, context)
                found_any = True
                if not self.select_all_matches:
                    break

            elif self.category == 'TRACK_ZONE' and obj.get("is_track_zone"):
                if self.object_id != -1 and int(obj.get("track_zone_id", -1)) != self.object_id:
                    continue
                self.select_object(obj, context)
                found_any = True
                if not self.select_all_matches:
                    break

            elif self.category == 'VISIBOX' and obj.get("is_visibox"):
                if obj.get("visibox_type") != self.visibox_type:
                    continue
                if self.object_id != -1 and int(obj.get("visibox_id", -1)) != self.object_id:
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

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
    
"""
MATERIALS & TEXTURES ---------------------------------------------------------
"""


def prune_unused_material_slots(obj, keep_names=None):
    """Remove unreferenced material slots, optionally preserving named entries.

    Args:
        obj (bpy.types.Object): Mesh object to prune.
        keep_names (set[str] | None): Materials that must not be removed even if
            unreferenced.
    """

    if obj.type != 'MESH':
        return

    keep_names = keep_names or set()
    mesh = obj.data

    # Determine which indices are referenced by polygons
    referenced = {poly.material_index for poly in mesh.polygons}

    # Remove from the end so indices remain valid while popping
    for idx in range(len(mesh.materials) - 1, -1, -1):
        mat = mesh.materials[idx]
        if idx not in referenced and (not mat or mat.name not in keep_names):
            mesh.materials.pop(index=idx)


class MaterialAssignmentHelper:
    car_parts_prefixes = ["body", "wheel", "axle", "spring", "pin", "spinner"]

    def _is_car_part(self, obj):
        return getattr(obj, "is_car_part", False) or any(
            prefix in obj.name.lower() for prefix in self.car_parts_prefixes
        )

    # -------------------------------------------------------------------------
    # High-level loop
    # -------------------------------------------------------------------------

    def assign_materials_to_all(self, mesh_objects, existing_textures, material_choice):
        print(f"[INFO] Assigning materials to {len(mesh_objects)} mesh objects (fast mode)")
        for obj in mesh_objects:
            try:
                if obj.type != 'MESH':
                    continue

                print(f"[DEBUG] Processing: {obj.name}")
                self.update_material_assignment(obj, existing_textures, material_choice)
                prune_unused_material_slots(obj)
                print(f"[DEBUG] Done: {obj.name}")

            except Exception as e:
                print(f"[ERROR] Exception while processing {obj.name}: {e}")

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
        return clean_model_base_name(obj.name)

    def get_current_base_name(self, obj):
        if obj.get("is_instance") and "fin_texture_base" in obj:
            print(f"[DEBUG] Using fin_texture_base: {obj['fin_texture_base']} for {obj.name}")
            return obj["fin_texture_base"]

        # Car parts should always derive their base from the selected car texture
        # instead of the object name (body, wheel, etc.).
        if self._is_car_part(obj):
            scene = bpy.context.scene
            car_tex = get_scene_value(scene, "selected_car_texture", "car.bmp")
            return clean_model_base_name(car_tex)

        model_name = clean_model_base_name(obj.name)
        print(f"[DEBUG] checking model_name={model_name}, obj['is_model']={obj.get('is_model', False)}")

        if obj.get("is_model", False):
            scene = bpy.context.scene
            for i in range(MAX_MODEL_SLOTS):
                slot_name = get_scene_value(scene, f"m_model_name_{i}", "")
                tex_mode = get_scene_value(scene, f"m_texture_mode_{i}", "")
                tex_path = get_scene_value(scene, f"m_texture_path_{i}", "")
                print(f"[DEBUG] Slot {i}: m_model_name = '{slot_name}', mode = '{tex_mode}', path = '{tex_path}'")

                if clean_model_base_name(slot_name) == model_name:
                    if tex_mode == "LEVEL_TEXTURES":
                        return os.path.basename(tex_path.rstrip("/\\")).lower()
                    elif tex_mode == "TEXTURE_NAME":
                        return os.path.splitext(os.path.basename(tex_path))[0].lower()
                    else:
                        return model_name

        return self.get_base_name_for_layers(obj)

    # -------------------------------------------------------------------------
    # TEX+VC material creation (your working version)
    # -------------------------------------------------------------------------

    def assign_tex_vc_materials(self, obj, existing_textures=None):
        """
        Auto-assign blended materials combining texture and vertex colour per face.

        Behaviour:
        - First assigns UV texture materials (so every face has a proper texture mat).
        - Then creates per-texture blended materials named "<base>_TexVC".
        - Each "<base>_TexVC" material:
            * Base = texture colour (fallback = Col if no texture).
            * Overlay = vertex color "Col" in OVERLAY mode.
            * Fac driven by vertex color "Alpha" brightness (0..1) mapped to:
                  brightness = 0.0 (black Alpha) → Fac = 0.02  (≈2 % VC overlay)
                  brightness = 1.0 (white Alpha) → Fac = 1.0   (100 % VC overlay)
            * BSDF Alpha is fixed to 1.0 (no actual transparency in viewport).
        """

        import bmesh

        print(f"[FAST] assign_tex_vc_materials: {obj.name}")

        # 0) First make sure regular texture materials exist & are assigned
        try:
            if existing_textures is not None:
                self.assign_uv_textures(obj, existing_textures)
            else:
                self.assign_uv_textures(obj)
        except Exception as e:
            print(f"[ERROR] assign_tex_vc_materials: UV assignment failed for {obj.name}: {e}")
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
            if not orig_mat:
                continue

            # If the face already uses a TexVC material, keep it as-is so we
            # don't end up nesting names like "*_TexVC_TexVC" on repeated runs.
            if self._is_tex_vc_mat(orig_mat):
                continue

            # Base name from the texture material
            base_name = orig_mat.name
            if base_name.lower().endswith('.bmp'):
                base_name = base_name[:-4]
            if base_name.endswith('_Col'):
                # COL-only assignment leaves faces on *_Col; strip that suffix
                # so TexVC is generated from the texture base again.
                base_name = base_name[:-4]
            if not base_name:
                base_name = self.get_current_base_name(obj)
            new_name = f"{base_name}_TexVC"

            new_mat = blended_cache.get(new_name)
            if not new_mat:
                # Reuse or create the material datablock
                new_mat = bpy.data.materials.get(new_name)
                if not new_mat:
                    new_mat = bpy.data.materials.new(name=new_name)

                new_mat.use_nodes = True
                nodes = new_mat.node_tree.nodes
                links = new_mat.node_tree.links

                # Clear any old node setup so we know exactly what we have
                for node in list(nodes):
                    nodes.remove(node)

                # Opaque in viewport – Alpha does NOT control transparency here
                if hasattr(new_mat, "blend_method"):
                    new_mat.blend_method = 'OPAQUE'
                if hasattr(new_mat, "shadow_method"):
                    new_mat.shadow_method = 'OPAQUE'

                # ------------------------------------------------------------------
                # 1) Texture node (re-using image from original texture material)
                # ------------------------------------------------------------------
                tex_node = nodes.new('ShaderNodeTexImage')
                has_texture = False
                tex_node.image = None

                if getattr(orig_mat, 'use_nodes', False):
                    for node in orig_mat.node_tree.nodes:
                        if node.type == 'TEX_IMAGE' and getattr(node, 'image', None):
                            tex_node.image = node.image
                            has_texture = True
                            break

                # ------------------------------------------------------------------
                # 2) Vertex Color: Col & Alpha
                # ------------------------------------------------------------------
                col_attr = nodes.new('ShaderNodeAttribute')
                col_attr.attribute_name = 'Col'

                alpha_attr = nodes.new('ShaderNodeAttribute')
                alpha_attr.attribute_name = 'Alpha'

                # Alpha RGB → brightness 0..1 (black = 0, white = 1)
                rgb2bw = nodes.new('ShaderNodeRGBToBW')
                links.new(alpha_attr.outputs['Color'], rgb2bw.inputs['Color'])

                # ------------------------------------------------------------------
                # 3) Fac for OVERLAY: Fac = 0.5 * brightness + 0.5
                #   brightness = 0 → Fac = 0.50  (≈50 % VC, 50 % texture)
                #   brightness = 1 → Fac = 1.00  (≈100 % VC, 0 % texture)
                mul = nodes.new('ShaderNodeMath')
                mul.operation = 'MULTIPLY'
                mul.inputs[1].default_value = 0.5
                links.new(rgb2bw.outputs['Val'], mul.inputs[0])

                add = nodes.new('ShaderNodeMath')
                add.operation = 'ADD'
                add.inputs[1].default_value = 0.5
                links.new(mul.outputs['Value'], add.inputs[0])

                # ------------------------------------------------------------------
                # 4) Mix texture + vertex color using OVERLAY
                # ------------------------------------------------------------------
                mix = nodes.new('ShaderNodeMixRGB')
                mix.blend_type = 'OVERLAY'
                mix.inputs['Fac'].default_value = 1.0  # overridden by add output
                links.new(add.outputs['Value'], mix.inputs['Fac'])

                if has_texture:
                    # base = texture
                    links.new(tex_node.outputs['Color'], mix.inputs[1])
                else:
                    # fallback when no texture: base = vertex color
                    links.new(col_attr.outputs['Color'], mix.inputs[1])

                # overlay = Col
                links.new(col_attr.outputs['Color'], mix.inputs[2])

                # ------------------------------------------------------------------
                # 5) BSDF & Output – Alpha fixed to 1.0 (no transparency here)
                # ------------------------------------------------------------------
                bsdf = nodes.new('ShaderNodeBsdfPrincipled')
                output = nodes.new('ShaderNodeOutputMaterial')

                # Color from overlay mix
                links.new(mix.outputs['Color'], bsdf.inputs['Base Color'])

                # Keep material fully opaque in viewport
                bsdf.inputs['Alpha'].default_value = 1.0

                links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

                # Cache for this run
                blended_cache[new_name] = new_mat

            # Ensure TexVC material is in the mesh's material slots
            if new_mat.name not in mesh.materials:
                mesh.materials.append(new_mat)

            # Assign the TexVC material slot to this face
            face.material_index = mesh.materials.find(new_mat.name)

        bm.to_mesh(mesh)
        bm.free()
        mesh.update()

        # Make one of the TexVC materials the active material
        for blended in blended_cache.values():
            if blended.name in mesh.materials:
                idx = mesh.materials.find(blended.name)
                if idx >= 0:
                    obj.active_material_index = idx
                    break

    # -------------------------------------------------------------------------
    # TexVC helpers / cleanup
    # -------------------------------------------------------------------------

    def _is_tex_vc_mat(self, mat):
        return bool(mat and isinstance(mat.name, str) and mat.name.endswith("_TexVC"))

    def _remove_unreferenced_tex_vc_slots(self, obj):
        mesh = obj.data
        import bmesh
        bm = bmesh.new()
        bm.from_mesh(mesh)
        referenced = set(f.material_index for f in bm.faces)
        bm.free()
        # Remove *_TexVC slots that aren't referenced (back-to-front so indices stay valid)
        for idx in range(len(mesh.materials) - 1, -1, -1):
            mat = mesh.materials[idx]
            if idx not in referenced and self._is_tex_vc_mat(mat):
                mesh.materials.pop(index=idx)

    def _set_active_texture_material(self, obj):
        """Pick a sane pure-texture active material (not *_TexVC, not *_Col, etc.)."""
        mesh = obj.data
        # 1) Prefer the material used by the first polygon (if any), if it's not TexVC
        if len(mesh.polygons) > 0:
            idx = mesh.polygons[0].material_index
            if 0 <= idx < len(mesh.materials) and not self._is_tex_vc_mat(mesh.materials[idx]):
                obj.active_material_index = idx
                return
        # 2) Else pick the first non-TexVC slot that looks like a texture (endswith .bmp or has a TEX_IMAGE node)
        for i, m in enumerate(mesh.materials):
            if not m or self._is_tex_vc_mat(m):
                continue
            if m.name.lower().endswith(".bmp"):
                obj.active_material_index = i
                return
            if getattr(m, "use_nodes", False):
                if any(n.type == 'TEX_IMAGE' for n in m.node_tree.nodes):
                    obj.active_material_index = i
                    return
        # 3) Fallback: first non-TexVC material
        for i, m in enumerate(mesh.materials):
            if not self._is_tex_vc_mat(m):
                obj.active_material_index = i
                return

    def _find_level_texture_material(self, base_name, tex_num):
        """
        Resolve a level texture material for a given texture page.

        Supports BOTH:
        - classic letter suffixes:  tracka.bmp, trackb.bmp, ...
        - numeric variants:         track0.bmp, track1.bmp, 0.bmp, 1.bmp, ...

        Returns a bpy.types.Material or None.
        """
        mat = None

        # 1) Existing behaviour: letter suffix via int_to_texture()
        try:
            letter_name = int_to_texture(tex_num, name=base_name)
        except Exception:
            letter_name = None

        if letter_name:
            mat = self.find_material_loose(letter_name)
            if mat:
                return mat

        # 2) Numeric fallbacks
        num = str(tex_num)
        candidates = []

        if base_name:
            # track1 / track1.bmp
            candidates.extend([
                f"{base_name}{num}",
                f"{base_name}{num}.bmp",
            ])

        # bare 1 / 1.bmp
        candidates.extend([
            num,
            f"{num}.bmp",
        ])

        for cand in candidates:
            mat = self.find_material_loose(cand)
            if mat:
                return mat

        return None

    def _reassign_faces_off_tex_vc(self, obj):
        """Force any *_TexVC faces to the correct texture-only material by texnum."""
        import bmesh
        mesh = obj.data

        # When running from assign_materials_to_all() we're in Edit mode.
        # Using bmesh.to_mesh() on an edit-mode mesh raises a ValueError, so
        # work with the live edit BMesh in that case and use
        # bmesh.update_edit_mesh() to flush changes back to the mesh.
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
            return

        # Rebuild the same base-name + source_mode logic you already use
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
                    base_name = clean_model_base_name(obj.name)
            source_mode = "LEVEL_TEXTURES"
        if not matched and is_car_part:
            fallback_name = get_scene_value(scene, "selected_car_texture", "car.bmp")
            base_name = clean_model_base_name(fallback_name)
            source_mode = "TEXTURE_NAME"

        for face in bm.faces:
            # Only touch faces that currently use *_TexVC
            cur = mesh.materials[face.material_index] if 0 <= face.material_index < len(mesh.materials) else None
            if not self._is_tex_vc_mat(cur):
                continue

            tex_num = face[texnum_layer]
            mat = None

            if source_mode == "TEXTURE_NAME":
                mat = self.find_material_loose(f"{base_name}.bmp")
            elif source_mode == "LEVEL_TEXTURES" and tex_num >= 0:
                # NEW: support both letter and numeric schemes
                mat = self._find_level_texture_material(base_name, tex_num)
            else:
                continue

            if not mat:
                # If it doesn't exist yet, UV assignment (step 1) should have added it;
                # if not, skip defensively.
                continue
            if mat.name not in mesh.materials:
                mesh.materials.append(mat)

            face.material_index = mesh.materials.find(mat.name)

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

        # material_choice is now passed in from execute()
        material_suffix = material_map.get(material_choice, '_Col')

        print(f"[DEBUG] update_material_assignment() called for {obj.name}")
        print(f"[DEBUG] material_choice = {material_choice}, resolved suffix = {material_suffix}")
        print(f"[DEBUG] Current materials: {[m.name for m in obj.data.materials]}")

        if material_choice == 'UV_TEX':
            print(f"[DEBUG] → Assigning UV textures for {obj.name}")
            self.assign_uv_textures(obj, existing_textures)
            self._reassign_faces_off_tex_vc(obj)
            self._remove_unreferenced_tex_vc_slots(obj)
            self._set_active_texture_material(obj)
            obj.data.update()
            obj.update_tag(refresh={'DATA'})

        elif material_choice == 'TEX_VC':
            print(f"[DEBUG] → Assigning Tex+VC materials for {obj.name}")
            try:
                self.assign_tex_vc_materials(obj, existing_textures)
            except TypeError:
                self.assign_tex_vc_materials(obj)

        elif material_choice == 'RGB':
            print(f"[DEBUG] → Assigning RGB Model Color materials for {obj.name}")
            self.assign_rgb_modelcolor_materials(obj)

        elif material_choice == 'NCP':
            print(f"[DEBUG] → Assigning NCP materials for {obj.name}")
            self.assign_ncp_materials(obj)

        else:
            print(f"[DEBUG] → Assigning regular materials with suffix {material_suffix} for {obj.name}")
            self.assign_regular_materials(obj, material_suffix)

        print(f"[DEBUG] After assignment: {[m.name for m in obj.data.materials]}")
        print(f"[DEBUG] Active material index is {obj.active_material_index} "
              f"({obj.active_material.name if obj.active_material else 'None'})")

    # -------------------------------------------------------------------------
    # UV texture assignment (Texture Number layer)
    # -------------------------------------------------------------------------

    def assign_uv_textures(self, obj, existing_textures):
        print(f"[FAST] assign_uv_textures: {obj.name}")

        bm = bmesh.new()
        bm.from_mesh(obj.data)

        texnum_layer = bm.faces.layers.int.get("Texture Number")
        if not texnum_layer:
            # Create the layer so we can still assign a sensible default texture
            texnum_layer = bm.faces.layers.int.new("Texture Number")
            for face in bm.faces:
                face[texnum_layer] = 0
            print(f"[INFO] Created missing 'Texture Number' layer on {obj.name} with default 0")

        scene = bpy.context.scene
        base_name = ""
        source_mode = ""
        matched = False
        model_slot_index = -1

        if obj.get("is_model", False):
            for i in range(MAX_MODEL_SLOTS):
                slot_model_name = get_scene_value(scene, f"m_model_name_{i}", "")
                if not slot_model_name:
                    continue

                if clean_model_base_name(slot_model_name) in clean_model_base_name(obj.name):
                    source_mode = get_scene_value(scene, f"m_texture_mode_{i}", "VERTEX_COLOR")
                    texture_path = get_scene_value(scene, f"m_texture_path_{i}", "")
                    model_slot_index = i

                    if source_mode == "TEXTURE_NAME":
                        base_name = os.path.splitext(os.path.basename(texture_path))[0].lower()
                    elif source_mode == "LEVEL_TEXTURES":
                        base_name = os.path.basename(texture_path.rstrip("/\\")).lower()

                    matched = True
                    print(f"[DEBUG] Matched .m model slot {i} → name={slot_model_name}, base={base_name}")
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
                    base_name = clean_model_base_name(obj.name)
            source_mode = "LEVEL_TEXTURES"

        if not matched and is_car_part:
            fallback_name = get_scene_value(scene, "selected_car_texture", "car.bmp")
            base_name = clean_model_base_name(fallback_name)
            source_mode = "TEXTURE_NAME"

        for face in bm.faces:
            tex_num = face[texnum_layer]
            mat = None

            if source_mode == 'TEXTURE_NAME':
                # single texture, no tex_num variation
                mat = self.find_material_loose(f"{base_name}.bmp")
            elif source_mode == 'LEVEL_TEXTURES' and tex_num >= 0:
                # NEW: support both tracka / trackb *and* track0 / track1 / 0 / 1
                mat = self._find_level_texture_material(base_name, tex_num)
            else:
                continue

            if not mat:
                continue

            if mat.name not in obj.data.materials:
                obj.data.materials.append(mat)

            face.material_index = obj.data.materials.find(mat.name)

        bm.to_mesh(obj.data)
        bm.free()
        obj.data.update()

    # -------------------------------------------------------------------------
    # NCP material assignment
    # -------------------------------------------------------------------------

    def assign_ncp_materials(self, obj):
        """Assign NCP preview materials based on the face 'Material' layer."""
        print(f"[FAST] assign_ncp_materials: {obj.name}")

        import bmesh

        mesh = obj.data
        bm = bmesh.new()
        bm.from_mesh(mesh)

        material_layer = bm.faces.layers.int.get("Material")
        if not material_layer:
            print(f"[SKIP] No 'Material' layer on {obj.name}")
            bm.free()
            return

        # Build a mapping: NCP material ID (int) -> MATERIALS entry
        id_to_name = {}
        for entry in MATERIALS:
            try:
                code = int(entry[0])  # "-1", "0", "1", ...
            except Exception:
                try:
                    code = int(entry[-1])  # last field is also numeric ID
                except Exception:
                    continue
            id_to_name[code] = entry[1]  # human-readable name, e.g. "GRASS"

        used_mat_names = set()

        for face in bm.faces:
            mat_id = face[material_layer]  # NCP material ID from the face
            mat_name = id_to_name.get(mat_id)
            if not mat_name:
                continue

            # Reuse the material if it already exists (e.g. from import),
            # otherwise create a simple new one.
            mat = self.find_material_loose(mat_name)
            if not mat:
                mat = bpy.data.materials.new(name=mat_name)
                mat.use_nodes = True  # keep it node-based for consistency

            if mat.name not in mesh.materials:
                mesh.materials.append(mat)

            slot_index = mesh.materials.find(mat.name)
            if slot_index >= 0:
                face.material_index = slot_index
                used_mat_names.add(mat.name)

        bm.to_mesh(mesh)
        bm.free()
        mesh.update()

        # Pick one of the NCP materials as the active material
        for i, m in enumerate(mesh.materials):
            if m and m.name in used_mat_names:
                obj.active_material_index = i
                break

        print(f"[DEBUG] NCP preview assigned materials {sorted(used_mat_names)} to {obj.name}")

    # -------------------------------------------------------------------------
    # RGB Model Color material assignment
    # -------------------------------------------------------------------------

    def assign_rgb_modelcolor_materials(self, obj):
        """
        Assign a material that previews the baked RGBModelColor vertex colors.

        Behaviour (similar idea to COL):
        - First, prefer any existing material *already on the object* whose name
          ends with _RGBModelColor / _RGBModelColour.
        - Then, try to find a matching datablock in bpy.data.materials using both:
            * the full object name (tins_g_row)
            * the cleaned RV base name (tins_g_r, from clean_model_base_name)
          with patterns like:
            <root>_RGBModelColor
            <root>.prm_RGBModelColor
            <root>.w_RGBModelColor
            <root>.m_RGBModelColor
        - If nothing exists, create a new <root>.prm_RGBModelColor material
          wired to the 'RGBModelColor' attribute.
        """

        import bmesh
        import bpy

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
    # Regular suffix-based material assignment
    # -------------------------------------------------------------------------

    def assign_regular_materials(self, obj, material_suffix):
        print(f"[FAST] assign_regular_materials: {obj.name}")

        base_name = clean_model_base_name(obj.name, truncate=False)
        potential_names = [
            f"{base_name}{material_suffix}",
            f"{base_name}.prm{material_suffix}",
            f"{base_name}.w{material_suffix}",
            f"{base_name}.m{material_suffix}"
        ]

        material = next((bpy.data.materials.get(n) for n in potential_names if bpy.data.materials.get(n)), None)
        if not material:
            material = bpy.data.materials.get(material_suffix)

        if not material:
            print(f"[WARN] Material not found for {obj.name} with suffix {material_suffix}")
            return

        if material.name not in obj.data.materials:
            obj.data.materials.append(material)

        index = obj.data.materials.find(material.name)

        # 🔹 NEW: make this material the active one in the UI
        if index >= 0:
            obj.active_material_index = index

        import bmesh
        bm = bmesh.new()
        bm.from_mesh(obj.data)

        for face in bm.faces:
            face.material_index = index

        bm.to_mesh(obj.data)
        bm.free()
        obj.data.update()

    # -------------------------------------------------------------------------
    # Material lookup helper
    # -------------------------------------------------------------------------

    def find_material_loose(self, name):
        """Try to find a material with or without .bmp suffix."""
        if name in bpy.data.materials:
            return bpy.data.materials[name]
        elif name.endswith('.bmp') and name[:-4] in bpy.data.materials:
            return bpy.data.materials[name[:-4]]
        elif f"{name}.bmp" in bpy.data.materials:
            return bpy.data.materials[f"{name}.bmp"]
        return None


class MaterialAssignmentAuto(MaterialAssignmentHelper, bpy.types.Operator):
    """Assign Materials to All Meshes Automatically"""
    bl_idname = "object.assign_materials_auto"
    bl_label = "Assign Materials Automatically"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        print("[DEBUG] Starting MaterialAssignmentAuto")

        if bpy.context.mode != 'OBJECT':
            print("[DEBUG] Switching to OBJECT mode")
            bpy.ops.object.mode_set(mode='OBJECT')

        mesh_objects = [obj for obj in bpy.data.objects if obj.type == 'MESH']
        print(f"[DEBUG] Found {len(mesh_objects)} mesh objects")

        if not mesh_objects:
            self.report({'WARNING'}, "No mesh objects found in the scene.")
            return {'CANCELLED'}

        scene = context.scene
        original_active_object = context.view_layer.objects.active

        # --- NEW: drive choice from scene, not from mesh ---
        material_choice = getattr(scene, "material_choice", None)
        if not material_choice:
            material_choice = 'UV_TEX'
        print(f"[DEBUG] Global / scene material choice: {material_choice}")

        # Texture-based modes still need a level texture base
        if material_choice in {"UV_TEX", "TEX_VC", "ENV", "ALPHA"}:
            if not get_scene_value(scene, "level_texture_base", "").strip():
                print("[ERROR] level_texture_base not set")
                bpy.ops.scene.prompt_texture_base('INVOKE_DEFAULT')
                return {'CANCELLED'}

        existing_textures = self.get_existing_textures()
        print(f"[DEBUG] Found {len(existing_textures)} existing textures")

        # Optional: if meshes *do* have a material_choice, keep them in sync
        for obj in mesh_objects:
            if hasattr(obj.data, "material_choice"):
                obj.data.material_choice = material_choice

        # --- pass material_choice further down ---
        self.assign_materials_to_all(mesh_objects, existing_textures, material_choice)

        print("[DEBUG] Material assignment done, restoring selection")
        bpy.ops.object.select_all(action='DESELECT')
        for obj in mesh_objects:
            obj.select_set(True)

        if original_active_object and original_active_object.name in bpy.data.objects:
            context.view_layer.objects.active = original_active_object

        print("[DEBUG] MaterialAssignmentAuto finished successfully")
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
            car_tex = get_scene_value(scene, "selected_car_texture", "car.bmp")
            return clean_model_base_name(car_tex)

        model_name = clean_model_base_name(obj.name)

        if obj.get("is_model", False):
            scene = bpy.context.scene
            for i in range(MAX_MODEL_SLOTS):
                slot_name = get_scene_value(scene, f"m_model_name_{i}", "")
                tex_mode = get_scene_value(scene, f"m_texture_mode_{i}", "")
                tex_path = get_scene_value(scene, f"m_texture_path_{i}", "")

                if clean_model_base_name(slot_name) == model_name:
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

        print(f"[DEBUG] update_material_assignment() called for {obj.name}")
        print(f"[DEBUG] material_choice = {material_choice}, resolved suffix = {material_suffix}")
        print(f"[DEBUG] Current materials: {[m.name for m in obj.data.materials]}")

        if material_choice == 'UV_TEX':
            print(f"[DEBUG] → Assigning UV textures for {obj.name}")
            self.assign_uv_textures(obj, existing_textures)

        # Block TEX+VC for this operator (Selected)
        elif material_choice == 'TEX_VC':   # ← was active_material_choice
            self.report({'INFO'}, "TEX+VC can only be assigned via Set to All.")
            return {'CANCELLED'}

        elif material_choice == 'NCP':
            print(f"[DEBUG] → Assigning NCP materials for {obj.name}")
            self.assign_ncp_materials(obj)

        else:
            print(f"[DEBUG] → Assigning regular materials with suffix {material_suffix} for {obj.name}")
            self.assign_regular_materials(obj, material_suffix)

        # ---- DEBUG AFTER ASSIGNMENT ----
        print(f"[DEBUG] After assignment: {[m.name for m in obj.data.materials]}")
        print(f"[DEBUG] Active material index is {obj.active_material_index} ({obj.active_material.name if obj.active_material else 'None'})")

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

            if not mat and is_car_part:
                fallback_name = get_scene_value(scene, "selected_car_texture", "car.bmp")
                mat = bpy.data.materials.get(fallback_name)

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
        base_name = clean_model_base_name(obj.name, truncate=False)

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
        if not material:
            return

        if material.name not in obj.data.materials:
            obj.data.materials.append(material)

        # IMPORTANT: multi-object edit mode => check mesh.is_editmode
        if obj.data.is_editmode:
            bm = bmesh.from_edit_mesh(obj.data)  # valid for any mesh currently in edit mode
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
        return None

class MaterialAssignmentImportExport(bpy.types.Operator):
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

        model_name = clean_model_base_name(obj.name)
        print(f"[DEBUG] checking model_name={model_name}, obj['is_model']={obj.get('is_model', False)}")

        if obj.get("is_model", False):
            scene = bpy.context.scene
            for i in range(MAX_MODEL_SLOTS):
                slot_name = get_scene_value(scene, f"m_model_name_{i}", "")
                tex_mode = get_scene_value(scene, f"m_texture_mode_{i}", "")
                tex_path = get_scene_value(scene, f"m_texture_path_{i}", "")
                print(f"[DEBUG] Slot {i}: m_model_name = '{slot_name}', mode = '{tex_mode}', path = '{tex_path}'")

                if clean_model_base_name(slot_name) == model_name:
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

        # If the mesh is currently in edit mode, use the existing edit BMesh to
        # avoid calling to_mesh() on an edit-mode mesh (which triggers a
        # ValueError). Otherwise, create a fresh BMesh from the object data.
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
                    print(f"[DEBUG] Matched .m model slot {i} → name={slot_model_name}, base={base_name_for_texture}")
                    break

        is_car_part = self._is_car_part(obj)
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
            tex_num = face[texnum_layer]
            mat = None

            if source_mode == 'TEXTURE_NAME':
                mat = self.find_material_loose(f"{base_name_for_texture}.bmp")
            elif source_mode == 'LEVEL_TEXTURES':
                if tex_num == -1:
                    continue
                # NEW: support numeric as well as letter suffixes
                mat = self._find_level_texture_material(base_name_for_texture, tex_num)
            else:
                continue

            if not mat:
                # Existing “infer from slot” fallback
                slot_index = face.material_index
                if slot_index < len(mesh.materials):
                    candidate = mesh.materials[slot_index].name
                    mat = bpy.data.materials.get(candidate)
                    if not mat and not candidate.endswith('.bmp'):
                        mat = bpy.data.materials.get(f"{candidate}.bmp")
                    elif not mat and candidate.endswith('.bmp'):
                        mat = bpy.data.materials.get(candidate[:-4])

            if not mat and is_car_part:
                fallback_name = get_scene_value(scene, "selected_car_texture", "car.bmp")
                mat = bpy.data.materials.get(fallback_name)
                if mat:
                    print(f"[INFO] Fallback texture '{fallback_name}' used for {obj.name}")

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
        base_name = clean_model_base_name(obj.name, truncate=False)

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

        if not material:
            return

        if material.name not in obj.data.materials:
            obj.data.materials.append(material)

        # Only call bmesh if object is active and in Edit Mode
        if bpy.context.view_layer.objects.active == obj and obj.mode == 'EDIT':
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
    bl_label = "Fix Texture Numbers and Materials"
    bl_description = (
        "Sets the texture number based on image suffix (letters or numbers), "
        "creates missing materials and assigns them per-face"
    )

    texture_base: bpy.props.StringProperty(
        name="Texture Base",
        description="Prefix for textures (e.g. 'box', 'kit_hexcity'). "
                    "Leave empty if textures are just 'a.bmp', '0.bmp', etc.",
        default=""
    )

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        import bmesh
        import bpy
        from .common import TEX_PAGES_MAX  # make sure this exists in common.py

        base = self.texture_base.lower().strip()
        renamed = 0

        # ------------------------------------------------------------------
        # Helper: map image name -> tex_num (supports letters AND numbers)
        # ------------------------------------------------------------------
        def suffix_to_texnum(image_name: str) -> int:
            """
            Extract tex_num from name.

            Handles:
              base + 'a'...'z', 'aa'...'lb' (0..63)
              base + '0'...'63' (0..63)

            If base is empty, the whole name is treated as the suffix.
            """
            name = image_name.lower().removesuffix(".bmp")

            # Split base + suffix
            if base:
                if not name.startswith(base):
                    return -1
                suffix = name[len(base):]
            else:
                suffix = name

            suffix = suffix.strip()
            if not suffix:
                return -1

            # Numeric suffix: base0, base1, ... or just "0", "1", ...
            if suffix.isdigit():
                try:
                    num = int(suffix)
                except ValueError:
                    return -1
                return num if 0 <= num < TEX_PAGES_MAX else -1

            # Alphabetic suffix: a..z, aa..??
            if not suffix.isalpha() or len(suffix) > 2:
                return -1

            if len(suffix) == 1:
                index = ord(suffix) - ord('a')
            else:
                major = ord(suffix[0]) - ord('a') + 1
                minor = ord(suffix[1]) - ord('a')
                index = major * 26 + minor

            return index if 0 <= index < TEX_PAGES_MAX else -1

        # ------------------------------------------------------------------
        # 1) Build tex_num → image mapping once (global)
        # ------------------------------------------------------------------
        texnum_to_image = {}
        for img in bpy.data.images:
            if img.name in {"Render Result", "Viewer Node"}:
                continue

            tex_num = suffix_to_texnum(img.name)
            if tex_num < 0:
                continue

            # Keep the first image we find for a given tex_num
            if tex_num not in texnum_to_image:
                texnum_to_image[tex_num] = img

        # ------------------------------------------------------------------
        # 2) For each mapped image, ensure there is a material using it
        #    Build tex_num → material map only once
        # ------------------------------------------------------------------
        texnum_to_material = {}
        existing_mats = {m.name: m for m in bpy.data.materials}

        for tex_num, image in texnum_to_image.items():
            image_name_norm = image.name.lower().removesuffix(".bmp")
            mat_name = f"{image_name_norm}.bmp" if image_name_norm else image.name

            mat = existing_mats.get(mat_name)
            if not mat:
                mat = bpy.data.materials.new(name=mat_name)
                existing_mats[mat_name] = mat
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

            texnum_to_material[tex_num] = mat

        # ------------------------------------------------------------------
        # 3) Per-object pass: per-face texture number + per-face material
        # ------------------------------------------------------------------
        for obj in context.scene.objects:
            if obj.type != 'MESH':
                continue

            if obj.mode == 'EDIT':
                bm = bmesh.from_edit_mesh(obj.data)
                is_edit = True
            else:
                bm = bmesh.new()
                bm.from_mesh(obj.data)
                is_edit = False

            texnum_layer = bm.faces.layers.int.get("Texture Number")
            had_texnum_layer = texnum_layer is not None
            if not texnum_layer:
                texnum_layer = bm.faces.layers.int.new("Texture Number")

            # Cache: for this object, which material slot index is used for each tex_num
            obj_texnum_to_slot = {}

            # Speed: local view of material slots
            obj_mats = list(obj.material_slots)

            for face in bm.faces:
                # 1) Start with existing tex_num if layer existed
                tex_num = face[texnum_layer] if had_texnum_layer else -1

                # 2) Try to derive from current face material if tex_num invalid
                if tex_num < 0:
                    mat_index = face.material_index
                    if 0 <= mat_index < len(obj_mats):
                        mat = obj_mats[mat_index].material
                        if mat and mat.use_nodes and mat.node_tree:
                            image = None
                            for node in mat.node_tree.nodes:
                                if node.type == 'TEX_IMAGE' and node.image:
                                    image = node.image
                                    break

                            if image:
                                tex_num = suffix_to_texnum(image.name)

                                # Optional: rename material based on base + suffix
                                image_name_norm = image.name.lower().removesuffix(".bmp")
                                if base:
                                    if image_name_norm.startswith(base):
                                        suffix = image_name_norm[len(base):]
                                    else:
                                        suffix = ""
                                    mat_base = base
                                else:
                                    suffix = image_name_norm
                                    mat_base = ""

                                if mat_base or suffix:
                                    correct_name = f"{(mat_base + suffix) if mat_base else image_name_norm}.bmp"
                                    if mat.name != correct_name:
                                        mat.name = correct_name
                                        renamed += 1

                # 3) Write Texture Number (even if -1)
                face[texnum_layer] = tex_num if tex_num is not None else -1

                # 4) Assign material based on texture number (per-face)
                if tex_num is not None and tex_num >= 0 and tex_num in texnum_to_material:
                    target_mat = texnum_to_material[tex_num]

                    # Quick lookup: have we already bound this tex_num to a slot in this object?
                    if tex_num in obj_texnum_to_slot:
                        target_index = obj_texnum_to_slot[tex_num]
                    else:
                        # Try to find existing slot with this material
                        target_index = None
                        for idx, slot in enumerate(obj.material_slots):
                            if slot.material == target_mat:
                                target_index = idx
                                break

                        # If not found, append a new slot
                        if target_index is None:
                            obj.data.materials.append(target_mat)
                            target_index = len(obj.data.materials) - 1

                        obj_texnum_to_slot[tex_num] = target_index

                    # This is the crucial *per-face* assignment:
                    face.material_index = target_index

            # Write back BMesh
            if is_edit:
                bmesh.update_edit_mesh(obj.data)
            else:
                bm.to_mesh(obj.data)
                bm.free()

        self.report(
            {'INFO'},
            f"Renamed {renamed} materials, updated Texture Numbers "
            f"and assigned per-face materials from texture numbers."
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
        base_name = clean_model_base_name(self.model_name.strip().lower())

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
    
"""
SHADOW -----------------------------------------------------------------------
"""

class BakeShadow(bpy.types.Operator):
    bl_idname = "lighttools.bake_shadow"
    bl_label = "Bake Shadow"
    bl_description = "Creates a shadow plane beneath the selected object"

    def check_for_selected(self, context):
        """Checks if exactly one object is selected and it is the car's body. If not, prompts the user."""
        selected_objects = context.selected_objects
    
        # Check if no objects are selected
        if not selected_objects:
            msg_box("Select Car first", "INFO")
            return False  # Indicates that the operation should be canceled

        # Check if multiple objects are selected
        if len(selected_objects) > 1:
            msg_box("Select Car's body only", "INFO")
            return False  # Indicates that the operation should be canceled
        return True  # Indicates that there are selected objects and the operation can continue

    def create_unique_material(self, base_name="ShadowMaterial"):
        material_name = base_name
        index = 1
        while material_name in bpy.data.materials:
            material_name = f"{base_name}.{index:03d}"
            index += 1
        new_material = bpy.data.materials.new(name=material_name)
        new_material.use_nodes = True
        return new_material, material_name

    def assign_texture_to_material(self, mat, image):
        """Assigns a texture image to the material for baking."""
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links

        # Add image texture node
        tex_image_node = nodes.new('ShaderNodeTexImage')
        tex_image_node.image = image
        links.clear()  # Clear existing links to avoid any issues

        # Set the image node as active for baking
        mat.node_tree.nodes.active = tex_image_node

    def get_brightness_factor(self):
        return 1.6  # Fixed value — no scene property needed

    def blur_texture_edges(self, material, image):
        """Applies a blur on the shadow edges using a gradient texture with a fixed blur scale."""
        nodes = material.node_tree.nodes
        links = material.node_tree.links

        # Clear existing nodes
        nodes.clear()

        # Add the image texture node (this is the texture being blurred)
        tex_image_node = nodes.new('ShaderNodeTexImage')
        tex_image_node.image = image

        # Add a gradient texture for edge softening
        gradient_node = nodes.new('ShaderNodeTexGradient')
        gradient_node.gradient_type = 'RADIAL'

        # Add a mapping node to control the gradient scale (fixed blur strength)
        mapping_node = nodes.new('ShaderNodeMapping')
        mapping_node.inputs['Scale'].default_value = (1.5, 1.5, 1.5)  # Fixed blur scale, adjust if necessary

        # Add the color ramp to control the blending of black and white
        color_ramp_node = nodes.new('ShaderNodeValToRGB')
        color_ramp_node.color_ramp.interpolation = 'LINEAR'

        # Set the black (background) value
        color_ramp_node.color_ramp.elements[0].position = 0.5  # Adjust as needed
        color_ramp_node.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)  # Black

        # Set the white (shadow) value
        color_ramp_node.color_ramp.elements[1].position = 0.99  # Keep the shadow white
        color_ramp_node.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1.0)  # White

        # Add a mix node to blend the shadow and the gradient for softening edges
        mix_node = nodes.new('ShaderNodeMixRGB')
        mix_node.blend_type = 'MIX'
        mix_node.inputs['Fac'].default_value = 1.0  # Full opacity

        # Connect the gradient to the mix shader
        links.new(mapping_node.outputs['Vector'], gradient_node.inputs['Vector'])
        links.new(gradient_node.outputs['Color'], color_ramp_node.inputs['Fac'])  # Mask for edges

        # Connect the shadow texture to the mix shader
        links.new(tex_image_node.outputs['Color'], mix_node.inputs[2])

        # Connect the color ramp to the mix node to ensure the shadow stays white
        links.new(color_ramp_node.outputs['Color'], mix_node.inputs[1])

        # Connect the final mix to the material output
        output_node = nodes.new('ShaderNodeOutputMaterial')
        links.new(mix_node.outputs['Color'], output_node.inputs['Surface'])

    def bake_and_process(self, context, margin, texture_name_suffix, material, threshold):
        shadow_resolution = int(context.scene.shadow_resolution)
        shadow_tex = bpy.data.images.new(f"Shadow_{texture_name_suffix}", width=shadow_resolution, height=shadow_resolution, alpha=True)

        # Assign bake texture and get node
        tex_image_node = material.node_tree.nodes.new('ShaderNodeTexImage')
        tex_image_node.image = shadow_tex
        tex_image_node.name = "AO_BakeTarget"
        material.node_tree.nodes.active = tex_image_node

        # Ensure the active object is selected
        shadow_obj = context.active_object
        context.view_layer.objects.active = shadow_obj
        shadow_obj.select_set(True)

        # Ensure UV unwrap
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.unwrap(method='ANGLE_BASED', margin=margin)
        bpy.ops.object.mode_set(mode='OBJECT')

        print("[DEBUG] Baking AO...")
        bpy.ops.object.bake(type='AO')
        print("[DEBUG] AO bake done")

        self.fast_shadow_post_process(shadow_tex, threshold)

        return shadow_tex

    def fast_shadow_post_process(self, image, threshold):
        import numpy as np
        print(f"[DEBUG] Threshold used: {threshold}")

        pixels = np.array(image.pixels[:], dtype=np.float32).reshape((-1, 4))

        # 1. Invert AO: shadows become white
        pixels[:, :3] = 1.0 - pixels[:, :3]

        # 2. Thicken shadow via remap
        pixels[:, :3] = np.clip(pixels[:, :3] ** 0.25, 0.0, 1.0)

        # 3. Apply binary threshold — snap to pure black or white
        shadow_mask = pixels[:, :3] >= threshold
        pixels[:, :3] = np.where(shadow_mask, 1.0, 0.0)

        image.pixels[:] = pixels.flatten()
        image.update()
        print("[DEBUG] Shadow finalized (thresholded)")

    def bake_blurred_texture_to_image(self, context, shadow_plane, material):
        """Bakes the blurred shader output into a texture image."""
        shadow_resolution = int(context.scene.shadow_resolution)
        shadow_image = bpy.data.images.new(name="shadow", width=shadow_resolution, height=shadow_resolution, alpha=True)

        # Ensure UV map exists
        if not shadow_plane.data.uv_layers:
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.uv.unwrap(method='ANGLE_BASED', margin=0.001)
            bpy.ops.object.mode_set(mode='OBJECT')

        # Create and activate image node for bake target
        nodes = material.node_tree.nodes
        tex_image_node = nodes.get("Blurred_BakeTarget") or nodes.new('ShaderNodeTexImage')
        tex_image_node.name = "Blurred_BakeTarget"
        tex_image_node.image = shadow_image
        material.node_tree.nodes.active = tex_image_node

        # Set the shadow plane as active
        context.view_layer.objects.active = shadow_plane
        shadow_plane.select_set(True)

        # Bake shader result to texture
        bpy.ops.object.bake(type='COMBINED')

        # Pack image to avoid loss
        shadow_image.pack()

        # Assign final texture
        self.assign_final_texture(shadow_plane, shadow_image)

        return shadow_image

    def assign_final_texture(self, shadow_plane, shadow_tex):
        """Assigns the final baked shadow texture to the shadow plane."""
        mat = shadow_plane.active_material
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links

        # Reuse or create Image Texture node
        tex_image_node = nodes.get("FinalShadowTex") or nodes.new('ShaderNodeTexImage')
        tex_image_node.name = "FinalShadowTex"
        tex_image_node.image = shadow_tex

        # Reuse or find BSDF node
        bsdf_node = nodes.get("Principled BSDF")
        if not bsdf_node:
            for node in nodes:
                if node.type == 'BSDF_PRINCIPLED':
                    bsdf_node = node
                    break

        # Connect texture to Base Color
        if bsdf_node:
            links.new(tex_image_node.outputs['Color'], bsdf_node.inputs['Base Color'])

        mat.use_nodes = True

    def bake_shadow(self, context):
        from .tools import map_strength_to_threshold
        
        original_active = context.view_layer.objects.active
        scene = context.scene
        original_engine = scene.render.engine

        print("[DEBUG] Starting BakeShadow operator")
        
        # Check for selected objects
        if not self.check_for_selected(context):
            return {'CANCELLED'}

        # Use shadow quality from scene
        print("[DEBUG] Setting Cycles render settings")
        scene.render.engine = 'CYCLES'
        scene.cycles.samples = int(scene.shadow_quality)
        scene.cycles.max_bounces = 1
        scene.cycles.diffuse_bounces = 0
        scene.cycles.glossy_bounces = 0
        scene.cycles.transmission_bounces = 0
        scene.cycles.transparent_max_bounces = 0
        scene.cycles.volume_bounces = 0

        # Proceed with baking if objects are selected
        shade_obj = context.selected_objects[0]

        # Setup light
        lamp_data_pos = bpy.data.lights.new(name="ShadePositive", type="AREA")
        lamp_data_pos.energy = 1000.0
        lamp_data_pos.size = 2.0
        lamp_positive = bpy.data.objects.new(name="ShadePositive", object_data=lamp_data_pos)
        scene.collection.objects.link(lamp_positive)
        
        print("[DEBUG] Light setup complete")

        all_objs = [ob_child for ob_child in context.scene.objects if ob_child.parent == shade_obj] + [shade_obj]

        far_left = min([min([(ob.matrix_world[0][3] + ob.bound_box[i][0] * shade_obj.scale[0]) for i in range(0, 8)]) for ob in all_objs])
        far_right = max([max([(ob.matrix_world[0][3] + ob.bound_box[i][0] * shade_obj.scale[0]) for i in range(0, 8)]) for ob in all_objs])
        far_front = max([max([(ob.matrix_world[1][3] + ob.bound_box[i][1] * shade_obj.scale[1]) for i in range(0, 8)]) for ob in all_objs])
        far_back = min([min([(ob.matrix_world[1][3] + ob.bound_box[i][1] * shade_obj.scale[1]) for i in range(0, 8)]) for ob in all_objs])
        far_bottom = min([min([(ob.matrix_world[2][3] + ob.bound_box[i][2] * shade_obj.scale[2]) for i in range(0, 8)]) for ob in all_objs])
        far_top = max([(ob.matrix_world @ BlenderVector(corner))[2] for ob in all_objs for corner in ob.bound_box])

        dim_x = abs(far_left - far_right)
        dim_y = abs(far_front - far_back)

        loc = ((far_right + far_left) / 2, (far_front + far_back) / 2, far_bottom)

        object_height = far_top - far_bottom
        light_height = far_top + object_height * 0.5
        lamp_positive.location = (loc[0], loc[1], light_height)
        lamp_positive.rotation_euler = (math.radians(0), 0, 0)

        # Ensure we're in object mode before running selection
        if context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        # Deselect all objects
        bpy.ops.object.select_all(action='DESELECT')
        
        print("[DEBUG] Bounds calculated, creating shadow plane")

        bpy.ops.mesh.primitive_plane_add(size=1, enter_editmode=False, align='WORLD', location=loc)
        shadow_plane = context.active_object
        shadow_plane.name = 'ShadowPlane'

        sphor = (shadow_plane.location[0] - (shadow_plane.dimensions[0] / 2))
        spver = ((shadow_plane.dimensions[1] / 2) - shadow_plane.location[1])

        sleft = (sphor - shade_obj.location[0]) * 100
        sright = (shade_obj.location[0] - sphor) * 100
        sfront = (spver - shade_obj.location[1]) * 100
        sback = (shade_obj.location[1] - spver) * 100
        sheight = (far_bottom - shade_obj.location[2]) * 100
        shtable = ";)SHADOWTABLE {:.4f} {:.4f} {:.4f} {:.4f} {:.4f}".format(
            sleft, sright, sfront, sback, sheight)

        scene["shadow_table"] = shtable
        scene.shadow_table = shtable

        shadow_plane.scale.x *= 1.5
        shadow_plane.scale.y *= 1.5
        
        print(f"[DEBUG] ShadowPlane created at {shadow_plane.location}")

        # Apply scale
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

        print("[DEBUG] Applying material")
        mat, material_name = self.create_unique_material("ShadowMaterial")
        shadow_plane.data.materials.append(mat)

        # Prepare for first bake
        context.view_layer.objects.active = shadow_plane
        shadow_plane.select_set(True)
        bpy.ops.object.mode_set(mode='EDIT')

        # First bake
        strength = bpy.context.scene.shadow_strength
        threshold = map_strength_to_threshold(strength)
        print(f"[DEBUG] Mapped shadow_strength={strength} → threshold={threshold}")
        shadow_tex1 = self.bake_and_process(
            context,
            margin=0.01,
            texture_name_suffix="Bake1",
            material=mat,
            threshold=threshold
        )

        # Apply edge softening effect
        self.blur_texture_edges(mat, shadow_tex1)
        print("[DEBUG] Blur node setup complete")
        
        # Assign final texture to ShadowPlane material
        self.assign_final_texture(shadow_plane, shadow_tex1)
        print("[DEBUG] Final texture assigned")

        # Bake the blurred texture to a UV image and assign it to the shadow plane
        blurred_texture_image = self.bake_blurred_texture_to_image(context, shadow_plane, mat)
        print(f"[DEBUG] Blurred texture bake done, image: {blurred_texture_image.name}")

        # **Remove Shadow_bake1 texture after baking**
        print("[DEBUG] Cleanup phase started")
        if "Shadow_Bake1" in bpy.data.images:
            bpy.data.images.remove(bpy.data.images["Shadow_Bake1"])
            
        # Remove ShadowPlane after baking is done
        bpy.data.objects.remove(shadow_plane, do_unlink=True)

        # Cleanup
        bpy.data.objects.remove(lamp_positive)
        scene.render.engine = original_engine
        
        print("[DEBUG] BakeShadow operator complete")

        # Deselect objects
        if context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')

    def restore_selection(self, context, original_selection, original_active):
        """Restores the original selection and active object after baking."""
        # Deselect all objects first
        bpy.ops.object.select_all(action='DESELECT')
        
        # Reselect the original objects
        for obj in original_selection:
            obj.select_set(True)
            
        # Restore the original active object
        context.view_layer.objects.active = original_active

    def execute(self, context):
        if not self.check_for_selected(context):
            return {'CANCELLED'}

        original_active = context.view_layer.objects.active
        original_selection = context.selected_objects[:]

        self.bake_shadow(context)

        self.restore_selection(context, original_selection, original_active)

        # Replace confirm_shadow_save with a message box
        msg_box("'shadow' has been baked and\n can be found in the Texture Images list.", "INFO")

        return {"FINISHED"}
    
class BakeVertex(bpy.types.Operator):
    """Bake lighting to vertex colors and apply changes to the _Col material."""
    bl_idname = "object.bake_vertex"
    bl_label = "Bake Light to Vertex Color"
    bl_options = {'REGISTER', 'UNDO'}
    
    shadow_strength: bpy.props.FloatProperty(
        name="Shadow Strength",
        description="Strength of the shadows",
        default=5.0,
        min=0.0,
        max=10.0
    )

    light_strength: bpy.props.FloatProperty(
        name="Light Strength",
        description="Strength of the light rays",
        default=0.5,
        min=0.0,
        max=10.0
    )
    
    samples: bpy.props.IntProperty(
        name="Samples",
        description="Number of samples for baking",
        default=512,
        min=1,
        max=5000
    )
    
    def get_base_name_for_layers(self, obj):
        base_name = obj.name.split('.')[0]
        extension = ""

        specific_parts = ["body", "wheel", "axle", "spring"]

        if ".w" in obj.name:
            extension = ".w"
        elif ".prm" in obj.name or any(part in obj.name for part in specific_parts):
            extension = ".prm"

        return f"{base_name}{extension}"

    def execute(self, context):
        scene = context.scene
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            self.report({'WARNING'}, "Active object is not a mesh")
            return {'CANCELLED'}

        # Check if the object is in Object mode
        if obj.mode != 'OBJECT':
            self.report({'WARNING'}, "You must be in Object Mode to bake vertex colors.")
            msg_box("You must be in Object Mode to bake vertex colors.", 'ERROR')
            return {'CANCELLED'}

        # Ensure the object has a vertex color layer named 'Col'
        vc_layer = obj.data.vertex_colors.get('Col')
        if not vc_layer:
            vc_layer = obj.data.vertex_colors.new(name='Col')
        obj.data.vertex_colors.active = vc_layer

        # Preserve the original vertex colors
        original_vcols = [loop.color[:] for loop in vc_layer.data]

        # Create temporary vertex color layers for baking
        temp_ao_vc_layer = obj.data.vertex_colors.new(name='TempBakeAO')
        temp_direct_vc_layer = obj.data.vertex_colors.new(name='TempBakeDirect')
        obj.data.vertex_colors.active = temp_ao_vc_layer

        # Set render engine to Cycles and configure settings
        original_engine = scene.render.engine
        scene.render.engine = 'CYCLES'
        original_samples = scene.cycles.samples
        scene.cycles.samples = self.samples

        # Ensure the material setup is correct
        base_name = self.get_base_name_for_layers(obj)
        prefixed_mat_name = f"{base_name}_Col"
        generic_mat_name = "_Col"

        material = bpy.data.materials.get(prefixed_mat_name) or bpy.data.materials.get(generic_mat_name)
        if not material:
            self.report({'WARNING'}, f"Material {prefixed_mat_name} or {generic_mat_name} not found.")
            return {'CANCELLED'}

        # Ensure material is in object material slot
        if material.name not in obj.data.materials:
            obj.data.materials.append(material)

        # Prepare vertex color material node setup with Principled BSDF
        if not material.use_nodes:
            material.use_nodes = True
        nodes = material.node_tree.nodes
        links = material.node_tree.links
        nodes.clear()
        vcol_node = nodes.new(type='ShaderNodeVertexColor')
        bsdf_node = nodes.new(type='ShaderNodeBsdfPrincipled')
        output_node = nodes.new(type='ShaderNodeOutputMaterial')
        links.new(vcol_node.outputs['Color'], bsdf_node.inputs['Base Color'])
        links.new(bsdf_node.outputs['BSDF'], output_node.inputs['Surface'])

        # Ensure the active mesh object is selected
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.ops.object.mode_set(mode='OBJECT')

        # Bake the ambient occlusion (AO) to the temporary vertex color layer
        vcol_node.layer_name = temp_ao_vc_layer.name
        bpy.ops.object.bake(type='AO', use_clear=True, use_selected_to_active=False, margin=2, cage_extrusion=0.0, normal_space='TANGENT', target='VERTEX_COLORS')

        # Switch to the temporary direct lighting vertex color layer
        obj.data.vertex_colors.active = temp_direct_vc_layer

        # Bake the direct lighting to the temporary vertex color layer
        vcol_node.layer_name = temp_direct_vc_layer.name
        bpy.ops.object.bake(type='DIFFUSE', use_clear=True, use_selected_to_active=False, margin=2, cage_extrusion=0.0, normal_space='TANGENT', pass_filter={'DIRECT'}, target='VERTEX_COLORS')

        # Merge the baked AO and direct lighting with the original colors using bmesh
        bm = bmesh.new()
        bm.from_mesh(obj.data)

        # Access vertex color layers in bmesh
        vc_layer_bm = bm.loops.layers.color.get('Col')
        temp_ao_vc_layer_bm = bm.loops.layers.color.get('TempBakeAO')
        temp_direct_vc_layer_bm = bm.loops.layers.color.get('TempBakeDirect')

        for face in bm.faces:
            for loop in face.loops:
                original_color = loop[vc_layer_bm]
                ao_color = loop[temp_ao_vc_layer_bm]
                direct_color = loop[temp_direct_vc_layer_bm]
                # Blend the original color with the AO shadow and direct lighting
                blended_color = [
                    original_color[j] * (1 - self.shadow_strength * (1 - ao_color[j])) + self.light_strength * direct_color[j]
                    for j in range(3)
                ]
                loop[vc_layer_bm] = blended_color + [1.0]

        # Update the mesh
        bm.to_mesh(obj.data)
        bm.free()

        # Delete the temporary vertex color layers
        obj.data.vertex_colors.remove(temp_ao_vc_layer)
        obj.data.vertex_colors.remove(temp_direct_vc_layer)

        # Cleanup and restore settings
        scene.render.engine = original_engine
        scene.cycles.samples = original_samples

        # Restore the correct vertex color layer in the material
        vcol_node.layer_name = 'Col'

        obj.select_set(True)
        context.view_layer.objects.active = obj
        context.view_layer.update()

        self.report({'INFO'}, "Baking completed successfully")
        return {'FINISHED'}
    
    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

class BakeVertexBatch(bpy.types.Operator):
    """Bake lighting to vertex colors on all selected mesh objects."""
    bl_idname = "object.bake_vertex_batch"
    bl_label = "Bake Light to Vertex Color (Selected)"
    bl_options = {'REGISTER', 'UNDO'}

    shadow_strength: bpy.props.FloatProperty(
        name="Shadow Strength",
        description="Strength of the shadows",
        default=5.0,
        min=0.0,
        max=10.0
    )

    light_strength: bpy.props.FloatProperty(
        name="Light Strength",
        description="Strength of the light rays",
        default=0.5,
        min=0.0,
        max=10.0
    )

    # NEW — dropdown with allowed options only
    samples: bpy.props.EnumProperty(
        name="Samples",
        description="Number of samples for baking",
        items=[
            ('64',  "64",  "Fast preview"),
            ('128', "128", "Balanced"),
            ('256', "256", "High quality"),
            ('512', "512", "Very high quality"),
        ],
        default='64',
    )

    def execute(self, context):
        # Only mesh objects from the selection
        mesh_objects = [o for o in context.selected_objects if o.type == 'MESH']
        if not mesh_objects:
            self.report({'WARNING'}, "No mesh objects selected.")
            return {'CANCELLED'}

        prev_active = context.view_layer.objects.active

        # Loop all selected meshes and call the original operator on each
        for obj in mesh_objects:
            print(f"[BakeVertexBatch] Baking {obj.name}")
            context.view_layer.objects.active = obj

            # Call existing single-object bake operator without UI
            bpy.ops.object.bake_vertex(
                'EXEC_DEFAULT',
                shadow_strength=self.shadow_strength,
                light_strength=self.light_strength,
                samples=int(self.samples)       # IMPORTANT: convert enum string to int
            )

        # Restore previous active object
        context.view_layer.objects.active = prev_active

        self.report({'INFO'}, f"Baked {len(mesh_objects)} mesh object(s)")
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
    
class BatchBakeVertexToEnv(bpy.types.Operator):
    """Batch Bake lighting to vertex colors and apply changes to the _Env material."""
    bl_idname = "object.batch_bake_vertex_to_env"
    bl_label = "Batch Bake Light to Vertex Color for _Env"
    bl_options = {'REGISTER', 'UNDO'}
    
    shadow_strength: bpy.props.FloatProperty(
        name="Shadow Strength",
        description="Strength of the shadows",
        default=5.0,
        min=0.0,
        max=10.0
    )

    light_strength: bpy.props.FloatProperty(
        name="Light Strength",
        description="Strength of the light rays",
        default=0.5,
        min=0.0,
        max=10.0
    )
    
    # CHANGED: EnumProperty with fixed options
    samples: bpy.props.EnumProperty(
        name="Samples",
        description="Number of samples for baking",
        items=[
            ('64',  "64",  "Fast preview"),
            ('128', "128", "Balanced"),
            ('256', "256", "High quality"),
            ('512', "512", "Very high quality"),
        ],
        default='64',
    )
    
    def get_base_name_for_layers(self, obj):
        base_name = obj.name.split('.')[0]
        extension = ""

        specific_parts = ["body", "wheel", "axle", "spring"]

        if ".w" in obj.name:
            extension = ".w"
        elif ".prm" in obj.name or any(part in obj.name for part in specific_parts):
            extension = ".prm"

        return f"{base_name}{extension}"

    def batch_bake(self, context):
        scene = context.scene

        # Set render engine to Cycles and configure settings
        original_engine = scene.render.engine
        scene.render.engine = 'CYCLES'
        original_samples = scene.cycles.samples
        scene.cycles.samples = int(self.samples)  # CHANGED: cast enum string to int

        # Bakes all selected objects
        for obj in context.selected_objects:
            if (
                obj.type != 'MESH'
                or not hasattr(obj.data, "vertex_colors")
                or not (getattr(obj, "is_instance", False) or obj.get("is_instance", False))
            ):
                continue

            print(f"Baking at {obj.name}...")
            context.view_layer.objects.active = obj

            # Ensure the object has a vertex color layer named 'Env'
            env_layer = obj.data.vertex_colors.get('Env')
            if not env_layer:
                env_layer = obj.data.vertex_colors.new(name='Env')
            obj.data.vertex_colors.active = env_layer

            # Preserve the original vertex colors
            original_vcols = [loop.color[:] for loop in env_layer.data]

            # Create temporary vertex color layers for baking
            temp_ao_env_layer = obj.data.vertex_colors.new(name='TempBakeAO')
            temp_direct_env_layer = obj.data.vertex_colors.new(name='TempBakeDirect')
            obj.data.vertex_colors.active = temp_ao_env_layer

            # Ensure the material setup is correct
            base_name = self.get_base_name_for_layers(obj)
            prefixed_mat_name = f"{base_name}_Env"
            generic_mat_name = "_Env"

            material = bpy.data.materials.get(prefixed_mat_name) or bpy.data.materials.get(generic_mat_name)
            if not material:
                self.report({'WARNING'}, f"Material {prefixed_mat_name} or {generic_mat_name} not found.")
                continue

            # Ensure material is in object material slot
            if material.name not in obj.data.materials:
                obj.data.materials.append(material)

            # Prepare vertex color material node setup with Principled BSDF
            if not material.use_nodes:
                material.use_nodes = True
            nodes = material.node_tree.nodes
            links = material.node_tree.links
            nodes.clear()
            vcol_node = nodes.new(type='ShaderNodeVertexColor')
            vcol_node.layer_name = 'Env'
            bsdf_node = nodes.new(type='ShaderNodeBsdfPrincipled')
            output_node = nodes.new(type='ShaderNodeOutputMaterial')
            links.new(vcol_node.outputs['Color'], bsdf_node.inputs['Base Color'])
            links.new(bsdf_node.outputs['BSDF'], output_node.inputs['Surface'])

            # Ensure the active mesh object is selected
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            bpy.ops.object.mode_set(mode='OBJECT')

            # Bake the ambient occlusion (AO) to the temporary vertex color layer
            bpy.ops.object.bake(
                type='AO',
                use_clear=True,
                use_selected_to_active=False,
                margin=2,
                cage_extrusion=0.0,
                normal_space='TANGENT',
                target='VERTEX_COLORS'
            )

            # Switch to the temporary direct lighting vertex color layer
            obj.data.vertex_colors.active = temp_direct_env_layer

            # Bake the direct lighting to the temporary vertex color layer
            bpy.ops.object.bake(
                type='DIFFUSE',
                use_clear=True,
                use_selected_to_active=False,
                margin=2,
                cage_extrusion=0.0,
                normal_space='TANGENT',
                pass_filter={'DIRECT'},
                target='VERTEX_COLORS'
            )

            # Merge the baked AO and direct lighting with the original colors using bmesh
            bm = bmesh.new()
            bm.from_mesh(obj.data)

            # Access vertex color layers in bmesh
            env_layer_bm = bm.loops.layers.color.get('Env')
            temp_ao_env_layer_bm = bm.loops.layers.color.get('TempBakeAO')
            temp_direct_env_layer_bm = bm.loops.layers.color.get('TempBakeDirect')

            for face in bm.faces:
                for loop in face.loops:
                    original_color = loop[env_layer_bm]
                    ao_color = loop[temp_ao_env_layer_bm]
                    direct_color = loop[temp_direct_env_layer_bm]
                    blended_color = [
                        original_color[j] * (1 - self.shadow_strength * (1 - ao_color[j])) +
                        self.light_strength * direct_color[j]
                        for j in range(3)
                    ]
                    loop[env_layer_bm] = blended_color + [original_color[3]]  # Preserve original alpha

            # Update the mesh
            bm.to_mesh(obj.data)
            bm.free()

            # Delete the temporary vertex color layers
            obj.data.vertex_colors.remove(temp_ao_env_layer)
            obj.data.vertex_colors.remove(temp_direct_env_layer)

        # Cleanup and restore settings
        scene.render.engine = original_engine
        scene.cycles.samples = original_samples

    def execute(self, context):
        self.batch_bake(context)
        self.report({'INFO'}, "Batch baking completed successfully")
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

class BakeVertexToRGBModelColor(bpy.types.Operator):
    """Bake lighting to vertex colors and apply changes to the _RGBModelColor material."""
    bl_idname = "object.bake_vertex_to_rgbmodelcolor"
    bl_label = "Bake Light to Vertex Color for RGBModelColor"
    bl_options = {'REGISTER', 'UNDO'}
    
    shadow_strength: bpy.props.FloatProperty(
        name="Shadow Strength",
        description="Strength of the shadows",
        default=5.0,
        min=0.0,
        max=10.0
    )

    light_strength: bpy.props.FloatProperty(
        name="Light Strength",
        description="Strength of the light rays",
        default=0.5,
        min=0.0,
        max=10.0
    )
    
    # CHANGED: EnumProperty with fixed options
    samples: bpy.props.EnumProperty(
        name="Samples",
        description="Number of samples for baking",
        items=[
            ('64',  "64",  "Fast preview"),
            ('128', "128", "Balanced"),
            ('256', "256", "High quality"),
            ('512', "512", "Very high quality"),
        ],
        default='64',
    )
    
    def get_base_name_for_layers(self, obj):
        base_name = obj.name.split('.')[0]
        extension = ""

        specific_parts = ["body", "wheel", "axle", "spring"]

        if ".w" in obj.name:
            extension = ".w"
        elif ".prm" in obj.name or any(part in obj.name for part in specific_parts):
            extension = ".prm"

        return f"{base_name}{extension}"

    def batch_bake(self, context):
        scene = context.scene

        # Set render engine to Cycles and configure settings
        original_engine = scene.render.engine
        scene.render.engine = 'CYCLES'
        original_samples = scene.cycles.samples
        scene.cycles.samples = int(self.samples)  # CHANGED: cast enum string to int

        # Bakes all selected objects
        for obj in context.selected_objects:
            if (
                obj.type != 'MESH'
                or not hasattr(obj.data, "vertex_colors")
                or not (getattr(obj, "is_instance", False) or obj.get("is_instance", False))
            ):
                continue

            print(f"Baking at {obj.name}...")
            context.view_layer.objects.active = obj

            # Ensure the object has a vertex color layer named 'RGBModelColor'
            rgb_layer = obj.data.vertex_colors.get('RGBModelColor')
            if not rgb_layer:
                rgb_layer = obj.data.vertex_colors.new(name='RGBModelColor')
            obj.data.vertex_colors.active = rgb_layer

            # Preserve the original vertex colors
            original_vcols = [loop.color[:] for loop in rgb_layer.data]

            # Create temporary vertex color layers for baking
            temp_ao_rgb_layer = obj.data.vertex_colors.new(name='TempBakeAO')
            temp_direct_rgb_layer = obj.data.vertex_colors.new(name='TempBakeDirect')
            obj.data.vertex_colors.active = temp_ao_rgb_layer

            # Ensure the material setup is correct
            base_name = self.get_base_name_for_layers(obj)
            prefixed_mat_name = f"{base_name}_RGBModelColor"
            generic_mat_name = "_RGBModelColor"

            material = bpy.data.materials.get(prefixed_mat_name) or bpy.data.materials.get(generic_mat_name)
            if not material:
                self.report({'WARNING'}, f"Material {prefixed_mat_name} or {generic_mat_name} not found.")
                continue

            # Ensure material is in object material slot
            if material.name not in obj.data.materials:
                obj.data.materials.append(material)

            # Prepare vertex color material node setup with Principled BSDF
            if not material.use_nodes:
                material.use_nodes = True
            nodes = material.node_tree.nodes
            links = material.node_tree.links
            nodes.clear()
            vcol_node = nodes.new(type='ShaderNodeVertexColor')
            vcol_node.layer_name = 'RGBModelColor'
            bsdf_node = nodes.new(type='ShaderNodeBsdfPrincipled')
            output_node = nodes.new(type='ShaderNodeOutputMaterial')
            links.new(vcol_node.outputs['Color'], bsdf_node.inputs['Base Color'])
            links.new(bsdf_node.outputs['BSDF'], output_node.inputs['Surface'])

            # Ensure the active mesh object is selected
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            bpy.ops.object.mode_set(mode='OBJECT')

            # Bake the ambient occlusion (AO) to the temporary vertex color layer
            bpy.ops.object.bake(
                type='AO',
                use_clear=True,
                use_selected_to_active=False,
                margin=2,
                cage_extrusion=0.0,
                normal_space='TANGENT',
                target='VERTEX_COLORS'
            )

            # Switch to the temporary direct lighting vertex color layer
            obj.data.vertex_colors.active = temp_direct_rgb_layer

            # Bake the direct lighting to the temporary vertex color layer
            bpy.ops.object.bake(
                type='DIFFUSE',
                use_clear=True,
                use_selected_to_active=False,
                margin=2,
                cage_extrusion=0.0,
                normal_space='TANGENT',
                pass_filter={'DIRECT'},
                target='VERTEX_COLORS'
            )

            # Merge the baked AO and direct lighting with the original colors using bmesh
            bm = bmesh.new()
            bm.from_mesh(obj.data)

            # Access vertex color layers in bmesh
            rgb_layer_bm = bm.loops.layers.color.get('RGBModelColor')
            temp_ao_rgb_layer_bm = bm.loops.layers.color.get('TempBakeAO')
            temp_direct_rgb_layer_bm = bm.loops.layers.color.get('TempBakeDirect')

            for face in bm.faces:
                for loop in face.loops:
                    original_color = loop[rgb_layer_bm]
                    ao_color = loop[temp_ao_rgb_layer_bm]
                    direct_color = loop[temp_direct_rgb_layer_bm]
                    blended_color = [
                        original_color[j] * (1 - self.shadow_strength * (1 - ao_color[j])) +
                        self.light_strength * direct_color[j]
                        for j in range(3)
                    ]
                    loop[rgb_layer_bm] = blended_color + [1.0]

            # Update the mesh
            bm.to_mesh(obj.data)
            bm.free()

            # Delete the temporary vertex color layers
            obj.data.vertex_colors.remove(temp_ao_rgb_layer)
            obj.data.vertex_colors.remove(temp_direct_rgb_layer)

        # Cleanup and restore settings
        scene.render.engine = original_engine
        scene.cycles.samples = original_samples

    def execute(self, context):
        self.batch_bake(context)
        self.report({'INFO'}, "Batch baking completed successfully")
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

"""
TEXTURE ANIMATIONS -------------------------------------------------------
"""

class ButtonCopyUvToFrame(bpy.types.Operator):
    bl_idname = "texanim.copy_uv_to_frame"
    bl_label = "UV to Frame"
    bl_description = "Copies the UV coordinates of the currently selected face to the texture animation frame"

    def execute(self, context):
        copy_uv_to_frame(context)
        context.area.tag_redraw()
        return{"FINISHED"}

class ButtonCopyFrameToUv(bpy.types.Operator):
    bl_idname = "texanim.copy_frame_to_uv"
    bl_label = "Frame to UV"
    bl_description = "Copies the UV coordinates of the frame to the currently selected face"

    def execute(self, context):
        copy_frame_to_uv(context)
        context.area.tag_redraw()
        return{"FINISHED"}
    
class PreviewNextFrame(bpy.types.Operator):
    bl_idname = "texanim.prev_next"
    bl_label = "Preview Next"
    bl_description = "Loads the next frame and previews it on the selected face"

    def execute(self, context):
        scene = context.scene

        # Ensure we don't go beyond the maximum number of frames
        if scene.ta_current_frame < scene.ta_max_frames - 1:
            scene.ta_current_frame += 1
        else:
            scene.ta_current_frame = 0  # Optionally loop back to the first frame

        copy_frame_to_uv(context)

        # Update the UI to reflect the changes
        context.area.tag_redraw()
        
        return {"FINISHED"}

class PreviewPrevFrame(bpy.types.Operator):
    bl_idname = "texanim.prev_prev"
    bl_label = "Preview Previous"
    bl_description = "Loads the previous frame and previews it on the selected face"

    def execute(self, context):
        scene = context.scene

        # Ensure we don't go below the first frame
        if scene.ta_current_frame > 0:
            scene.ta_current_frame -= 1
        else:
            scene.ta_current_frame = scene.ta_max_frames - 1  # Optionally loop to the last frame

        copy_frame_to_uv(context)

        # Update the UI to reflect the changes
        context.area.tag_redraw()

        return {"FINISHED"}

class TexAnimTransform(bpy.types.Operator):
    bl_idname = "texanim.transform"
    bl_label = "Transform Animation"
    bl_description = "Creates a linear animation from one frame to another"

    def execute(self, context):
        scene = context.scene
        
        # Check if the slot limit is 0
        if scene.ta_max_slots == 0:
            msg_box("Slot limit is 0. Please increase the slot limit before creating an animation.", "ERROR")
            return {'FINISHED'}

        ta = eval(scene.texture_animations)
        slot = scene.ta_current_slot

        if slot >= len(ta):
            msg_box("Slot index out of range.", "ERROR")
            return {'FINISHED'}

        max_frames = scene.ta_max_frames
        frame_start = scene.ta_frame_start
        frame_end = scene.ta_frame_end

        # Bounds check against current slot's max_frames
        if frame_start >= max_frames or frame_end >= max_frames:
            msg_box("Frame index out of range. Please increase Frames Limit if needed.", "ERROR")
            return {'FINISHED'}

        # Remember original values for the message
        orig_start = frame_start
        orig_end = frame_end

        # Ensure start <= end for interpolation math
        if frame_end < frame_start:
            frame_start, frame_end = frame_end, frame_start

        # Shortcut: if start == end, nothing to interpolate – just ensure delay/texture are set
        if frame_start == frame_end:
            idx = frame_start
            ta[slot]["frames"][idx]["delay"] = scene.ta_delay
            ta[slot]["frames"][idx]["texture"] = scene.ta_texture
            # No UV change needed, but we could also copy current frame UVs here if desired

            scene.texture_animations = str(ta)
            update_ta_current_frame(self, context)

            msg_box(f"Single-frame transform applied at frame {idx}.", icon="FILE_TICK")
            return {'FINISHED'}

        # Read UVs from the start frame
        uv_start = (
            (ta[slot]["frames"][frame_start]["uv"][0]["u"],
             ta[slot]["frames"][frame_start]["uv"][0]["v"]),
            (ta[slot]["frames"][frame_start]["uv"][1]["u"],
             ta[slot]["frames"][frame_start]["uv"][1]["v"]),
            (ta[slot]["frames"][frame_start]["uv"][2]["u"],
             ta[slot]["frames"][frame_start]["uv"][2]["v"]),
            (ta[slot]["frames"][frame_start]["uv"][3]["u"],
             ta[slot]["frames"][frame_start]["uv"][3]["v"])
        )

        # And from the end frame
        uv_end = (
            (ta[slot]["frames"][frame_end]["uv"][0]["u"],
             ta[slot]["frames"][frame_end]["uv"][0]["v"]),
            (ta[slot]["frames"][frame_end]["uv"][1]["u"],
             ta[slot]["frames"][frame_end]["uv"][1]["v"]),
            (ta[slot]["frames"][frame_end]["uv"][2]["u"],
             ta[slot]["frames"][frame_end]["uv"][2]["v"]),
            (ta[slot]["frames"][frame_end]["uv"][3]["u"],
             ta[slot]["frames"][frame_end]["uv"][3]["v"])
        )

        nframes = (frame_end - frame_start) + 1
        denom = (frame_end - frame_start)

        for i in range(nframes):
            current_frame = frame_start + i
            prog = i / denom  # safe because frame_end != frame_start here

            ta[slot]["frames"][current_frame]["delay"] = scene.ta_delay
            ta[slot]["frames"][current_frame]["texture"] = scene.ta_texture

            for j in range(4):
                new_u = uv_start[j][0] * (1 - prog) + uv_end[j][0] * prog
                new_v = uv_start[j][1] * (1 - prog) + uv_end[j][1] * prog

                ta[slot]["frames"][current_frame]["uv"][j]["u"] = new_u
                ta[slot]["frames"][current_frame]["uv"][j]["v"] = new_v

        # 🔸 IMPORTANT: do NOT touch frame_count here.
        # Transform only reshapes existing frames inside [frame_start, frame_end].
        # Frame count / allocation is handled when user sets Frames Limit (ta_max_frames)
        # and by Grid (which already updates frame_count safely).

        scene.texture_animations = str(ta)
        update_ta_current_frame(self, context)

        msg_box("Animation from frame {} to {} completed.".format(
            orig_start, orig_end),
            icon="FILE_TICK"
        )

        return {'FINISHED'}

class TexAnimGrid(bpy.types.Operator):
    bl_idname = "texanim.grid"
    bl_label = "Grid Animation"
    bl_description = "Creates an animation based on a grid texture."

    def execute(self, context):
        scene = context.scene

        # Check if the slot limit is 0
        if scene.ta_max_slots == 0:
            msg_box("Slot limit is 0. Please increase the slot limit before creating a grid animation.", "ERROR")
            return {'FINISHED'}

        ta = eval(scene.texture_animations)
        slot = scene.ta_current_slot

        if slot >= len(ta):
            msg_box("Slot index out of range.", "ERROR")
            return {'FINISHED'}

        # Current info for this slot
        max_frames = scene.ta_max_frames
        frame_start = scene.ta_frame_start
        grid_x = scene.grid_x
        grid_y = scene.grid_y
        nframes = grid_x * grid_y

        # We need at least frame_start + nframes frames available
        needed_frames = frame_start + nframes

        # If the UI limit is too small, warn the user (keeps existing behaviour)
        if needed_frames > max_frames:
            msg_box(
                "Frame out of range.\n"
                "Please set the amount of frames to at least {}.".format(needed_frames),
                "ERROR"
            )
            return {'FINISHED'}

        # Ensure the internal frames list is large enough for this slot
        # (in case something got out of sync)
        frames_list = ta[slot]["frames"]
        while len(frames_list) < needed_frames:
            new_frame = rvstruct.Frame().as_dict()
            frames_list.append(new_frame)

        i = 0
        for y in range(grid_x):
            for x in range(grid_y):
                uv0 = (x / grid_x,     y / grid_y)
                uv1 = ((x + 1) / grid_x, y / grid_y)
                uv2 = ((x + 1) / grid_x, (y + 1) / grid_y)
                uv3 = (x / grid_x,     (y + 1) / grid_y)

                idx = frame_start + i

                frames_list[idx]["delay"] = scene.ta_delay
                frames_list[idx]["texture"] = scene.ta_texture

                frames_list[idx]["uv"][0]["u"] = uv0[0]
                frames_list[idx]["uv"][0]["v"] = uv0[1]
                frames_list[idx]["uv"][1]["u"] = uv1[0]
                frames_list[idx]["uv"][1]["v"] = uv1[1]
                frames_list[idx]["uv"][2]["u"] = uv2[0]
                frames_list[idx]["uv"][2]["v"] = uv2[1]
                frames_list[idx]["uv"][3]["u"] = uv3[0]
                frames_list[idx]["uv"][3]["v"] = uv3[1]

                i += 1

        # 🔹 Update frame_count so export writes ALL generated frames
        ta[slot]["frame_count"] = max(ta[slot].get("frame_count", 0), needed_frames)

        # Keep UI in sync with actual data
        scene.ta_max_frames = ta[slot]["frame_count"]

        # Store back once with the updated frame_count
        scene.texture_animations = str(ta)

        # Refresh current frame UI
        update_ta_current_frame(self, context)

        msg_box("Animation of {} frames completed.".format(nframes), icon="FILE_TICK")

        return {'FINISHED'}
    
class TexAnimAssignSlot(bpy.types.Operator):
    bl_idname = "texanim.assign_anim_slot"
    bl_label = "Assign Anim Slot"
    bl_description = "Assign the current animation slot to the selected faces and enable texture animation"

    def execute(self, context):
        scene = context.scene
        obj = context.object

        if not obj or obj.type != 'MESH' or not obj.data:
            msg_box("Please select a valid mesh object in Edit Mode.", "ERROR")
            return {'CANCELLED'}

        if obj.mode != 'EDIT':
            bpy.ops.object.mode_set(mode='EDIT')

        import bmesh
        bm = bmesh.from_edit_mesh(obj.data)

        # Get / create layers
        anim_slot_layer = bm.faces.layers.int.get("Anim Slot")
        if anim_slot_layer is None:
            anim_slot_layer = bm.faces.layers.int.new("Anim Slot")

        type_layer = bm.faces.layers.int.get("Type")
        if type_layer is None:
            type_layer = bm.faces.layers.int.new("Type")

        selected_faces = [f for f in bm.faces if f.select]
        if not selected_faces:
            msg_box("Please select at least one face.", "ERROR")
            return {'CANCELLED'}

        slot = scene.ta_current_slot

        for f in selected_faces:
            f[anim_slot_layer] = slot
            # Enable texture animation bit in the Type field
            f[type_layer] |= FACE_TEXANIM

        bmesh.update_edit_mesh(obj.data)
        if context.area:
            context.area.tag_redraw()

        return {'FINISHED'}

"""
VERTEX COLORS -----------------------------------------------------------------
"""

class VertexAndAlphaLayer(bpy.types.Operator):
    """Setup Vertex Color and Alpha Layers and create generic named materials if they do not exist."""
    bl_idname = "mesh.vertex_color_and_alpha_setup"
    bl_label = "Setup Vertex Color and Alpha Layers"
    bl_description = "Creates necessary vertex color layers and materials if they do not exist."

    @classmethod
    def poll(cls, context):
        obj = context.object
        return obj and obj.type == 'MESH' and obj.mode == 'EDIT'

    def execute(self, context):
        for obj in context.selected_objects:
            if obj.type == 'MESH':
                mesh = obj.data
                bm = bmesh.from_edit_mesh(mesh)

                # Define the layers to be checked or created
                layers = ['Col', 'Alpha']

                for layer_name in layers:
                    # Check if the specific layer already exists
                    created_layer = bm.loops.layers.color.get(layer_name)
                    if not created_layer:
                        created_layer = bm.loops.layers.color.new(layer_name)
                        # Set default color to gray (0.5, 0.5, 0.5) with full opacity (1.0) for both layers
                        default_color = (0.5, 0.5, 0.5, 1.0) if layer_name == 'Alpha' else (1.0, 1.0, 1.0, 1.0)
                        for face in bm.faces:
                            if face.select:  # Apply to selected faces only
                                for loop in face.loops:
                                    loop[created_layer] = default_color
                        self.report({'INFO'}, f"{layer_name} vertex color layer created for {obj.name}.")
                    else:
                        for face in bm.faces:
                            if face.select:  # Ensure selected faces have the correct layer data
                                for loop in face.loops:
                                    loop[created_layer] = (1.0, 1.0, 1.0, 1.0)  # Reapply default white color with full opacity
                        self.report({'INFO'}, f"{layer_name} vertex color layer already exists for {obj.name}.")

                bmesh.update_edit_mesh(mesh, destructive=True)

                # Ensure materials are set up for the layers and assigned to selected faces
                self.setup_materials(obj, layers)
                self.reassign_materials_to_selected_faces(bm, obj, layers)

                # Recreate the vertex color and alpha layers if they were removed
                self.reapply_vertex_colors_to_selected_faces(bm, layers, mesh)

                # Trigger the MaterialAssignment operator to assign materials automatically
                bpy.ops.object.assign_materials()

        return {'FINISHED'}

    def setup_materials(self, obj, attributes):
        obj_name = obj.name.split('.')[0]  # Get the base name of the object
        
        # Define the potential shared material names based on the "worldname"
        worldname_materials = {attr_name: f"{obj_name}.w_{attr_name}" for attr_name in attributes}
        
        for attr_name in attributes:
            # First, try to find an existing material with the specific worldname
            material = bpy.data.materials.get(worldname_materials[attr_name])

            if not material:
                # If the specific worldname material doesn't exist, check for a generic one
                mat_name_generic = f"_{attr_name}"
                material = bpy.data.materials.get(mat_name_generic)

                if not material:
                    # If no generic material exists, create one
                    material = bpy.data.materials.new(name=mat_name_generic)
                    material.use_nodes = True
                    nodes = material.node_tree.nodes
                    nodes.clear()
                    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
                    output = nodes.new('ShaderNodeOutputMaterial')
                    vcol = nodes.new('ShaderNodeVertexColor')
                    vcol.layer_name = attr_name
                    bsdf.inputs['Base Color'].default_value = (0.5, 0.5, 0.5, 1.0) if attr_name == 'Alpha' else (1.0, 1.0, 1.0, 1.0)
                    material.node_tree.links.new(vcol.outputs['Color'], bsdf.inputs['Base Color'])
                    material.node_tree.links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
                    self.report({'INFO'}, f"Col/Alpha material created.")
            
            # Ensure the material is assigned to the object
            if material.name not in obj.data.materials:
                obj.data.materials.append(material)

    def reassign_materials_to_selected_faces(self, bm, obj, attributes):
        for face in bm.faces:
            if face.select:
                for attr_name in attributes:
                    material_index = obj.data.materials.find(f"_{attr_name}")
                    if material_index != -1:
                        face.material_index = material_index

        bmesh.update_edit_mesh(obj.data, destructive=True)

    def reapply_vertex_colors_to_selected_faces(self, bm, layers, mesh):
        for layer_name in layers:
            created_layer = bm.loops.layers.color.get(layer_name)
            if created_layer:
                for face in bm.faces:
                    if face.select:
                        for loop in face.loops:
                            loop[created_layer] = (1.0, 1.0, 1.0, 1.0)  # Reapply white color with full opacity
        bmesh.update_edit_mesh(mesh, destructive=True)

class VertexColorRemove(bpy.types.Operator):
    bl_idname = "vertexcolor.remove_layer"
    bl_label = "Remove Vertex Color and Alpha Layers"
    bl_description = "Clears the active vertex color and alpha data from selected faces in the selected meshes"

    @classmethod
    def poll(cls, context):
        obj = context.object
        return obj and obj.type == 'MESH' and obj.mode == 'EDIT'

    def execute(self, context):
        for obj in context.selected_objects:
            if obj.type == 'MESH':
                mesh = obj.data
                bm = bmesh.from_edit_mesh(mesh)

                # Access vertex color and alpha layers
                vc_layer = bm.loops.layers.color.get("Col")
                va_layer = bm.loops.layers.color.get("Alpha")

                # Clear vertex color and alpha data for selected faces
                for face in bm.faces:
                    if face.select:  # Check if the face is selected
                        for loop in face.loops:
                            if vc_layer is not None:
                                loop[vc_layer] = (0.0, 0.0, 0.0, 1.0)  # Set color to transparent black
                            if va_layer is not None:
                                loop[va_layer] = (0.0, 0.0, 0.0, 1.0)  # Set alpha to transparent black

                bmesh.update_edit_mesh(mesh, destructive=True)

                # Clear material assignment from selected faces only
                materials_to_clear = [mat for mat in obj.data.materials if mat.name.endswith('_Col') or mat.name.endswith('_Alpha')]

                for face in bm.faces:
                    if face.select:  # Check if the face is selected
                        for mat in materials_to_clear:
                            if face.material_index == obj.data.materials.find(mat.name):
                                face.material_index = 0  # Set to 0 to ensure valid range

                bmesh.update_edit_mesh(mesh, destructive=True)

        self.report({'INFO'}, "Vertex color and alpha data cleared from selected faces, and materials cleared.")
        return {'FINISHED'}

class SetVertexColor(bpy.types.Operator):
    bl_idname = "vertexcolor.set_color"
    bl_label = "Set Vertex Color"
    bl_description = "Sets the vertex colors on the active vertex color layer using a scene-wide color picker"

    @classmethod
    def poll(cls, context):
        obj = context.object
        return obj and obj.type == 'MESH' and obj.mode == 'EDIT'

    def execute(self, context):
        for eo in context.selected_objects:
            if eo.type == 'MESH':
                bm = bmesh.from_edit_mesh(eo.data)

                vc_layer = bm.loops.layers.color.get("Col")
                if not vc_layer:
                    self.report({'WARNING'}, f"No active vertex color layer found for {eo.name}.")
                    continue

                selmode = context.tool_settings.mesh_select_mode
                color = context.scene.vertex_color_picker

                for face in bm.faces:
                    for loop in face.loops:
                        if (selmode[0] and loop.vert.select) or (selmode[1] and loop.edge.select) or (selmode[2] and face.select):
                            loop[vc_layer] = (color[0], color[1], color[2], 1.0)  # Set the alpha to 1.0

                bmesh.update_edit_mesh(eo.data, destructive=False)
                self.report({'INFO'}, f"Vertex color set for {eo.name}.")
        return {'FINISHED'}

class SetVertexAlpha(bpy.types.Operator):
    bl_idname = "vertexcolor.set_alpha"
    bl_label = "Set Vertex Alpha"
    bl_description = "Adjusts alpha on a specified vertex color layer for selected faces"

    @classmethod
    def poll(cls, context):
        obj = context.object
        return obj and obj.type == 'MESH'

    def execute(self, context):
        for eo in context.selected_objects:
            if eo.type == 'MESH':
                bm = bmesh.from_edit_mesh(eo.data)

                va_layer = bm.loops.layers.color.get("Alpha")
                if not va_layer:
                    self.report({'WARNING'}, f"No vertex color layer with 'Alpha' in its name found for {eo.name}.")
                    continue

                # Retrieve the alpha percentage from the scene property and update the vertex_alpha
                alpha_percent = int(context.scene.vertex_alpha_percentage)
                alpha_value = alpha_percent / 100.0  # Normalize to 0-1
                context.scene.vertex_alpha = alpha_value  # Update the scene's vertex_alpha property

                grayscale_value = 1.0 - alpha_value  # Set color based on the inverse of alpha value

                for face in bm.faces:
                    if face.select:
                        for loop in face.loops:
                            loop[va_layer] = (grayscale_value, grayscale_value, grayscale_value, alpha_value)

                bmesh.update_edit_mesh(eo.data, destructive=False)
                self.report({'INFO'}, f"Alpha adjusted to {alpha_percent}% for selected faces on the chosen layer for {eo.name}.")
        return {'FINISHED'}

class CarAutoShader(bpy.types.Operator):
    bl_idname = "object.car_auto_shader"
    bl_label = "Auto Shader Bake"
    bl_description = "Bake lighting into vertex colors with base color"

    @classmethod
    def poll(cls, context):
        obj = context.object
        return obj and obj.type == 'MESH'

    def execute(self, context):
        scene = context.scene
        base_color = scene.car_shader_color

        # --- Create temp lights in a safe way (scene collection, object mode) ---
        prev_active = context.view_layer.objects.active
        prev_mode = prev_active.mode if prev_active else 'OBJECT'

        if context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        def create_temp_light(name, location):
            light_data = bpy.data.lights.new(name=name, type='POINT')
            light_data.energy = 3500.0
            light_obj = bpy.data.objects.new(name, light_data)
            light_obj.location = BlenderVector(location)
            context.scene.collection.objects.link(light_obj)
            return light_obj

        temp_lights = [
            create_temp_light("TempLight1", (4, 1.5, 7)),
            create_temp_light("TempLight2", (-4, -1.5, 7)),
        ]

        # Cache light info (avoid property lookups in the hot loop)
        light_positions = [l.location.copy() for l in temp_lights]
        light_energies = [float(l.data.energy) for l in temp_lights]
        light_count = len(temp_lights)

        try:
            # Process each selected mesh
            for obj in context.selected_objects:
                if obj.type != 'MESH' or not obj.visible_get():
                    continue

                me = obj.data
                bm = bmesh.new()
                bm.from_mesh(me)
                bm.verts.ensure_lookup_table()
                bm.faces.ensure_lookup_table()

                # Ensure layers exist (BMesh loop color layers)
                col_layer = bm.loops.layers.color.get("Col") or bm.loops.layers.color.new("Col")
                alpha_layer = bm.loops.layers.color.get("Alpha") or bm.loops.layers.color.new("Alpha")

                mw = obj.matrix_world
                nmat = mw.to_3x3()

                # Optional speedup: compute lighting per-vertex once, then reuse for loops
                v_light = [0.0] * len(bm.verts)
                for i, v in enumerate(bm.verts):
                    world_pos = mw @ v.co
                    world_n = (nmat @ v.normal).normalized()

                    lv = 0.0
                    for lp, e in zip(light_positions, light_energies):
                        to_light = (lp - world_pos)
                        to_light.normalize()
                        b = world_n.dot(to_light)
                        if b > 0.0:
                            lv += b * e

                    lv = lv / (light_count * 1000.0)
                    if lv < 0.1:
                        lv = 0.1
                    elif lv > 1.0:
                        lv = 1.0
                    v_light[i] = lv

                # Write loop colors
                for face in bm.faces:
                    for loop in face.loops:
                        li = v_light[loop.vert.index]
                        loop[col_layer] = (
                            base_color[0] * li,
                            base_color[1] * li,
                            base_color[2] * li,
                            1.0
                        )
                        loop[alpha_layer] = (0.0, 0.0, 0.0, 1.0)

                bm.to_mesh(me)
                bm.free()
                me.update()

                # If you really need it, do it once per object, but it's expensive:
                # context.view_layer.objects.active = obj
                # bpy.ops.object.assign_materials()

        finally:
            # cleanup lights even if something fails
            for l in temp_lights:
                if l and l.name in bpy.data.objects:
                    bpy.data.objects.remove(l, do_unlink=True)

            # restore previous mode
            if prev_active:
                context.view_layer.objects.active = prev_active
                try:
                    bpy.ops.object.mode_set(mode=prev_mode)
                except Exception:
                    pass

        self.report({'INFO'}, "Vertex colors and alpha baked based on lighting.")
        return {'FINISHED'}
