"""
Name:    operators
Purpose: Provides operators for importing and exporting and other buttons.

Description:
These operators are used for importing and exporting files, as well as
providing the functions behind the UI buttons.

"""


import os
import bpy
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
from .common import get_format, FORMAT_PRM, FORMAT_FIN, FORMAT_NCP, FORMAT_HUL, FORMAT_W, FORMAT_M, FORMAT_RIM, FORMAT_TA_CSV
from .common import FORMAT_TAZ, FORMAT_TRI, FORMAT_UNK, MATERIALS, COLORS
from .common import get_errors, msg_box, FORMATS, to_revolt_scale, FORMAT_CAR, TEX_PAGES_MAX, int_to_texture, to_revolt_coord
from .layers import set_face_env, create_or_assign_env_material
from .parameters_out import append_aerial_info, append_axle_info, append_back_left_wheel, append_back_right_wheel
from .parameters_out import append_front_left_wheel, append_front_right_wheel, append_pin_info, append_spring_info
from .parameters_out import compare_and_adjust_axle_lengths, remove_imported_axles, compare_and_adjust_spring_lengths
from .parameters_out import remove_imported_springs, compare_and_adjust_pin_lengths, remove_imported_pins
from .taz_in import create_zone
from .texanim import copy_frame_to_uv, copy_uv_to_frame
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
        'PRM': '.prm',
        'FIN': '.fin',
        'NCP': '.ncp',
        'HUL': '.hul',
        'W': '.w',
        'M': '.m',
        'RIM': '.rim',
        'TAZ': '.taz',
        'TRI': '.tri'
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
    """ Import Operator for all file types """
    bl_idname = "import_scene.revolt"
    bl_label = "Import Re-Volt Files"
    bl_description = "Import Re-Volt game files"
    filepath: bpy.props.StringProperty(subtype="FILE_PATH")

    def execute(self, context):
        scene = context.scene
        frmt = get_format(self.filepath)

        start_time = time.time()
        context.window.cursor_set("WAIT")

        print("Importing {}".format(self.filepath))

        try:
            #Handle different formats
            if frmt == FORMAT_UNK:
                self.report({'ERROR'}, "Unsupported format.")
                return {'CANCELLED'}

            elif frmt == FORMAT_PRM:
                from . import prm_in
                prm_in.import_file(self.filepath, context.scene)

            elif frmt == FORMAT_CAR:
                from . import parameters_in
                parameters_in.import_file(self.filepath, context.scene)

            elif frmt == FORMAT_NCP:
                from . import ncp_in
                ncp_in.import_file(self.filepath, scene)

            elif frmt == FORMAT_FIN:
                from . import fin_in
                fin_in.import_file(self.filepath, scene)

            elif frmt == FORMAT_HUL:
                from . import hul_in
                hul_in.import_file(self.filepath, scene)

            elif frmt == FORMAT_TA_CSV:
                from . import ta_csv_in
                ta_csv_in.import_file(self.filepath, scene)

            elif frmt == FORMAT_W:
                from . import w_in
                w_in.import_file(self.filepath, context.scene)
                
            elif frmt == FORMAT_M:
                from . import m_in
                m_in.import_file(self.filepath, context.scene)

            elif frmt == FORMAT_RIM:
                from . import rim_in
                rim_in.import_file(self.filepath, scene)
        
            elif frmt == FORMAT_TAZ:
                from . import taz_in
                taz_in.import_file(self.filepath, scene)
                
            elif frmt == FORMAT_TRI:
                from . import tri_in
                tri_in.import_file(self.filepath, scene)
        
            else:
                self.report({'ERROR'}, "Format not yet supported: {}".format(FORMATS.get(frmt, "Unknown Format")))
                return {'CANCELLED'}

            # Use the following line if your import functions might change visible aspects of the UI
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
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

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
            ('PRM', "PRM (.prm)", "Export as PRM file"),
            ('FIN', "FIN (.fin)", "Export as FIN file"),
            ('NCP', "NCP (.ncp)", "Export as NCP file"),
            ('HUL', "HUL (.hul)", "Export as HUL file"),
            ('W', "W (.w)", "Export as W file"),
            ('M', "M (.m)", "Export as M file"),
            ('RIM', "RIM (.rim)", "Export as RIM file"),
            ('TAZ', "TAZ (.taz)", "Export as TAZ file"),
            ('TRI', "TRI (.tri)", "Export as TRI file"),
        ],
        update=None  # Removing the update function
    )

    def execute(self, context):
        # Debugging: Print the filepath and format type
        print(f"Exporting to filepath: {self.filepath}")
        print(f"Exporting format type: {self.format_type}")

        # Ensure filepath is set
        if not self.filepath:
            print("Error: Filepath is not set.")
            return {'CANCELLED'}

        # Saves filepath for re-exporting the same file
        context.scene.last_exported_filepath = self.filepath
        context.scene.last_exported_format = self.format_type

        result = exec_export(self.filepath, self.format_type, context)
        return result

    def invoke(self, context, event):
        # Open the file browser to select the export path
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

class SelectDefaultTexture(bpy.types.Operator):
    bl_idname = "wm.select_default_texture"
    bl_label = "Select Default Texture"
    bl_description = "Select the default texture for the exported object from the available textures in the scene"

    texture_name: bpy.props.EnumProperty(
        name="Texture",
        description="Select the default texture",
        items=lambda self, context: [
            (img.name, img.name, "") for img in bpy.data.images
            if img.name not in ["Render Result", "Viewer Node"]
        ],
    )

    def execute(self, context):
        # Store the selected texture name in the scene for later use
        context.scene.default_texture_name = self.texture_name

        # Debugging: Print the last exported format
        print(f"Last exported format before execution: {context.scene.last_exported_format}")

        # Ensure last_exported_format is set to a valid value
        if not context.scene.last_exported_format:
            context.scene.last_exported_format = 'PRM'  # Default to PRM or any valid format

        # Continue with the export process by invoking the ExportRV operator
        bpy.ops.export_scene.revolt('INVOKE_DEFAULT')
        return {'FINISHED'}

    def invoke(self, context, event):
        # Check if a single object is selected for export
        if len(context.selected_objects) == 1:
            obj = context.selected_objects[0]
            car_part_prefixes = ["body", "wheel", "axle", "spring", "pin", "spinner"]
            if any(obj.name.startswith(prefix) for prefix in car_part_prefixes):
                # Check if 'car' or 'car.bmp' texture is present
                car_texture = bpy.data.images.get('car')
                car_bmp_texture = bpy.data.images.get('car.bmp')
                if not car_texture and not car_bmp_texture:
                    # Open a dialog to select from available textures in the scene
                    return context.window_manager.invoke_props_dialog(self)
                else:
                    # If texture is present, directly invoke the export operator
                    return bpy.ops.export_scene.revolt('INVOKE_DEFAULT')

        # If not a car part, directly invoke the export operator
        return bpy.ops.export_scene.revolt('INVOKE_DEFAULT')

    def draw(self, context):
        layout = self.layout
        layout.label(text="Default Texture:")
        layout.prop(self, "texture_name")

def exec_export(filepath, format_type, context):
    start_time = time.time()
    bpy.context.window.cursor_set("WAIT")

    # Extensions mapping from dropdown
    format_map = {
        'PRM': '.prm',
        'FIN': '.fin',
        'NCP': '.ncp',
        'HUL': '.hul',
        'W': '.w',
        'M': '.m',
        'RIM': '.rim',
        'TAZ': '.taz',
        'TRI': '.tri'
    }

    # Extract the extension from the filename
    _, file_ext = os.path.splitext(filepath)

    # Check if the user provided a valid extension
    if file_ext in format_map.values():
        # Use the user-provided extension
        frmt = next(k for k, v in format_map.items() if v == file_ext)
    else:
        # Fallback to the dropdown and ensure the filepath has the correct extension
        file_ext = format_map.get(format_type, "")
        if not filepath.lower().endswith(file_ext):
            filepath += file_ext
        frmt = format_type

    if not frmt:
        print({'ERROR'}, "Unsupported format.")
        return {'CANCELLED'}

    # Import specific format modules and handle export based on the determined format
    if frmt == 'PRM':
        from . import prm_out
        prm_out.export_file(filepath, context.scene)

    elif frmt == 'FIN':
        from . import fin_out
        fin_out.export_file(filepath, context.scene)

    elif frmt == 'NCP':
        from . import ncp_out
        ncp_out.export_file(filepath, context.scene)

    elif frmt == 'HUL':
        from . import hul_out
        hul_out.export_file(filepath, context.scene)

    elif frmt == 'W':
        from . import w_out
        w_out.export_file(filepath, context.scene)

    elif frmt == 'M':
        from . import m_out
        m_out.export_file(filepath, context.scene)

    elif frmt == 'RIM':
        from . import rim_out
        rim_out.export_file(filepath, context.scene)

    elif frmt == 'TAZ':
        from . import taz_out
        taz_out.export_file(filepath, context.scene)

    elif frmt == 'TRI':
        from . import tri_out
        tri_out.export_file(filepath, context.scene)

    # Re-enable undo and cleanup
    bpy.context.preferences.edit.use_global_undo = True
    bpy.context.window.cursor_set("DEFAULT")

    end_time = time.time() - start_time
    print("Export to {} done in {:.3f} seconds.".format(filepath, end_time))

    return {'FINISHED'}
    
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

class TexturesSave(bpy.types.Operator):
    bl_idname = "helpers.textures_save"
    bl_label = "Save Textures to RVGL Directory"
    bl_description = "Saves all used track texture files to the RVGL directory"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.scene.rvgl_dir != ""

    def execute(self, context):
        directory_path = context.scene.rvgl_dir

        if not directory_path or not os.path.isdir(directory_path):
            self.report({'ERROR'}, "Invalid or no RVGL directory path set.")
            return {'CANCELLED'}

        for image in bpy.data.images:
            # Work only with image files
            if image.source == 'FILE' and image.file_format in ['BMP', 'PNG', 'JPEG', 'TIFF', 'TGA']:  # Extendable for any format
                base, ext = os.path.splitext(image.name)
                base = base[:8]  # Truncate to 8 characters
                suffix = 'a'  # Placeholder for your suffix logic
                new_filename = f"{base}{suffix}.bmp"  # Force the .bmp extension
                dst = os.path.join(directory_path, new_filename)
            
                # Save the file as BMP
                try:
                    original_path = image.filepath_from_user()
                    image.filepath_raw = dst
                    image.file_format = 'BMP'
                    image.save()
                    image.filepath_raw = original_path  # Restore the original path
                    image.reload()  # Reload to undo changes made to the image in Blender
                except Exception as e:
                    self.report({'ERROR'}, f"Failed to save image {image.name} as BMP: {str(e)}")
                    continue

        self.report({'INFO'}, "Textures saved to RVGL directory in BMP format.")
        return {'FINISHED'}

    def invoke(self, context, event):
        if not context.scene.rvgl_dir:
            self.report({'WARNING'}, "No RVGL directory selected. Please specify the directory first.")
            return {'CANCELLED'}
        return context.window_manager.invoke_confirm(self, event)

class TexturesRename(bpy.types.Operator):
    bl_idname = "helpers.texture_rename"
    bl_label = "Rename Texture"
    bl_description = "Rename selected object's texture(s) based on their order in the blend file"

    base_name: bpy.props.StringProperty(
        name="Base Name",
        description="Base name for the textures",
        maxlen=64  # Adequate length for most use cases
    )

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def execute(self, context):
        if not self.base_name:
            self.report({'WARNING'}, "No base name provided")
            return {'CANCELLED'}

        # Fetch all textures in the blend file, sorted by their name to maintain a consistent order
        textures = [img for img in bpy.data.images if img.source == 'FILE' and img.users > 0 and 'Viewer Node' not in img.name and 'Render Result' not in img.name]
        textures.sort(key=lambda x: x.name)  # Sort by name
        
        if not textures:
            self.report({'WARNING'}, "No applicable textures found")
            return {'CANCELLED'}

        # Rename textures with a sequential letter suffix starting from 'a'
        for i, texture in enumerate(textures):
            suffix = chr(97 + i % 26)  # ASCII 'a' + index, wraps every 26
            prefix = '' if i < 26 else chr(96 + i // 26)
            new_name = f"{self.base_name}{prefix}{suffix}"
            print(f"Renaming {texture.name} to {new_name}")  # Debug print
            texture.name = new_name

        self.report({'INFO'}, f"Renamed {len(textures)} textures starting with base name '{self.base_name}'")
        return {'FINISHED'}
    
class CopyWheelParams(bpy.types.Operator):
    bl_idname = "headers.copy_wheel_params"
    bl_label = "Copy Wheel Parameters"
    bl_description = "Copies wheel parameters into clipboard"

    def execute(self, context):
        body = bpy.data.objects.get("body")
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
        processed = set()

        params = ""
        params = append_aerial_info(params, body, processed)

        bpy.context.window_manager.clipboard = params
        self.report({'INFO'}, "Aerial parameters copied to clipboard.")
        return {"FINISHED"}
    
"""
INSTANCES -----------------------------------------------------------------------
"""

class SetInstanceProperty(bpy.types.Operator):
    bl_idname = "instances.set_instance_property"
    bl_label = "Mark as Instance"
    bl_description = "Marks all selected objects as instances"

    def execute(self, context):
        # Check if any selected object is not in Object Mode
        for obj in context.selected_objects:
            if obj.type == 'MESH':
                if obj.mode != 'OBJECT':
                    self.report({'WARNING'}, "You must be in Object Mode to run this operator.")
                    return {'CANCELLED'}  # Exit if not in Object Mode
                
                # Set 'is_instance' and 'fin_env' as custom properties
                obj["is_instance"] = True
                obj["fin_env"] = True  # Set the default for EnvMap to True

                # Create and assign the _Env material
                create_or_assign_env_material(obj)

                # Print debug information
                print(f"Marked {obj.name} as instance with fin_env set to {obj['fin_env']}")

        context.view_layer.update()
        self.report({'INFO'}, f"Marked {len(context.selected_objects)} objects as is_instance")
        return {'FINISHED'}


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

        context.view_layer.update()
        self.report({'INFO'}, f"Removed 'is_instance' property from {removed_count} objects")
        return {'FINISHED'}
    
"""
MAKEITGOOD SECTOR & HULL SPHERE -------------------------------------------------------
"""

class ButtonZoneHide(bpy.types.Operator):
    bl_idname = "scene.zone_hide"
    bl_label = "Show / Hide Track Zones"
    bl_description = "Shows or hides all track zones"
    
    def execute(self, context):
        track_zone_collection = bpy.data.collections.get('TRACK_ZONES')

        # Check if the TRACK_ZONES collection exists
        if track_zone_collection:
            for obj in track_zone_collection.objects:
                # Check if the object has the custom property and toggle visibility
                if "is_track_zone" in obj:
                    # In Blender 2.8 and later, visibility is controlled by 'hide_viewport'
                    obj.hide_viewport = not obj.hide_viewport

        return {"FINISHED"}

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
                    
class ButtonTriggerHide(bpy.types.Operator):
    bl_idname = "scene.trigger_hide"
    bl_label = "Show / Hide Triggers"
    bl_description = "Shows or hides all triggers"

    def execute(self, context):
        triggers_collection = bpy.data.collections.get('TRIGGERS')

        # Check if the TRIGGERS collection exists
        if triggers_collection:
            for obj in triggers_collection.objects:
                # Toggle visibility for each trigger object
                obj.hide_viewport = not obj.hide_viewport

        return {"FINISHED"}
    
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
        if bpy.context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        mesh_objects = [obj for obj in bpy.data.objects if obj.type == 'MESH']

        original_active_object = context.view_layer.objects.active
        if original_active_object and original_active_object.type == 'MESH':
            active_material_choice = original_active_object.data.material_choice
        else:
            self.report({'WARNING'}, "No active mesh object with material choice found.")
            return {'CANCELLED'}

        # Get existing textures once and reuse the result
        existing_textures = self.get_existing_textures()

        for obj in mesh_objects:
            obj.data.material_choice = active_material_choice

        self.assign_materials_to_all(mesh_objects, existing_textures)

        bpy.ops.object.select_all(action='DESELECT')
        for obj in mesh_objects:
            obj.select_set(True)
        context.view_layer.objects.active = original_active_object

        return {'FINISHED'}

    def update_material_assignment(self, obj, existing_textures):
        material_map = {
            'UV_TEX': '_UVTex',
            'COL': '_Col',
            'ALPHA': '_Alpha',
            'ENV': '_Env',
            'RGB': '_RGBModelColor',
            'NCP': '_NCP'  # Add NCP Material to the map
        }

        material_choice = obj.data.material_choice
        material_suffix = material_map.get(material_choice, '_Col')

        if material_choice == 'UV_TEX':
            self.assign_uv_textures(obj, existing_textures)
        elif material_choice == 'NCP':
            self.assign_ncp_materials(obj)
        else:
            self.assign_regular_materials(obj, material_suffix)

    def assign_materials_to_all(self, mesh_objects, existing_textures):
        bpy.ops.object.select_all(action='DESELECT')

        for obj in mesh_objects:
            obj.select_set(True)

        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')

        for obj in mesh_objects:
            self.update_material_assignment(obj, existing_textures)

        bpy.ops.object.mode_set(mode='OBJECT')

    def get_existing_textures(self):
        textures = {}
        for image in bpy.data.images:
            name_parts = image.name.rsplit('.', 1)
            if len(name_parts) > 1 and name_parts[-1].isalpha():
                textures[image.name] = name_parts[0]
                print(f"Added texture: {image.name} with base name: {name_parts[0]}")
        return textures

    def get_base_name_for_layers(self, obj):
        base_name = obj.name.split('.')[0]

        # Check if the object name contains any of the specific car part prefixes
        car_parts_prefixes = ["pin", "axle", "spring"]
        if any(prefix in base_name for prefix in car_parts_prefixes):
            # Remove digits for these car parts
            base_name = ''.join([char for char in base_name if not char.isdigit()])

        print(f"Base name derived: {base_name} for object: {obj.name}")
        return base_name

    def get_texture_base_name(self, tex_num, existing_textures):
        # Get the base name from the object name
        obj_name = self.get_base_name_for_layers(bpy.context.active_object)
        print(f"Checking base name: {obj_name} in existing textures: {existing_textures}")

        # Check if any texture in existing_textures starts with the base name
        for texture_name in existing_textures.keys():
            if texture_name.startswith(obj_name):
                return obj_name

        # If not, check for a generic 'car' texture
        if "car" in existing_textures:
            return "car"

        # If no match is found, return None
        return None

    def assign_uv_textures(self, obj, existing_textures):
        bm = bmesh.from_edit_mesh(obj.data)
        if bm is None:
            return

        texnum_layer = bm.faces.layers.int.get("Texture Number") or bm.faces.layers.int.new("Texture Number")

        is_car_part = any(prefix in obj.name for prefix in self.car_parts_prefixes)
        is_prm_object = obj.name.endswith('.prm')

        for face in bm.faces:
            if face.select:
                tex_num = face[texnum_layer]
                if tex_num == -1:
                    continue

                if is_car_part:
                    material_name = "car.bmp"
                    mat = bpy.data.materials.get(material_name)
                    if mat:
                        print(f"Assigned {material_name} to {obj.name}")
                    else:
                        base_material_name = self.get_texture_base_name(tex_num, existing_textures)
                        if base_material_name:
                            material_name = f"{base_material_name}{chr(97 + tex_num)}.bmp"
                            mat = bpy.data.materials.get(material_name)
                        else:
                            print(f"No matching material found for tex_num {tex_num} in {obj.name}")
                            continue
                elif is_prm_object:
                    # Directly use tex_num to determine the texture name
                    material_name = f"{chr(97 + tex_num)}.bmp"
                    mat = bpy.data.materials.get(material_name)
                    if not mat:
                        # If no direct match, try to find a texture with the same letter suffix
                        for texture_name in existing_textures.keys():
                            if texture_name.endswith(f"{chr(97 + tex_num)}.bmp"):
                                material_name = texture_name
                                mat = bpy.data.materials.get(material_name)
                                break
                        if not mat:
                            print(f"Material {material_name} not found for {obj.name}")
                            continue
                else:
                    base_material_name = self.get_texture_base_name(tex_num, existing_textures)
                    if base_material_name:
                        material_name = f"{base_material_name}{chr(97 + tex_num)}.bmp"
                        mat = bpy.data.materials.get(material_name)
                        if not mat:
                            print(f"Material {material_name} not found for {obj.name}")
                            continue
                    else:
                        print(f"No base material name found for tex_num {tex_num} in {obj.name}")
                        continue

                if mat and mat.name not in obj.data.materials:
                    obj.data.materials.append(mat)
                face.material_index = obj.data.materials.find(mat.name)

        bmesh.update_edit_mesh(obj.data)
        obj.data.update()

    def assign_ncp_materials(self, obj):
        bm = bmesh.from_edit_mesh(obj.data)
        if bm is None:
            return

        material_layer = bm.faces.layers.int.get("Material") or bm.faces.layers.int.new("Material")

        for face in bm.faces:
            if face.select:
                material_index = face[material_layer]
                if -1 < material_index < len(MATERIALS):
                    material_info = MATERIALS[material_index]
                    material_name = material_info[1]

                    mat = bpy.data.materials.get(material_name)
                    if not mat:
                        mat = bpy.data.materials.new(name=material_name)
                        mat.use_nodes = True
                        bsdf = mat.node_tree.nodes.get('Principled BSDF')
                        if bsdf:
                            bsdf.inputs['Base Color'].default_value = (*COLORS[material_index], 1.0)

                    if mat.name not in obj.data.materials:
                        obj.data.materials.append(mat)

                    face.material_index = obj.data.materials.find(mat.name)

        bmesh.update_edit_mesh(obj.data)
        obj.data.update()

    def assign_regular_materials(self, obj, material_suffix):
        base_name = self.get_base_name_for_layers(obj)

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
            print(f"Material {potential_names[0]} not found. Trying generic suffix.")
            material = bpy.data.materials.get(material_suffix)

        if not material:
            self.report({'WARNING'}, f"Material {potential_names[0]} not found.")
            return

        if material.name not in obj.data.materials:
            obj.data.materials.append(material)

        bm = bmesh.from_edit_mesh(obj.data)
        if bm:
            material_index = obj.data.materials.find(material.name)
            for face in bm.faces:
                if face.select:
                    face.material_index = material_index
            bmesh.update_edit_mesh(obj.data)

class MaterialAssignment(bpy.types.Operator):
    """Assign Materials to Selected Meshes Based on Material Choice"""
    bl_idname = "object.assign_materials"
    bl_label = "Assign Materials to Selected Meshes"
    bl_options = {'REGISTER', 'UNDO'}

    car_parts_prefixes = ["body", "wheel", "axle", "spring", "pin", "spinner"]

    def execute(self, context):
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

        active_material_choice = context.active_object.data.material_choice if context.active_object else 'COL'

        # Get existing textures once and reuse the result
        existing_textures = self.get_existing_textures()

        for obj in context.selected_objects:
            if obj.type == 'MESH' and hasattr(obj.data, 'material_choice'):
                obj.data.material_choice = active_material_choice
                self.update_material_assignment(obj, existing_textures)

        return {'FINISHED'}

    def update_material_assignment(self, obj, existing_textures):
        material_map = {
            'UV_TEX': '_UVTex',
            'COL': '_Col',
            'ALPHA': '_Alpha',
            'ENV': '_Env',
            'RGB': '_RGBModelColor',
            'NCP': '_NCP'  # Add NCP Material to the map
        }

        material_choice = obj.data.material_choice
        material_suffix = material_map.get(material_choice, '_Col')

        if material_choice == 'UV_TEX':
            self.assign_uv_textures(obj, existing_textures)
        elif material_choice == 'NCP':
            self.assign_ncp_materials(obj)
        else:
            self.assign_regular_materials(obj, material_suffix)

    def assign_ncp_materials(self, obj):
        bm = bmesh.from_edit_mesh(obj.data)
        if bm is None:
            return

        material_layer = bm.faces.layers.int.get("Material") or bm.faces.layers.int.new("Material")

        for face in bm.faces:
            if face.select:
                material_index = face[material_layer]
                if -1 < material_index < len(MATERIALS):
                    material_info = MATERIALS[material_index]
                    material_name = material_info[1]

                    mat = bpy.data.materials.get(material_name)
                    if not mat:
                        mat = bpy.data.materials.new(name=material_name)
                        mat.use_nodes = True
                        bsdf = mat.node_tree.nodes.get('Principled BSDF')
                        if bsdf:
                            bsdf.inputs['Base Color'].default_value = (*COLORS[material_index], 1.0)

                    if mat.name not in obj.data.materials:
                        obj.data.materials.append(mat)

                    face.material_index = obj.data.materials.find(mat.name)

        bmesh.update_edit_mesh(obj.data)
        obj.data.update()

    def get_existing_textures(self):
        textures = {}
        for image in bpy.data.images:
            name_parts = image.name.rsplit('.', 1)
            if len(name_parts) > 1 and name_parts[-1].isalpha():
                textures[image.name] = name_parts[0]
                print(f"Added texture: {image.name} with base name: {name_parts[0]}")
        return textures

    def get_base_name_for_layers(self, obj):
        base_name = obj.name.split('.')[0]

        # Check if the object name contains any of the specific car part prefixes
        car_parts_prefixes = ["pin", "axle", "spring"]
        if any(prefix in base_name for prefix in car_parts_prefixes):
            # Remove digits for these car parts
            base_name = ''.join([char for char in base_name if not char.isdigit()])

        print(f"Base name derived: {base_name} for object: {obj.name}")
        return base_name

    def get_texture_base_name(self, tex_num, existing_textures):
        # Get the base name from the object name
        obj_name = self.get_base_name_for_layers(bpy.context.active_object)
        print(f"Checking base name: {obj_name} in existing textures: {existing_textures}")

        # Check if any texture in existing_textures starts with the base name
        for texture_name in existing_textures.keys():
            if texture_name.startswith(obj_name):
                return obj_name

        # If not, check for a generic 'car' texture
        if "car" in existing_textures:
            return "car"

        # If no match is found, return None
        return None

    def assign_uv_textures(self, obj, existing_textures):
        bm = bmesh.from_edit_mesh(obj.data)
        if bm is None:
            return

        texnum_layer = bm.faces.layers.int.get("Texture Number") or bm.faces.layers.int.new("Texture Number")

        is_car_part = any(prefix in obj.name for prefix in self.car_parts_prefixes)
        is_prm_object = obj.name.endswith('.prm')

        for face in bm.faces:
            if face.select:
                tex_num = face[texnum_layer]
                if tex_num == -1:
                    continue

                if is_car_part:
                    material_name = "car.bmp"
                    mat = bpy.data.materials.get(material_name)
                    if mat:
                        print(f"Assigned {material_name} to {obj.name}")
                    else:
                        base_material_name = self.get_texture_base_name(tex_num, existing_textures)
                        if base_material_name:
                            material_name = f"{base_material_name}{chr(97 + tex_num)}.bmp"
                            mat = bpy.data.materials.get(material_name)
                        else:
                            print(f"No matching material found for tex_num {tex_num} in {obj.name}")
                            continue
                elif is_prm_object:
                    # Directly use tex_num to determine the texture name
                    material_name = f"{chr(97 + tex_num)}.bmp"
                    mat = bpy.data.materials.get(material_name)
                    if not mat:
                        # If no direct match, try to find a texture with the same letter suffix
                        for texture_name in existing_textures.keys():
                            if texture_name.endswith(f"{chr(97 + tex_num)}.bmp"):
                                material_name = texture_name
                                mat = bpy.data.materials.get(material_name)
                                break
                        if not mat:
                            print(f"Material {material_name} not found for {obj.name}")
                            continue
                else:
                    base_material_name = self.get_texture_base_name(tex_num, existing_textures)
                    if base_material_name:
                        material_name = f"{base_material_name}{chr(97 + tex_num)}.bmp"
                        mat = bpy.data.materials.get(material_name)
                        if not mat:
                            print(f"Material {material_name} not found for {obj.name}")
                            continue
                    else:
                        print(f"No base material name found for tex_num {tex_num} in {obj.name}")
                        continue

                if mat and mat.name not in obj.data.materials:
                    obj.data.materials.append(mat)
                face.material_index = obj.data.materials.find(mat.name)

        bmesh.update_edit_mesh(obj.data)
        obj.data.update()

    def assign_regular_materials(self, obj, material_suffix):
        base_name = self.get_base_name_for_layers(obj)

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
            print(f"Material {potential_names[0]} not found. Trying generic suffix.")
            material = bpy.data.materials.get(material_suffix)

        if not material:
            self.report({'WARNING'}, f"Material {potential_names[0]} not found.")
            return

        if material.name not in obj.data.materials:
            obj.data.materials.append(material)

        bm = bmesh.from_edit_mesh(obj.data)
        if bm:
            material_index = obj.data.materials.find(material.name)
            for face in bm.faces:
                if face.select:
                    face.material_index = material_index
            bmesh.update_edit_mesh(obj.data)

class MaterialAssignmentFin(bpy.types.Operator):
    """Assign Materials to All Meshes Automatically"""
    bl_idname = "object.assign_materials_fin"
    bl_label = "Assign Materials Automatically"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        if bpy.context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        mesh_objects = [obj for obj in bpy.data.objects if obj.type == 'MESH']

        original_active_object = context.view_layer.objects.active
        if original_active_object and original_active_object.type == 'MESH':
            active_material_choice = original_active_object.data.material_choice
        else:
            self.report({'WARNING'}, "No active mesh object with material choice found.")
            return {'CANCELLED'}

        for obj in mesh_objects:
            obj.data.material_choice = active_material_choice

        self.assign_materials_to_all(mesh_objects)

        bpy.ops.object.select_all(action='DESELECT')
        for obj in mesh_objects:
            obj.select_set(True)
        context.view_layer.objects.active = original_active_object

        return {'FINISHED'}

    def assign_materials_to_all(self, mesh_objects):
        bpy.ops.object.select_all(action='DESELECT')

        for obj in mesh_objects:
            obj.select_set(True)

        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')

        for obj in mesh_objects:
            self.update_material_assignment(obj)

        bpy.ops.object.mode_set(mode='OBJECT')

    def update_material_assignment(self, obj):
        material_map = {
            'UV_TEX': '_UVTex',
            'COL': '_Col',
            'ALPHA': '_Alpha',
            'ENV': '_Env',
            'RGB': '_RGBModelColor'
        }

        material_choice = obj.data.material_choice
        material_suffix = material_map.get(material_choice, '_Col')

        if material_choice == 'UV_TEX':
            self.assign_uv_textures(obj)
        else:
            self.assign_regular_materials(obj, material_suffix)

    def get_existing_textures(self):
        textures = {}
        for image in bpy.data.images:
            name_parts = image.name.rsplit('.', 1)
            if len(name_parts) > 1 and name_parts[-1].isalpha():
                textures[image.name] = name_parts[0]
        return textures

    def get_base_name_for_layers(self, obj):
        # Strip out any suffix numbers or additional suffixes like '.prm'
        base_name = obj.name.split('.')[0]
        base_name = ''.join([char for char in base_name if not char.isdigit()])
        return base_name

    def get_texture_base_name(self, tex_num, existing_textures):
        # Check if the texture name matches the object name
        obj_name = self.get_base_name_for_layers(bpy.context.active_object)
        if obj_name in existing_textures:
            return obj_name
        return None

    def assign_uv_textures(self, obj):
        # Ensure the object is in object mode before modifying the mesh
        if obj.mode == 'EDIT':
            bpy.ops.object.mode_set(mode='OBJECT')

        bm = bmesh.new()
        bm.from_mesh(obj.data)

        existing_textures = self.get_existing_textures()
        texnum_layer = bm.faces.layers.int.get("Texture Number") or bm.faces.layers.int.new("Texture Number")

        for face in bm.faces:
            tex_num = face[texnum_layer]
            if tex_num == -1:
                continue

            base_material_name = self.get_texture_base_name(tex_num, existing_textures)
            if base_material_name:
                material_name = f"{base_material_name}{chr(97 + tex_num)}.bmp"
                mat = bpy.data.materials.get(material_name)
                if mat:
                    if mat.name not in obj.data.materials:
                        obj.data.materials.append(mat)
                    face.material_index = obj.data.materials.find(mat.name)
                else:
                    print(f"No matching material found for tex_num {tex_num} in {obj.name}")

        bm.to_mesh(obj.data)
        bm.free()

        obj.data.update()  # Ensure the mesh updates in the viewport

    def assign_regular_materials(self, obj, material_suffix):
        base_name = self.get_base_name_for_layers(obj)

        potential_names = [
            f"{base_name}{material_suffix}",
            f"{base_name}.prm{material_suffix}",
        ]

        material = None
        for mat_name in potential_names:
            material = bpy.data.materials.get(mat_name)
            if material:
                break

        if not material:
            print(f"Material {potential_names[0]} not found. Trying generic suffix.")
            material = bpy.data.materials.get(material_suffix)

        if not material:
            self.report({'WARNING'}, f"Material {potential_names[0]} not found.")
            return

        if material.name not in obj.data.materials:
            obj.data.materials.append(material)

        bm = bmesh.from_edit_mesh(obj.data)
        if bm:
            material_index = obj.data.materials.find(material.name)
            for face in bm.faces:
                if face.select:
                    face.material_index = material_index
            bmesh.update_edit_mesh(obj.data)
        
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
    bl_label = "Calculate Texture Number"
    bl_description = "Sets the texture number based on the suffix (a-bz) of the assigned texture"

    def execute(self, context):
        for obj in context.scene.objects:
            if obj.type == 'MESH':
                # If the object is in edit mode, use from_edit_mesh and update_edit_mesh
                if obj.mode == 'EDIT':
                    bm = bmesh.from_edit_mesh(obj.data)
                else:
                    bm = bmesh.new()
                    bm.from_mesh(obj.data)

                # Check for the existence of the "Texture Number" layer
                texnum_layer = bm.faces.layers.int.get("Texture Number")
                if not texnum_layer:
                    texnum_layer = bm.faces.layers.int.new("Texture Number")

                # Iterate over all faces in the mesh
                for face in bm.faces:
                    # Get the material index for the face
                    mat_index = face.material_index
                    if mat_index >= len(obj.material_slots):
                        continue

                    # Retrieve the material from the object's material slots
                    material = obj.material_slots[mat_index].material

                    if not material or not material.use_nodes:
                        continue

                    # Iterate over the nodes in the material's node tree to find a texture node
                    texture_name = None
                    for node in material.node_tree.nodes:
                        if node.type == 'TEX_IMAGE':
                            texture_name = node.image.name
                            break

                    if texture_name:
                        # Extract the suffix before the file extension
                        suffix = texture_name.split('.')[-2][-1].lower() if '.' in texture_name else ''

                        # Map the suffix to a texture number (e.g., 'a' -> 0, 'b' -> 1)
                        if suffix.isalpha():
                            texture_num = ord(suffix) - ord('a')
                            if texture_num < 0 or texture_num >= TEX_PAGES_MAX:
                                texture_num = -1  # Set to -1 if the suffix is out of range
                        else:
                            texture_num = -1  # No valid suffix found

                        # Assign the texture number to the "Texture Number" layer
                        face[texnum_layer] = texture_num

                # Update the mesh with the changes
                if obj.mode == 'EDIT':
                    bmesh.update_edit_mesh(obj.data)
                else:
                    bm.to_mesh(obj.data)
                    bm.free()

                self.report({'INFO'}, f"Textures set for {obj.name}.")

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

    def adjust_brightness(self, texture, factor):
        for i in range(0, len(texture.pixels), 4):
            for j in range(3):
                texture.pixels[i + j] = min(texture.pixels[i + j] * factor, 1.0)
        texture.update()

    def get_brightness_factor(self, scene):
        factor_mapping = {
            1: 2.0,
            2: 1.9,
            3: 1.8,
            4: 1.7,
            5: 1.6,
            6: 1.5,
            7: 1.4,
            8: 1.3
        }
        return factor_mapping.get(scene.shadow_strength, 1.6)

    def darken_shadow(self, texture, threshold=0.99):
        for i in range(0, len(texture.pixels), 4):
            is_shadow_pixel = all(texture.pixels[i + j] < threshold for j in range(3))
            if is_shadow_pixel:
                for j in range(3):
                    texture.pixels[i + j] = 0.0
        texture.update()

    def invert_shadow(self, texture):
        for i in range(0, len(texture.pixels), 4):
            for j in range(3):
                texture.pixels[i + j] = 1.0 - texture.pixels[i + j]
        texture.update()

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

    def bake_and_process(self, context, margin, brightness_factor, darken_threshold, texture_name_suffix, material):
        """Bake and process the texture with given margin and brightness settings."""
        shadow_resolution = int(context.scene.shadow_resolution)
        shadow_tex = bpy.data.images.new(f"Shadow_{texture_name_suffix}", width=shadow_resolution, height=shadow_resolution, alpha=True)

        # Assign the texture to the material and make it active for baking
        self.assign_texture_to_material(material, shadow_tex)

        # Unwrap with specified margin and bake
        bpy.ops.uv.unwrap(method='ANGLE_BASED', margin=margin)
        bpy.ops.object.bake(type='AO')

        # Adjust brightness
        self.adjust_brightness(shadow_tex, brightness_factor)

        # Darken the shadow based on the threshold
        self.darken_shadow(shadow_tex, darken_threshold)

        # Invert the colors
        self.invert_shadow(shadow_tex)

        return shadow_tex

    def bake_blurred_texture_to_image(self, context, shadow_plane, material):
        """Bakes the material with the blur effect to a UV image and assigns it to the shadow plane."""
        shadow_resolution = int(context.scene.shadow_resolution)

        # Create a new image to store the baked blur
        shadow_image = bpy.data.images.new(name="shadow", width=shadow_resolution, height=shadow_resolution, alpha=True)

        # Ensure the shadow_plane has a UV map
        if not shadow_plane.data.uv_layers:
            bpy.ops.mesh.uv_texture_add()

        # Set the new image as active in the material for baking
        nodes = material.node_tree.nodes
        links = material.node_tree.links

        # Create the texture image node for baking
        tex_image_node = nodes.new('ShaderNodeTexImage')
        tex_image_node.image = shadow_image
        nodes.active = tex_image_node  # Set the image texture node as active

        # Ensure the shadow plane is the active object
        context.view_layer.objects.active = shadow_plane
        shadow_plane.select_set(True)

        # Bake the material to the image (using 'COMBINED' to include all shaders)
        bpy.ops.object.bake(type='COMBINED')

        # The blurred image will now appear in Blender's texture image list
        # Assign the baked image to the shadow plane for final output
        self.assign_final_texture(shadow_plane, shadow_image)

        return shadow_image

    def assign_final_texture(self, shadow_plane, shadow_tex):
        """Assigns the final baked shadow texture to the shadow plane."""
        mat = shadow_plane.active_material
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links

        # Add Image Texture node and assign the baked texture
        tex_image_node = nodes.new('ShaderNodeTexImage')
        tex_image_node.image = shadow_tex

        # Link texture to the material output
        bsdf_node = nodes.get("Principled BSDF")  # Assuming you're using Principled BSDF
        if bsdf_node:
            links.new(tex_image_node.outputs['Color'], bsdf_node.inputs['Base Color'])

        shadow_plane.active_material.use_nodes = True

    def bake_shadow(self, context):
        original_active = context.view_layer.objects.active
        scene = context.scene
        original_engine = scene.render.engine

        # Check for selected objects
        if not self.check_for_selected(context):
            return {'CANCELLED'}

        # Use shadow quality from scene
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
        lamp_data_pos.energy = 2000.0
        lamp_data_pos.size = 2.0
        lamp_positive = bpy.data.objects.new(name="ShadePositive", object_data=lamp_data_pos)
        scene.collection.objects.link(lamp_positive)

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

        # Apply scale
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

        mat, material_name = self.create_unique_material("ShadowMaterial")
        shadow_plane.data.materials.append(mat)

        # Prepare for first bake
        context.view_layer.objects.active = shadow_plane
        shadow_plane.select_set(True)
        bpy.ops.object.mode_set(mode='EDIT')

       # Get the brightness factor from the scene
        brightness_factor = self.get_brightness_factor(scene)

        # First bake
        shadow_tex1 = self.bake_and_process(context, margin=0.01, brightness_factor=brightness_factor, darken_threshold=0.99, texture_name_suffix="Bake1", material=mat)

        # Apply edge softening effect
        self.blur_texture_edges(mat, shadow_tex1)
        
        # Assign final texture to ShadowPlane material
        self.assign_final_texture(shadow_plane, shadow_tex1)

        # Bake the blurred texture to a UV image and assign it to the shadow plane
        blurred_texture_image = self.bake_blurred_texture_to_image(context, shadow_plane, mat)

        # **Remove Shadow_bake1 texture after baking**
        if "Shadow_Bake1" in bpy.data.images:
            bpy.data.images.remove(bpy.data.images["Shadow_Bake1"])
            
        # Remove ShadowPlane after baking is done
        bpy.data.objects.remove(shadow_plane, do_unlink=True)

        # Cleanup
        bpy.data.objects.remove(lamp_positive)
        scene.render.engine = original_engine

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
        # Check if the selection is valid
        if not self.check_for_selected(context):
            return {'CANCELLED'}  # Stop execution if the check fails

        # Store the original selection and active object
        original_active = context.view_layer.objects.active
        original_selection = context.selected_objects[:]

        # Perform shadow baking
        self.bake_shadow(context)
    
        # Restore the original selection and active object
        self.restore_selection(context, original_selection, original_active)
    
        # Ask if the user wants to save the shadow
        bpy.ops.lighttools.confirm_shadow_save('INVOKE_DEFAULT')

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

def menu_func_import(self, context):
    self.layout.operator(ImportRV.bl_idname, text="Re-Volt (.prm, .w, .ncp, .fin, .rim., .hul, .taz, .tri, .m, parameters.txt)")

def menu_func_export(self, context):
    # Use the SelectDefaultTexture operator to start the export process
    self.layout.operator(SelectDefaultTexture.bl_idname, text="Re-Volt (.prm, .w, .ncp, .fin, .rim, .hul, .taz, .tri, .m)")
