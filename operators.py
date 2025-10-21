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
from .common import generate_fob_name, create_directional_fob_mesh_ui
from .layers import set_face_env, create_or_assign_env_material
from .parameters_out_redux import append_aerial_info, append_axle_info, append_back_left_wheel, append_back_right_wheel
from .parameters_out_redux import append_front_left_wheel, append_front_right_wheel, append_pin_info, append_spring_info
from .parameters_out_redux import compare_and_adjust_axle_lengths, remove_imported_axles, compare_and_adjust_spring_lengths
from .parameters_out_redux import remove_imported_springs, compare_and_adjust_pin_lengths, remove_imported_pins
from .taz_in import create_zone
from .texanim import copy_frame_to_uv, copy_uv_to_frame
from .tools import trigger_type_items, fob_type_items, visibox_type_items
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

        try:
            if frmt == FORMAT_UNK:
                self.report({'ERROR'}, "Unsupported format.")
                return {'CANCELLED'}

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

                return {'FINISHED'}

            else:
                self.report({'ERROR'}, "Format not yet supported: {}".format(FORMATS.get(frmt, "Unknown Format")))
                return {'CANCELLED'}

            for area in context.screen.areas:
                if area.type in ['VIEW_3D', 'PROPERTIES']:
                    area.tag_redraw()

            self.report({'INFO'}, "Import completed in {:.2f} seconds".format(time.time() - start_time))

        except Exception as e:
            self.report({'ERROR'}, "Failed to import: {}".format(str(e)))
            return {'CANCELLED'}
        finally:
            context.window.cursor_set("DEFAULT")
            return {"FINISHED"}

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
            ('FIN', "FIN (.fin)", "Instance file"),
            ('FOB', "FOB (.fob)", "FOB object file"),
            ('HUL', "HUL (.hul)", "Hull file"),
            ('LIT', "LIT (.lit)", "Light file"),
            ('NCP', "NCP (.ncp)", "Collision file"),
            ('PRM', "PRM (.prm)", "Mesh file"),
            ('RIM', "RIM (.rim)", "Mirror file"),
            ('TAZ', "TAZ (.taz)", "Track zone file"),
            ('FAN', "FAN (.fan)", "AI Nodes file"),
            ('PAN', "PAN (.pan)", "Position Nodes file"),
            ('TRI', "TRI (.tri)", "Trigger file"),
            ('VIS', "VIS (.vis)", "Visibox file"),
            ('W', "W (.w)", "World file"),
            ('M', "M (.m)", "Model file"),
        ],
        update=None
    )

    def execute(self, context):
        if not self.filepath:
            self.filepath = context.scene.get("last_exported_filepath", "")
        if not self.format_type:
            self.format_type = context.scene.get("last_exported_format", "")

        # Force the format_type to match the actual file extension
        ext_map = {
            ".fin": "FIN", ".fob": "FOB", ".hul": "HUL", ".lit": "LIT",
            ".ncp": "NCP", ".prm": "PRM", ".rim": "RIM", ".taz": "TAZ",
            ".fan": "FAN", ".pan": "PAN", ".tri": "TRI", ".vis": "VIS",
            ".w": "W", ".m": "M"
        }
        ext = os.path.splitext(self.filepath)[1].lower()
        if ext in ext_map:
            self.format_type = ext_map[ext]

        print(f"Exporting to filepath: {self.filepath}, format: {self.format_type}")

        if not self.filepath:
            print("Error: Filepath is not set.")
            return {'CANCELLED'}

        # Save for future reuse
        context.scene.last_exported_filepath = self.filepath
        context.scene.last_exported_format = self.format_type

        result = exec_export(self.filepath, self.format_type, context)
        return result

    def invoke(self, context, event):
        # Open the file browser to select the export path
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
            scene["level_texture_base"] = "car"
            self.report({'INFO'}, "Using 'car' as level texture base.")
        elif self.level_texture_base.strip():
            scene["level_texture_base"] = self.level_texture_base.strip().lower()
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

            if context.scene.get("skip_texture_prompt_once", False):
                del context.scene["skip_texture_prompt_once"]
                m_out.export_file(filepath, context.scene)
                return {'FINISHED'}

            print("Checking textures before exporting .m file...")
            export_folder = os.path.dirname(filepath)
            missing = check_missing_textures(export_folder)

            if missing:
                print(f"[WARNING] {len(missing)} texture(s) not found in export folder, but continuing anyway.")
                print("[INFO] RVGL will find textures from its own folders")

            model_name = os.path.splitext(os.path.basename(filepath))[0].lower()
            context.scene.last_exported_filepath = filepath
            context.scene["skip_texture_prompt_once"] = True
            bpy.ops.wm.prompt_texture_prefix_model('INVOKE_DEFAULT', model_name=model_name)
            return {'CANCELLED'}

        else:
            print(f"[ERROR] Export format '{frmt}' is not handled.")
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
        scene[f"m_model_name_{self.slot_index}"] = self.model_name

        # Store selected choice and path
        scene[f"m_texture_mode_{self.slot_index}"] = self.choice
        if self.choice == 'LEVEL_TEXTURES':
            if not os.path.isdir(self.texture_folder):
                self.report({'ERROR'}, "Invalid folder path")
                return {'CANCELLED'}
            scene[f"m_texture_path_{self.slot_index}"] = self.texture_folder

        elif self.choice == 'TEXTURE_NAME':
            if not self.texture_file.lower().endswith('.bmp') or not os.path.isfile(self.texture_file):
                self.report({'ERROR'}, "Please select a valid .bmp file")
                return {'CANCELLED'}
            scene[f"m_texture_path_{self.slot_index}"] = self.texture_file

        else:  # VERTEX_COLOR
            scene[f"m_texture_path_{self.slot_index}"] = ""  # Clear path

        print(f"[SLOT {self.slot_index}] {self.model_name} → {self.choice}, Path: {scene[f'm_texture_path_{self.slot_index}']}")

        # If this was a .m or .fin import that was cancelled earlier
        filepath = scene.get("pending_import_filepath", "")
        if filepath:
            del scene["pending_import_filepath"]  # Clear it
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

        # Save texture config
        for i in range(MAX_MODEL_SLOTS):
            if not scene.get(f"m_model_name_{i}", ""):
                scene[f"m_model_name_{i}"] = self.model_name
                scene[f"m_texture_mode_{i}"] = self.choice
                scene[f"m_texture_path_{i}"] = self.texture_path_input
                break

        # Handle single export without a queue
        if not hasattr(scene, "m_models_prompt_queue"):
            # Mark that the prompt has already occurred
            context.scene["skip_texture_prompt_once"] = True
            bpy.ops.export_scene.revolt('EXEC_DEFAULT')
            return {'FINISHED'}

        # Continue queue if more models left
        scene.m_models_prompt_index += 1
        if scene.m_models_prompt_index < len(scene.m_models_prompt_queue):
            next_model = scene.m_models_prompt_queue[scene.m_models_prompt_index]
            bpy.ops.wm.prompt_texture_prefix_model('INVOKE_DEFAULT', model_name=next_model)
        else:
            # All prompts done
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

    def execute(self, context):
        context.scene['existing_objects'] = list(bpy.data.objects.keys())
        bpy.ops.import_scene.revolt('INVOKE_DEFAULT')
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if event.type == 'TIMER':
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

                return {'FINISHED'}

        return {'PASS_THROUGH'}

    def invoke(self, context, event):
        context.window_manager.event_timer_add(0.1, window=context.window)
        return self.execute(context)

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

    def execute(self, context):
        context.scene['existing_objects'] = list(bpy.data.objects.keys())
        bpy.ops.import_scene.revolt('INVOKE_DEFAULT')
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if event.type == 'TIMER':
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

                return {'FINISHED'}

        return {'PASS_THROUGH'}

    def invoke(self, context, event):
        context.window_manager.event_timer_add(0.1, window=context.window)
        return self.execute(context)

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

    def execute(self, context):
        context.scene['existing_objects'] = list(bpy.data.objects.keys())
        bpy.ops.import_scene.revolt('INVOKE_DEFAULT')
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if event.type == 'TIMER':
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

                return {'FINISHED'}

        return {'PASS_THROUGH'}

    def invoke(self, context, event):
        context.window_manager.event_timer_add(0.1, window=context.window)
        return self.execute(context)

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
    
"""
INSTANCES -----------------------------------------------------------------------
"""

class SetInstanceProperty(bpy.types.Operator):
    bl_idname = "instances.set_instance_property"
    bl_label = "Mark as Instance"
    bl_description = "Marks all selected objects as instances and stores texture base"
    
    texture_base: bpy.props.StringProperty(
        name="Texture Base",
        description="Base name for level textures (e.g. 'elementary1')",
        default="texture"
    )

    def execute(self, context):
        for obj in context.selected_objects:
            if obj.type == 'MESH' and obj.mode == 'OBJECT':
                obj["is_instance"] = True
                obj["fin_env"] = True
                obj["fin_texture_base"] = self.texture_base
                create_or_assign_env_material(obj)
                print(f"Marked {obj.name} as instance with fin_texture_base = {self.texture_base}")
        self.report({'INFO'}, f"Marked {len(context.selected_objects)} objects as is_instance")
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

class RemoveInstanceProperty(bpy.types.Operator):
    bl_idname = "instances.rem_instance_property"
    bl_label = "Remove Instance property"
    bl_description = "Removes the 'is_instance' property from all selected objects"

    def execute(self, context):
        removed_count = 0

        for obj in context.selected_objects:
            # Check if 'is_instance' property exists and then remove it
            if "is_instance" in obj:
                del obj["is_instance"]
                removed_count += 1
                
            if "fin_texture_base" in obj:
                del obj["fin_texture_base"]

        context.view_layer.update()
        self.report({'INFO'}, f"Removed 'is_instance' property from {removed_count} objects")
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

        ob = create_sphere(scene, center, radius, filename)

        if ob.name not in context.collection.objects:
            context.collection.objects.link(ob)
        else:
            self.report({'WARNING'}, f"Object '{ob.name}' already exists")
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

class MaterialAssignmentAuto(bpy.types.Operator):
    """Assign Materials to All Meshes Automatically"""
    bl_idname = "object.assign_materials_auto"
    bl_label = "Assign Materials Automatically"
    bl_options = {'REGISTER', 'UNDO'}

    car_parts_prefixes = ["body", "wheel", "axle", "spring", "pin", "spinner"]

    def execute(self, context):
        print("[DEBUG] Starting MaterialAssignmentAuto")

        if bpy.context.mode != 'OBJECT':
            print("[DEBUG] Switching to OBJECT mode")
            bpy.ops.object.mode_set(mode='OBJECT')

        mesh_objects = [obj for obj in bpy.data.objects if obj.type == 'MESH']
        print(f"[DEBUG] Found {len(mesh_objects)} mesh objects")

        original_active_object = context.view_layer.objects.active
        if not (original_active_object and original_active_object.type == 'MESH'):
            print("[ERROR] No valid active mesh object")
            self.report({'WARNING'}, "No active mesh object with material choice found.")
            return {'CANCELLED'}

        active_material_choice = original_active_object.data.material_choice
        print(f"[DEBUG] Active material choice: {active_material_choice}")

        existing_textures = self.get_existing_textures()
        print(f"[DEBUG] Found {len(existing_textures)} existing textures")

        for obj in mesh_objects:
            obj.data.material_choice = active_material_choice

        if not context.scene.get("level_texture_base", "").strip():
            print("[ERROR] level_texture_base not set")
            bpy.ops.scene.prompt_texture_base('INVOKE_DEFAULT')
            return {'CANCELLED'}

        self.assign_materials_to_all(mesh_objects, existing_textures)

        print("[DEBUG] Material assignment done, restoring selection")
        bpy.ops.object.select_all(action='DESELECT')
        for obj in mesh_objects:
            obj.select_set(True)
        context.view_layer.objects.active = original_active_object

        print("[DEBUG] MaterialAssignmentAuto finished successfully")
        return {'FINISHED'}

    def assign_materials_to_all(self, mesh_objects, existing_textures):
        print(f"[INFO] Assigning materials to {len(mesh_objects)} mesh objects (fast mode)")
        for obj in mesh_objects:
            try:
                if obj.type != 'MESH':
                    continue

                print(f"[DEBUG] Processing: {obj.name}")
                self.update_material_assignment(obj, existing_textures)
                print(f"[DEBUG] Done: {obj.name}")

            except Exception as e:
                print(f"[ERROR] Exception while processing {obj.name}: {e}")

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

        model_name = clean_model_base_name(obj.name)
        print(f"[DEBUG] checking model_name={model_name}, obj['is_model']={obj.get('is_model', False)}")

        if obj.get("is_model", False):
            scene = bpy.context.scene
            for i in range(MAX_MODEL_SLOTS):
                slot_name = scene.get(f"m_model_name_{i}", "")
                tex_mode = scene.get(f"m_texture_mode_{i}", "")
                tex_path = scene.get(f"m_texture_path_{i}", "")
                print(f"[DEBUG] Slot {i}: m_model_name = '{slot_name}', mode = '{tex_mode}', path = '{tex_path}'")

                if clean_model_base_name(slot_name) == model_name:
                    if tex_mode == "LEVEL_TEXTURES":
                        return os.path.basename(tex_path.rstrip("/\\")).lower()
                    elif tex_mode == "TEXTURE_NAME":
                        return os.path.splitext(os.path.basename(tex_path))[0].lower()
                    else:
                        return model_name

        return self.get_base_name_for_layers(obj)

    def assign_tex_vc_materials(self, obj, existing_textures=None):
        """
        Auto-assign blended materials combining texture and vertex colour per face.

        This function mirrors assign_tex_vc_materials() but accepts an existing_textures
        cache from the auto operator.  It calls assign_uv_textures() with the cache,
        then creates blended materials per unique texture.
        """
        try:
            if existing_textures is not None:
                self.assign_uv_textures(obj, existing_textures)
            else:
                self.assign_uv_textures(obj)
        except Exception:
            # If assigning UV textures fails, leave existing materials unchanged
            return
        mesh = obj.data
        bm = bmesh.new()
        bm.from_mesh(mesh)
        blended_cache = {}
        for face in bm.faces:
            idx = face.material_index
            if idx < 0 or idx >= len(mesh.materials):
                continue
            orig_mat = mesh.materials[idx]
            base_name = orig_mat.name
            if base_name.lower().endswith('.bmp'):
                base_name = base_name[:-4]
            new_name = f"{base_name}_TexVC"
            new_mat = blended_cache.get(new_name)
            if not new_mat:
                new_mat = bpy.data.materials.get(new_name)
                if not new_mat:
                    new_mat = bpy.data.materials.new(name=new_name)
                    new_mat.use_nodes = True
                    nodes = new_mat.node_tree.nodes
                    links = new_mat.node_tree.links
                    for node in list(nodes):
                        nodes.remove(node)
                    tex_node = nodes.new('ShaderNodeTexImage')
                    tex_node.image = None
                    if getattr(orig_mat, 'use_nodes', False):
                        for node in orig_mat.node_tree.nodes:
                            if node.type == 'TEX_IMAGE' and getattr(node, 'image', None):
                                tex_node.image = node.image
                                break
                    col_attr = nodes.new('ShaderNodeAttribute')
                    col_attr.attribute_name = 'Col'
                    # Alpha attribute node; separate its X channel to use as a scalar
                    alpha_attr = nodes.new('ShaderNodeAttribute')
                    alpha_attr.attribute_name = 'Alpha'
                    separate = nodes.new('ShaderNodeSeparateXYZ')
                    # Math nodes to map alpha (0–1) to mix factor:
                    # alpha=0 → 0.01 (1%), alpha=1 → 0.20 (20%)
                    mult_node = nodes.new('ShaderNodeMath')
                    mult_node.operation = 'MULTIPLY'
                    mult_node.inputs[1].default_value = 0.19
                    add_node = nodes.new('ShaderNodeMath')
                    add_node.operation = 'ADD'
                    add_node.inputs[1].default_value = 0.01
                    mix = nodes.new('ShaderNodeMixRGB')
                    mix.blend_type = 'MIX'
                    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
                    output = nodes.new('ShaderNodeOutputMaterial')
                    links.new(tex_node.outputs['Color'], mix.inputs[1])
                    links.new(col_attr.outputs['Color'], mix.inputs[2])
                    # Connect alpha mapping: use the X (red) channel of the attribute
                    links.new(alpha_attr.outputs['Color'], separate.inputs['Vector'])
                    links.new(separate.outputs['X'], mult_node.inputs[0])
                    links.new(mult_node.outputs['Value'], add_node.inputs[0])
                    links.new(add_node.outputs['Value'], mix.inputs['Fac'])
                    links.new(mix.outputs['Color'], bsdf.inputs['Base Color'])
                    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
                blended_cache[new_name] = new_mat
            if new_mat.name not in mesh.materials:
                mesh.materials.append(new_mat)
            face.material_index = mesh.materials.find(new_mat.name)
        bm.to_mesh(mesh)
        bm.free()
        # Ensure vertex colour changes are committed and visible
        mesh.update()
        # Make one of the blended materials the active material
        for blended in blended_cache.values():
            if blended.name in mesh.materials:
                idx = mesh.materials.find(blended.name)
                if idx >= 0:
                    obj.active_material_index = idx
                    break

    def update_material_assignment(self, obj, existing_textures):
        material_map = {
            'UV_TEX': '_UVTex',
            'COL': '_Col',
            'TEX_VC': '_TexVC',
            'ALPHA': '_Alpha',
            'ENV': '_Env',
            'RGB': '_RGBModelColor',
            'NCP': '_NCP'
        }

        material_choice = obj.data.material_choice
        material_suffix = material_map.get(material_choice, '_Col')

        # ---- DEBUG START ----
        print(f"[DEBUG] update_material_assignment() called for {obj.name}")
        print(f"[DEBUG] material_choice = {material_choice}, resolved suffix = {material_suffix}")
        print(f"[DEBUG] Current materials: {[m.name for m in obj.data.materials]}")
        # ---- DEBUG END ----

        if material_choice == 'UV_TEX':
            print(f"[DEBUG] → Assigning UV textures for {obj.name}")
            self.assign_uv_textures(obj, existing_textures)

        elif material_choice == 'TEX_VC':
            print(f"[DEBUG] → Assigning Tex+VC materials for {obj.name}")
            # Some classes take existing_textures, others don’t; handle both
            try:
                self.assign_tex_vc_materials(obj, existing_textures)
            except TypeError:
                self.assign_tex_vc_materials(obj)

        elif material_choice == 'NCP':
            print(f"[DEBUG] → Assigning NCP materials for {obj.name}")
            self.assign_ncp_materials(obj)

        else:
            print(f"[DEBUG] → Assigning regular materials with suffix {material_suffix} for {obj.name}")
            self.assign_regular_materials(obj, material_suffix)

        # ---- DEBUG AFTER ASSIGNMENT ----
        print(f"[DEBUG] After assignment: {[m.name for m in obj.data.materials]}")
        print(f"[DEBUG] Active material index is {obj.active_material_index} ({obj.active_material.name if obj.active_material else 'None'})")

    def assign_uv_textures(self, obj, existing_textures):
        print(f"[FAST] assign_uv_textures: {obj.name}")

        bm = bmesh.new()
        bm.from_mesh(obj.data)

        texnum_layer = bm.faces.layers.int.get("Texture Number")
        if not texnum_layer:
            bm.free()
            print(f"[SKIP] No 'Texture Number' layer on {obj.name}")
            return

        scene = bpy.context.scene
        base_name = ""
        source_mode = ""

        matched = False
        model_slot_index = -1

        if obj.get("is_model", False):
            for i in range(MAX_MODEL_SLOTS):
                slot_model_name = scene.get(f"m_model_name_{i}", "")
                if not slot_model_name:
                    continue

                if clean_model_base_name(slot_model_name) in clean_model_base_name(obj.name):
                    source_mode = scene.get(f"m_texture_mode_{i}", "VERTEX_COLOR")
                    texture_path = scene.get(f"m_texture_path_{i}", "")
                    model_slot_index = i

                    if source_mode == "TEXTURE_NAME":
                        base_name = os.path.splitext(os.path.basename(texture_path))[0].lower()
                    elif source_mode == "LEVEL_TEXTURES":
                        base_name = os.path.basename(texture_path.rstrip("/\\")).lower()

                    matched = True
                    print(f"[DEBUG] Matched .m model slot {i} → name={slot_model_name}, base={base_name}")
                    break

        is_car_part = any(prefix in obj.name.lower() for prefix in self.car_parts_prefixes)
        if not matched and not is_car_part:
            if obj.get("is_instance") and "fin_texture_base" in obj:
                base_name = obj["fin_texture_base"]
            elif "level_texture_base" in scene:
                base_name = os.path.splitext(scene["level_texture_base"].strip().lower())[0]
            else:
                base_name = clean_model_base_name(obj.name)
            source_mode = "LEVEL_TEXTURES"

        if not matched and is_car_part:
            fallback_name = scene.get("selected_car_texture", "car.bmp")
            base_name = clean_model_base_name(fallback_name)
            source_mode = "TEXTURE_NAME"

        for face in bm.faces:
            tex_num = face[texnum_layer]

            if source_mode == 'TEXTURE_NAME':
                mat_name = f"{base_name}.bmp"
            elif source_mode == 'LEVEL_TEXTURES' and tex_num >= 0:
                mat_name = int_to_texture(tex_num, name=base_name)
            else:
                continue

            mat = self.find_material_loose(mat_name)
            if not mat:
                continue

            if mat.name not in obj.data.materials:
                obj.data.materials.append(mat)

            face.material_index = obj.data.materials.find(mat.name)

        bm.to_mesh(obj.data)
        bm.free()
        obj.data.update()

    def assign_ncp_materials(self, obj):
        print(f"[FAST] assign_ncp_materials: {obj.name}")

        bm = bmesh.new()
        bm.from_mesh(obj.data)

        material_layer = bm.faces.layers.int.get("Material")
        if not material_layer:
            print(f"[SKIP] No 'Material' layer on {obj.name}")
            bm.free()
            return

        for face in bm.faces:
            index = face[material_layer]
            if 0 <= index < len(MATERIALS):
                mat_name = MATERIALS[index][1]
                mat = self.find_material_loose(mat_name) or bpy.data.materials.new(name=mat_name)

                if mat.name not in obj.data.materials:
                    obj.data.materials.append(mat)

                face.material_index = obj.data.materials.find(mat.name)

        bm.to_mesh(obj.data)
        bm.free()
        obj.data.update()

    def assign_regular_materials(self, obj, material_suffix):
        print(f"[FAST] assign_regular_materials: {obj.name}")

        base_name = clean_model_base_name(obj.name)
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

        bm = bmesh.new()
        bm.from_mesh(obj.data)

        for face in bm.faces:
            face.material_index = index

        bm.to_mesh(obj.data)
        bm.free()
        obj.data.update()
            
    def find_material_loose(self, name):
        """Try to find a material with or without .bmp suffix."""
        if name in bpy.data.materials:
            return bpy.data.materials[name]
        elif name.endswith('.bmp') and name[:-4] in bpy.data.materials:
            return bpy.data.materials[name[:-4]]
        elif f"{name}.bmp" in bpy.data.materials:
            return bpy.data.materials[f"{name}.bmp"]
        return None

class MaterialAssignment(bpy.types.Operator):
    """Assign Materials to Selected Meshes Based on Material Choice"""
    bl_idname = "object.assign_materials"
    bl_label = "Assign Materials to Selected Meshes"
    bl_options = {'REGISTER', 'UNDO'}

    car_parts_prefixes = ["body", "wheel", "axle", "spring", "pin", "spinner"]

    def execute(self, context):
        scene = context.scene

        # Prompt for level_texture_base if not set
        if "level_texture_base" not in scene or not scene["level_texture_base"].strip():
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

        active_material_choice = obj.data.material_choice

        existing_textures = self.get_existing_textures()

        for obj in context.selected_objects:
            if obj.type == 'MESH' and hasattr(obj.data, 'material_choice'):
                obj.data.material_choice = active_material_choice
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

        model_name = clean_model_base_name(obj.name)

        if obj.get("is_model", False):
            scene = bpy.context.scene
            for i in range(MAX_MODEL_SLOTS):
                slot_name = scene.get(f"m_model_name_{i}", "")
                tex_mode = scene.get(f"m_texture_mode_{i}", "")
                tex_path = scene.get(f"m_texture_path_{i}", "")

                if clean_model_base_name(slot_name) == model_name:
                    if tex_mode == "LEVEL_TEXTURES":
                        return os.path.basename(tex_path.rstrip("/\\")).lower()
                    elif tex_mode == "TEXTURE_NAME":
                        return os.path.splitext(os.path.basename(tex_path))[0].lower()
                    else:
                        return model_name

        return self.get_base_name_for_layers(obj)

    def assign_tex_vc_materials(self, obj, existing_textures=None):
        """
        Create/assign *_TexVC materials that blend the face's texture with vertex colors.
        In multi-object Edit Mode, runs on selected faces of this object.
        """

        # Try to ensure the base UV texture assignment first; if that call signature
        # doesn't match in your build, the try/except keeps this operator usable.
        try:
            if existing_textures is not None:
                self.assign_uv_textures(obj, existing_textures)
            else:
                self.assign_uv_textures(obj)  # OK if it raises; we just continue
        except Exception:
            pass

        mesh = obj.data

        # Cache for blended materials created during this call
        blended_cache = {}

        def ensure_texvc_from(orig_mat):
            base_name = orig_mat.name
            if base_name.lower().endswith('.bmp'):
                base_name = base_name[:-4]
            new_name = f"{base_name}_TexVC"

            new_mat = blended_cache.get(new_name) or bpy.data.materials.get(new_name)
            if new_mat:
                blended_cache[new_name] = new_mat
                return new_mat

            # Build a fresh node tree
            new_mat = bpy.data.materials.new(name=new_name)
            new_mat.use_nodes = True
            nodes = new_mat.node_tree.nodes
            links = new_mat.node_tree.links
            for n in list(nodes):
                nodes.remove(n)

            tex_node = nodes.new('ShaderNodeTexImage')
            tex_node.image = None
            if getattr(orig_mat, 'use_nodes', False) and getattr(orig_mat, 'node_tree', None):
                for n in orig_mat.node_tree.nodes:
                    if n.type == 'TEX_IMAGE' and getattr(n, 'image', None):
                        tex_node.image = n.image
                        break

            # Vertex color attributes
            col_attr = nodes.new('ShaderNodeAttribute')
            col_attr.attribute_name = 'Col'

            alpha_attr = nodes.new('ShaderNodeAttribute')
            alpha_attr.attribute_name = 'Alpha'

            separate = nodes.new('ShaderNodeSeparateXYZ')

            mult_node = nodes.new('ShaderNodeMath')
            mult_node.operation = 'MULTIPLY'
            mult_node.inputs[1].default_value = 0.19  # scale alpha

            add_node = nodes.new('ShaderNodeMath')
            add_node.operation = 'ADD'
            add_node.inputs[1].default_value = 0.01   # base 1%

            mix = nodes.new('ShaderNodeMixRGB')
            mix.blend_type = 'MIX'

            bsdf = nodes.new('ShaderNodeBsdfPrincipled')
            output = nodes.new('ShaderNodeOutputMaterial')

            # Wire it up
            links.new(tex_node.outputs['Color'], mix.inputs[1])
            links.new(col_attr.outputs['Color'], mix.inputs[2])

            links.new(alpha_attr.outputs['Color'], separate.inputs['Vector'])
            links.new(separate.outputs['X'], mult_node.inputs[0])
            links.new(mult_node.outputs['Value'], add_node.inputs[0])
            links.new(add_node.outputs['Value'], mix.inputs['Fac'])

            links.new(mix.outputs['Color'], bsdf.inputs['Base Color'])
            links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

            blended_cache[new_name] = new_mat
            return new_mat

        # EDIT-MODE PATH (multi-object edit safe)
        if mesh.is_editmode:
            bm = bmesh.from_edit_mesh(mesh)
            for face in bm.faces:
                if not face.select:
                    continue
                idx = face.material_index
                if 0 <= idx < len(mesh.materials):
                    orig_mat = mesh.materials[idx]
                    if orig_mat is None:
                        continue
                    new_mat = ensure_texvc_from(orig_mat)
                    if new_mat.name not in mesh.materials:
                        mesh.materials.append(new_mat)
                    face.material_index = mesh.materials.find(new_mat.name)
            bmesh.update_edit_mesh(mesh, loop_triangles=False, destructive=False)
            mesh.update()

        else:
            # OBJECT-MODE PATH (applies to all faces on this object)
            bm = bmesh.new()
            bm.from_mesh(mesh)
            for face in bm.faces:
                idx = face.material_index
                if 0 <= idx < len(mesh.materials):
                    orig_mat = mesh.materials[idx]
                    if orig_mat is None:
                        continue
                    new_mat = ensure_texvc_from(orig_mat)
                    if new_mat.name not in mesh.materials:
                        mesh.materials.append(new_mat)
                    face.material_index = mesh.materials.find(new_mat.name)
            bm.to_mesh(mesh)
            bm.free()
            mesh.update()

        # Set any of the blended materials as active (purely UX)
        for blended in blended_cache.values():
            idx = mesh.materials.find(blended.name)
            if idx >= 0:
                obj.active_material_index = idx
                break

    def update_material_assignment(self, obj, existing_textures):
        material_map = {
            'UV_TEX': '_UVTex',
            'COL': '_Col',
            'TEX_VC': '_TexVC',
            'ALPHA': '_Alpha',
            'ENV': '_Env',
            'RGB': '_RGBModelColor',
            'NCP': '_NCP'
        }

        material_choice = obj.data.material_choice
        material_suffix = material_map.get(material_choice, '_Col')

        # ---- DEBUG START ----
        print(f"[DEBUG] update_material_assignment() called for {obj.name}")
        print(f"[DEBUG] material_choice = {material_choice}, resolved suffix = {material_suffix}")
        print(f"[DEBUG] Current materials: {[m.name for m in obj.data.materials]}")
        # ---- DEBUG END ----

        if material_choice == 'UV_TEX':
            print(f"[DEBUG] → Assigning UV textures for {obj.name}")
            self.assign_uv_textures(obj, existing_textures)

        elif material_choice == 'TEX_VC':
            print(f"[DEBUG] → Assigning Tex+VC materials for {obj.name}")
            # Some classes take existing_textures, others don’t; handle both
            try:
                self.assign_tex_vc_materials(obj, existing_textures)
            except TypeError:
                self.assign_tex_vc_materials(obj)

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
                slot_model_name = scene.get(f"m_model_name_{i}", "")
                if not slot_model_name:
                    continue

                if clean_model_base_name(slot_model_name) in clean_model_base_name(obj.name):
                    source_mode = scene.get(f"m_texture_mode_{i}", "VERTEX_COLOR")
                    texture_path = scene.get(f"m_texture_path_{i}", "")
                    model_slot_index = i

                    if source_mode == "TEXTURE_NAME":
                        base_name_for_texture = os.path.splitext(os.path.basename(texture_path))[0].lower()
                    elif source_mode == "LEVEL_TEXTURES":
                        base_name_for_texture = os.path.basename(texture_path.rstrip("/\\")).lower()

                    matched = True
                    break

        is_car_part = any(prefix in obj.name.lower() for prefix in self.car_parts_prefixes)
        if not matched and not is_car_part:
            if obj.get("is_instance") and "fin_texture_base" in obj:
                base_name_for_texture = obj["fin_texture_base"]
            elif "level_texture_base" in scene:
                base_name_for_texture = os.path.splitext(scene["level_texture_base"].strip().lower())[0]
            else:
                base_name_for_texture = clean_model_base_name(obj.name)
            source_mode = "LEVEL_TEXTURES"

        if not matched and is_car_part:
            fallback_name = scene.get("selected_car_texture", "car.bmp")
            base_name_for_texture = clean_model_base_name(fallback_name)
            source_mode = "TEXTURE_NAME"

        for face in bm.faces:
            if not face.select:
                continue

            tex_num = face[texnum_layer]
            if source_mode == 'TEXTURE_NAME':
                material_name = f"{base_name_for_texture}.bmp"
            elif source_mode == 'LEVEL_TEXTURES':
                if tex_num == -1:
                    continue
                material_name = int_to_texture(tex_num, name=base_name_for_texture)
            else:
                continue

            mat = self.find_material_loose(material_name)

            # Try to infer from the current slot if missing
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
                fallback_name = scene.get("selected_car_texture", "car.bmp")
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
        base_name = clean_model_base_name(obj.name)

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

    def execute(self, context):
        if bpy.context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        mesh_objects = [obj for obj in bpy.data.objects if obj.type == 'MESH']

        original_active_object = context.view_layer.objects.active
        if not (original_active_object and original_active_object.type == 'MESH'):
            self.report({'WARNING'}, "No active mesh object with material choice found.")
            return {'CANCELLED'}

        active_material_choice = original_active_object.data.material_choice

        existing_textures = self.get_existing_textures()

        for obj in mesh_objects:
            obj.data.material_choice = active_material_choice

        self.assign_materials_to_all(mesh_objects, existing_textures)

        bpy.ops.object.select_all(action='DESELECT')
        for obj in mesh_objects:
            obj.select_set(True)
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

        model_name = clean_model_base_name(obj.name)
        print(f"[DEBUG] checking model_name={model_name}, obj['is_model']={obj.get('is_model', False)}")

        if obj.get("is_model", False):
            scene = bpy.context.scene
            for i in range(MAX_MODEL_SLOTS):
                slot_name = scene.get(f"m_model_name_{i}", "")
                tex_mode = scene.get(f"m_texture_mode_{i}", "")
                tex_path = scene.get(f"m_texture_path_{i}", "")
                print(f"[DEBUG] Slot {i}: m_model_name = '{slot_name}', mode = '{tex_mode}', path = '{tex_path}'")

                if clean_model_base_name(slot_name) == model_name:
                    if tex_mode == "LEVEL_TEXTURES":
                        return os.path.basename(tex_path.rstrip("/\\")).lower()
                    elif tex_mode == "TEXTURE_NAME":
                        return os.path.splitext(os.path.basename(tex_path))[0].lower()
                    else:
                        return model_name

        return self.get_base_name_for_layers(obj)

    def assign_materials_to_all(self, mesh_objects, existing_textures):
        bpy.ops.object.select_all(action='DESELECT')

        for obj in mesh_objects:
            obj.select_set(True)

        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')

        for obj in mesh_objects:
            self.update_material_assignment(obj, existing_textures)

        bpy.ops.object.mode_set(mode='OBJECT')

    def update_material_assignment(self, obj, existing_textures):
        material_map = {
            'UV_TEX': '_UVTex',
            'COL': '_Col',
            'ALPHA': '_Alpha',
            'ENV': '_Env',
            'RGB': '_RGBModelColor',
            'NCP': '_NCP'
        }

        material_choice = obj.data.material_choice
        material_suffix = material_map.get(material_choice, '_Col')

        if material_choice == 'UV_TEX':
            self.assign_uv_textures(obj, existing_textures)
        elif material_choice == 'NCP':
            self.assign_ncp_materials(obj)
        else:
            self.assign_regular_materials(obj, material_suffix)

    def assign_uv_textures(self, obj, existing_textures):
        if not (bpy.context.view_layer.objects.active == obj and obj.mode == 'EDIT'):
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
                slot_model_name = scene.get(f"m_model_name_{i}", "")
                if not slot_model_name:
                    continue

                if clean_model_base_name(slot_model_name) in clean_model_base_name(obj.name):
                    source_mode = scene.get(f"m_texture_mode_{i}", "VERTEX_COLOR")
                    texture_path = scene.get(f"m_texture_path_{i}", "")
                    model_slot_index = i

                    if source_mode == "TEXTURE_NAME":
                        base_name_for_texture = os.path.splitext(os.path.basename(texture_path))[0].lower()
                    elif source_mode == "LEVEL_TEXTURES":
                        base_name_for_texture = os.path.basename(texture_path.rstrip("/\\")).lower()

                    matched = True
                    print(f"[DEBUG] Matched .m model slot {i} → name={slot_model_name}, base={base_name_for_texture}")
                    break

        is_car_part = any(prefix in obj.name.lower() for prefix in self.car_parts_prefixes)
        if not matched and not is_car_part:
            if obj.get("is_instance") and "fin_texture_base" in obj:
                base_name_for_texture = obj["fin_texture_base"]
            elif "level_texture_base" in scene:
                base_name_for_texture = os.path.splitext(scene["level_texture_base"].strip().lower())[0]
            else:
                base_name_for_texture = clean_model_base_name(obj.name)
            source_mode = "LEVEL_TEXTURES"

        if not matched and is_car_part:
            fallback_name = scene.get("selected_car_texture", "car.bmp")
            base_name_for_texture = clean_model_base_name(fallback_name)
            source_mode = "TEXTURE_NAME"

        for face in bm.faces:
            if face.select:
                tex_num = face[texnum_layer]

                if source_mode == 'TEXTURE_NAME':
                    material_name = f"{base_name_for_texture}.bmp"
                elif source_mode == 'LEVEL_TEXTURES':
                    if tex_num == -1:
                        continue
                    material_name = int_to_texture(tex_num, name=base_name_for_texture)
                else:
                    continue

                mat = self.find_material_loose(material_name)

                if not mat:
                    slot_index = face.material_index
                    if slot_index < len(obj.data.materials):
                        candidate = obj.data.materials[slot_index].name
                        mat = bpy.data.materials.get(candidate)
                        if not mat and not candidate.endswith('.bmp'):
                            mat = bpy.data.materials.get(f"{candidate}.bmp")
                        elif not mat and candidate.endswith('.bmp'):
                            mat = bpy.data.materials.get(candidate[:-4])

                if not mat and is_car_part:
                    fallback_name = scene.get("selected_car_texture", "car.bmp")
                    mat = bpy.data.materials.get(fallback_name)
                    if mat:
                        print(f"[INFO] Fallback texture '{fallback_name}' used for {obj.name}")

                if not mat:
                    continue

                if mat.name not in obj.data.materials:
                    obj.data.materials.append(mat)

                face.material_index = obj.data.materials.find(mat.name)

        bmesh.update_edit_mesh(obj.data)
        obj.data.update()

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
        base_name = clean_model_base_name(obj.name)

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

class SetFaceTextureNumber(bpy.types.Operator):
    bl_idname = "mesh.set_face_texnum"
    bl_label = "Fix Texture Numbers and Materials"
    bl_description = "Sets the texture number based on image suffix and optionally renames materials to .bmp"

    texture_base: bpy.props.StringProperty(
        name="Texture Base",
        description="Prefix for textures (e.g. 'box')",
        default=""
    )

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        base = self.texture_base.lower()
        renamed = 0

        def suffix_to_texnum(name, base):
            """Extract tex_num from name, allowing a-z and aa–lb (0–63)."""
            if not name.lower().startswith(base):
                return -1
            suffix = name[len(base):].lower().removesuffix(".bmp")
            if not suffix.isalpha() or len(suffix) > 2:
                return -1
            if len(suffix) == 1:
                index = ord(suffix) - ord('a')
            else:
                major = ord(suffix[0]) - ord('a') + 1
                minor = ord(suffix[1]) - ord('a')
                index = major * 26 + minor
            return index if 0 <= index <= 63 else -1

        for obj in context.scene.objects:
            if obj.type != 'MESH':
                continue

            bm = bmesh.from_edit_mesh(obj.data) if obj.mode == 'EDIT' else bmesh.new()
            if obj.mode != 'EDIT':
                bm.from_mesh(obj.data)

            texnum_layer = bm.faces.layers.int.get("Texture Number") or bm.faces.layers.int.new("Texture Number")
            for face in bm.faces:
                mat_index = face.material_index
                if mat_index >= len(obj.material_slots):
                    continue
                mat = obj.material_slots[mat_index].material
                if not mat or not mat.use_nodes:
                    continue

                image = next((n.image for n in mat.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image), None)
                if not image:
                    continue

                tex_num = suffix_to_texnum(image.name, base)
                face[texnum_layer] = tex_num

                # Rename material to match new base + suffix
                image_name_normalized = image.name.lower().removesuffix(".bmp")
                suffix = image_name_normalized[len(base):]
                correct_name = f"{base}{suffix}.bmp"
                if mat.name != correct_name:
                    mat.name = correct_name
                    renamed += 1

            if obj.mode != 'EDIT':
                bm.to_mesh(obj.data)
                bm.free()
            else:
                bmesh.update_edit_mesh(obj.data)

        self.report({'INFO'}, f"Renamed {renamed} materials to match BMP naming.")
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
        guessed_base = scene.get("level_texture_base", "")
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
            context.scene["level_texture_base"] = "car"
            self.report({'INFO'}, "Set level texture base to: car")
        else:
            context.scene["level_texture_base"] = self.texture_base.strip().lower()
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
                if clean_model_base_name(scene.get(f"m_model_name_{i}", "").lower()) == base_name:
                    scene[f"m_model_name_{i}"] = ""
                    scene[f"m_texture_mode_{i}"] = ""
                    scene[f"m_texture_path_{i}"] = ""
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
            if not scene.get(f"m_model_name_{i}", ""):
                scene[f"m_model_name_{i}"] = base_name
                scene[f"m_texture_mode_{i}"] = self.texture_source
                scene[f"m_texture_path_{i}"] = texture_path
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

    def batch_bake(self, context):
        scene = context.scene

        # Set render engine to Cycles and configure settings
        original_engine = scene.render.engine
        scene.render.engine = 'CYCLES'
        original_samples = scene.cycles.samples
        scene.cycles.samples = self.samples

        # Bakes all selected objects
        for obj in context.selected_objects:
            # Skips unsupported objects
            if not hasattr(obj.data, "vertex_colors") or not obj.get('is_instance'):
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
            bpy.ops.object.bake(type='AO', use_clear=True, use_selected_to_active=False, margin=2, cage_extrusion=0.0, normal_space='TANGENT', target='VERTEX_COLORS')

            # Switch to the temporary direct lighting vertex color layer
            obj.data.vertex_colors.active = temp_direct_env_layer

            # Bake the direct lighting to the temporary vertex color layer
            bpy.ops.object.bake(type='DIFFUSE', use_clear=True, use_selected_to_active=False, margin=2, cage_extrusion=0.0, normal_space='TANGENT', pass_filter={'DIRECT'}, target='VERTEX_COLORS')

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
                    # Blend the original color with the AO shadow and direct lighting
                    blended_color = [
                        original_color[j] * (1 - self.shadow_strength * (1 - ao_color[j])) + self.light_strength * direct_color[j]
                        for j in range(3)
                    ]
                    loop[env_layer_bm] = blended_color + [original_color[3]]  # Preserve original alpha value

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
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

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

    def batch_bake(self, context):
        scene = context.scene

        # Set render engine to Cycles and configure settings
        original_engine = scene.render.engine
        scene.render.engine = 'CYCLES'
        original_samples = scene.cycles.samples
        scene.cycles.samples = self.samples

        # Bakes all selected objects
        for obj in context.selected_objects:
            # Skips unsupported objects
            if not hasattr(obj.data, "vertex_colors") or not obj.get('is_instance'):
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
            bpy.ops.object.bake(type='AO', use_clear=True, use_selected_to_active=False, margin=2, cage_extrusion=0.0, normal_space='TANGENT', target='VERTEX_COLORS')

            # Switch to the temporary direct lighting vertex color layer
            obj.data.vertex_colors.active = temp_direct_rgb_layer

            # Bake the direct lighting to the temporary vertex color layer
            bpy.ops.object.bake(type='DIFFUSE', use_clear=True, use_selected_to_active=False, margin=2, cage_extrusion=0.0, normal_space='TANGENT', pass_filter={'DIRECT'}, target='VERTEX_COLORS')

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
                    # Blend the original color with the AO shadow and direct lighting
                    blended_color = [
                        original_color[j] * (1 - self.shadow_strength * (1 - ao_color[j])) + self.light_strength * direct_color[j]
                        for j in range(3)
                    ]
                    loop[rgb_layer_bm] = blended_color + [1.0]  # Add alpha value for RGBModelColor

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
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

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

        if frame_start >= max_frames or frame_end >= max_frames:
            msg_box("Frame index out of range.", "ERROR")
            return {'FINISHED'}

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

        nframes = abs(frame_end - frame_start) + 1

        for i in range(0, nframes):
            current_frame = frame_start + i
            prog = i / (frame_end - frame_start)

            ta[slot]["frames"][frame_start + i]["delay"] = scene.ta_delay
            ta[slot]["frames"][frame_start + i]["texture"] = scene.ta_texture

            for j in range(0, 4):
                new_u = uv_start[j][0] * (1 - prog) + uv_end[j][0] * prog
                new_v = uv_start[j][1] * (1 - prog) + uv_end[j][1] * prog

                ta[slot]["frames"][frame_start + i]["uv"][j]["u"] = new_u
                ta[slot]["frames"][frame_start + i]["uv"][j]["v"] = new_v

        scene.texture_animations = str(ta)
        update_ta_current_frame(self, context)

        msg_box("Animation from frame {} to {} completed.".format(
            frame_start, frame_end),
            icon = "FILE_TICK"
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
        max_frames = scene.ta_max_frames

        frame_start = scene.ta_frame_start
        grid_x = scene.grid_x
        grid_y = scene.grid_y
        nframes = grid_x * grid_y

        if nframes > max_frames:
            msg_box(
                "Frame out of range.\n"
                "Please set the amount of frames to {}.".format(
                    nframes + 1),
                "ERROR"
            )
            return {'FINISHED'}

        i = 0
        for y in range(grid_x):
            for x in range(grid_y):
                uv0 = (x/grid_x, y/grid_y)
                uv1 = ((x+1)/grid_x, y/grid_y)
                uv2 = ((x+1)/grid_x, (y+1)/grid_y)
                uv3 = (x/grid_x, (y+1)/grid_y)

                ta[slot]["frames"][frame_start + i]["delay"] = scene.ta_delay
                ta[slot]["frames"][frame_start + i]["texture"] = scene.ta_texture

                ta[slot]["frames"][frame_start + i]["uv"][0]["u"] = uv0[0]
                ta[slot]["frames"][frame_start + i]["uv"][0]["v"] = uv0[1]
                ta[slot]["frames"][frame_start + i]["uv"][1]["u"] = uv1[0]
                ta[slot]["frames"][frame_start + i]["uv"][1]["v"] = uv1[1]
                ta[slot]["frames"][frame_start + i]["uv"][2]["u"] = uv2[0]
                ta[slot]["frames"][frame_start + i]["uv"][2]["v"] = uv2[1]
                ta[slot]["frames"][frame_start + i]["uv"][3]["u"] = uv3[0]
                ta[slot]["frames"][frame_start + i]["uv"][3]["v"] = uv3[1]

                i += 1

        scene.texture_animations = str(ta)
        update_ta_current_frame(self, context)

        msg_box("Animation of {} frames completed.".format(
            nframes),
            icon = "FILE_TICK"
        )
        
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
        alpha_percent = int(scene.vertex_alpha_percentage)
        alpha_value = alpha_percent / 100.0
        scene.vertex_alpha = alpha_value

        # Create two temporary lights
        def create_temp_light(name, location):
            light_data = bpy.data.lights.new(name=name, type='POINT')
            light_data.energy = 3500.0  # or higher if needed
            light_obj = bpy.data.objects.new(name, light_data)
            light_obj.location = location
            bpy.context.collection.objects.link(light_obj)
            return light_obj

        temp_lights = [
            create_temp_light("TempLight1", (4, 1.5, 7)),
            create_temp_light("TempLight2", (-4, -1.5, 7))
        ]

        for obj in context.selected_objects:
            if obj.type != 'MESH' or not obj.visible_get():
                continue

            original_mode = obj.mode
            bpy.context.view_layer.objects.active = obj
            bpy.ops.mesh.vertex_color_and_alpha_setup()

            bm = bmesh.from_edit_mesh(obj.data)
            col_layer = bm.loops.layers.color.get("Col")
            alpha_layer = bm.loops.layers.color.get("Alpha")

            if not col_layer or not alpha_layer:
                self.report({'ERROR'}, f"Missing Col or Alpha layer on {obj.name}")
                continue

            for face in bm.faces:
                for loop in face.loops:
                    world_pos = obj.matrix_world @ loop.vert.co
                    normal = (obj.matrix_world.to_3x3() @ loop.vert.normal).normalized()
                    light_val = 0.0

                    for light in temp_lights:
                        to_light = (light.location - world_pos).normalized()
                        brightness = max(0.0, normal.dot(to_light))
                        light_val += brightness * light.data.energy

                    light_val = light_val / (len(temp_lights) * 1000.0)
                    light_val = max(0.1, min(light_val, 1.0))

                    loop[col_layer] = (
                        base_color[0] * light_val,
                        base_color[1] * light_val,
                        base_color[2] * light_val,
                        1.0
                    )
                    loop[alpha_layer] = (0.0, 0.0, 0.0, 1.0)  # Set alpha black

            bmesh.update_edit_mesh(obj.data, destructive=False)
            obj.data.update()
            bpy.ops.object.assign_materials()

        for light in temp_lights:
            try:
                bpy.data.objects.remove(light, do_unlink=True)
            except Exception:
                pass

        self.report({'INFO'}, "Vertex colors and alpha baked based on lighting.")
        return {'FINISHED'}

def menu_func_import(self, context):
    self.layout.operator(
        ImportRV.bl_idname,
        text="Re-Volt (.fin, .fob, .hul, .lit, .ncp, .parameters.txt, .prm, .rim, .taz, .fan, .pan, .tri, .vis, .w, .m)"
    )

def menu_func_export(self, context):
    self.layout.operator(
        ExportExtension.bl_idname,
        text="Re-Volt (.fin, .fob, .hul, .lit, .ncp, .prm, .rim, .taz, .fan, .pan, .tri, .vis, .w, .m)"
    )