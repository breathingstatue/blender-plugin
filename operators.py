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
import json

from mathutils import Vector as BlenderVector
from . import tools
from .hul_in import create_sphere
from .layers import *
from .texanim import *
from .tools import generate_chull, bake_shadow
from .rvstruct import *
from . import carinfo
from .common import get_format, FORMAT_PRM, FORMAT_FIN, FORMAT_NCP, FORMAT_HUL, FORMAT_W, FORMAT_RIM, FORMAT_TA_CSV, FORMAT_TAZ, FORMAT_UNK
from .common import get_errors, msg_box, FORMATS, to_revolt_scale, FORMAT_CAR, TEX_PAGES_MAX

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

class ButtonSelectFaceProp(bpy.types.Operator):
    bl_idname = "faceprops.select"
    bl_label = "sel"
    bl_description = "Select or delesect all polygons with this property"
    prop = bpy.props.IntProperty()

    def execute(self, context):
        select_faces(context, self.prop)
        return{"FINISHED"}


class ButtonSelectNCPFaceProp(bpy.types.Operator):
    bl_idname = "ncpfaceprops.select"
    bl_label = "sel"
    bl_description = "Select or delesect all polygons with this property"
    prop = bpy.props.IntProperty()

    def execute(self, context):
        select_ncp_faces(context, self.prop)
        return{"FINISHED"}


class ButtonSelectNCPMaterial(bpy.types.Operator):
    bl_idname = "ncpmaterial.select"
    bl_label = "sel"
    bl_description = "Select all faces of the same material"

    def execute(self, context):
        props = context.scene.revolt
        meshprops = context.object.data.revolt
        props.select_material = meshprops.face_material
        return{"FINISHED"}
    
class ButtonBakeShadow(bpy.types.Operator):
    bl_idname = "button.bake_shadow"
    bl_label = "Bake Shadow"
    bl_description = "Creates a shadow plane beneath the selected object"

    def execute(self, context):
        bake_shadow(context)
        return {"FINISHED"}
    

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
        props = scene.revolt
        frmt = get_format(self.filepath)

        start_time = time.time()
        context.window.cursor_set("WAIT")

        print("Importing {}".format(self.filepath))

        # Handle different formats
        if frmt == FORMAT_UNK:
            self.report({'ERROR'}, "Unsupported format.")
            return {'CANCELLED'}

        elif frmt == FORMAT_PRM:
            from . import prm_in
            prm_in.import_file(self.filepath, scene)

        elif frmt == FORMAT_CAR:
            from . import parameters_in
            old_check = props.prm_check_parameters
            props.prm_check_parameters = True
            parameters_in.import_file(self.filepath, scene)
            props.prm_check_parameters = old_check

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
            w_in.import_file(self.filepath, scene)

        elif frmt == FORMAT_RIM:
            from . import rim_in
            rim_in.import_file(self.filepath, scene)
        
        elif frmt == FORMAT_TAZ:
            from . import taz_in
            taz_in.import_file(self.filepath, scene)
        
        else:
            self.report({'ERROR'}, "Format not yet supported: {}".format(FORMATS.get(frmt, "Unknown Format")))
            return {'CANCELLED'}

        # Gets any encountered errors
        errors = get_errors()
            
        context.window.cursor_set("DEFAULT")
        return {"FINISHED"}

    def draw(self, context):
        props = context.scene.revolt
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

    def execute(self, context):
        return exec_export(self.filepath, context)

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
     
        return {'RUNNING_MODAL'}
    
def exec_export(filepath, context):
    scene = context.scene
    props = context.scene.revolt

    start_time = time.time()
    context.window.cursor_set("WAIT")

    frmt = get_format(filepath)

    # Turns off undo for better performance
    use_global_undo = bpy.context.preferences.edit.use_global_undo
    bpy.context.preferences.edit.use_global_undo = False

    if bpy.ops.object.mode_set.poll():
        bpy.ops.object.mode_set(mode="OBJECT")

    # Saves filepath for re-exporting the same file
    scene.last_exported_filepath = filepath
    
    # Handle different formats
    if frmt == FORMAT_UNK:
        self.report({'ERROR'}, "Unsupported format.")
        return {'CANCELLED'}

    if frmt == FORMAT_PRM:
        from . import prm_out
        prm_out.export_file(filepath, scene, context)

    elif frmt == FORMAT_FIN:
        from . import fin_out
        print("Exporting to .fin...")
        fin_out.export_file(filepath, scene)

    elif frmt == FORMAT_NCP:
        from . import ncp_out
        print("Exporting to .ncp...")
        ncp_out.export_file(filepath, scene)

    elif frmt == FORMAT_HUL:   
        from . import hul_out
        print("Exporting to .hul...")
        hul_out.export_file(filepath, scene)

    elif frmt == FORMAT_W:
        from . import w_out
        print("Exporting to .w...")
        w_out.export_file(filepath, scene)

    elif frmt == FORMAT_RIM:
        from . import rim_out
        print("Exporting to .rim...")
        rim_out.export_file(filepath, scene)

    elif frmt == FORMAT_TA_CSV:
        from . import ta_csv_out
        print("Exporting texture animation sheet...")
        ta_csv_out.export_file(filepath, scene)

    elif frmt == FORMAT_TAZ:
        from . import taz_out
        taz_out.export_file(filepath, scene)
        
    # Re-enables undo and cleanup
    bpy.context.preferences.edit.use_global_undo = use_global_undo
        
    context.window.cursor_set("DEFAULT")

    end_time = time.time() - start_time
    errors = get_errors()  # Make sure this function does not depend on 'self'
    print("Export to {} done in {:.3f} seconds.\n{}".format(FORMATS[frmt], end_time, errors))

    return {"FINISHED"}
    
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
            elif key in ['wheel', 'spring', 'pin', 'axle', 'spinner', 'aerial', 'body', 'ai']:
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
        filepath = scene.last_exported_filepath
        if filepath:
            result = exec_export(filepath, context)
            if result == {'FINISHED'}:
                self.report({'INFO'}, "Re-export successful.")
            else:
                self.report({'WARNING'}, "Re-export may have encountered issues.")
            return result
        else:
            self.report({'WARNING'}, "No file path found for re-exporting.")
            return {'CANCELLED'}
        
class ToggleTriangulateNgons(bpy.types.Operator):
    """Toggle Triangulate Ngons"""
    bl_idname = "export.triangulate_ngons"
    bl_label = "Triangulate Ngons"

    def execute(self, context):
        context.scene.triangulate_ngons = not context.scene.triangulate_ngons
        self.report({'INFO'}, "Triangulate Ngons: {}".format("Enabled" if context.scene.triangulate_ngons else "Disabled"))
        return {'FINISHED'}

class ExportWithoutTexture(bpy.types.Operator):
    """Toggle Export w/o Texture"""
    bl_idname = "export.without_texture"
    bl_label = "Toggle Export w/o Texture"

    def execute(self, context):
        context.scene.use_tex_num = not context.scene.use_tex_num
        if context.scene.use_tex_num:
            self.report({'INFO'}, "Exports without Texture")
        else:
            self.report({'INFO'}, "Uses Texture on Export")
        return {'FINISHED'}
    
class ToggleApplyScale(bpy.types.Operator):
    """Toggle Apply Scale on Export"""
    bl_idname = "export.apply_scale"
    bl_label = "Apply Scale on Export"

    def execute(self, context):
        context.scene.apply_scale = not context.scene.apply_scale
        if context.scene.apply_scale:
            self.report({'INFO'}, "Apply Scale on Export ON")
        else:
            self.report({'INFO'}, "Apply Scale on Export OFF")
        return {'FINISHED'}

class ToggleApplyRotation(bpy.types.Operator):
    """Toggle Apply Rotation on Export"""
    bl_idname = "export.apply_rotation"
    bl_label = "Toggle Apply Rotation on Export"

    def execute(self, context):
        context.scene.apply_rotation = not context.scene.apply_rotation
        if context.scene.apply_rotation:
            self.report({'INFO'}, "Apply Rotation on Export ON")
        else:
            self.report({'INFO'}, "Apply Rotation on Export OFF")
        return {'FINISHED'}
    
class ToggleApplyTranslation(bpy.types.Operator):
    """Toggle Apply Translation on Export.\nDisable for single/instance .ncp files"""
    bl_idname = "export.apply_translation"
    bl_label = "Apply Translation on Export."

    def execute(self, context):
        context.scene.apply_translation = not context.scene.apply_translation
        if context.scene.apply_translation:
            self.report({'INFO'}, "Apply Translation on Export ON")
        else:
            self.report({'INFO'}, "Apply Translation on Export OFF")
        return {'FINISHED'}
    
class RVIO_OT_ToggleWParentMeshes(bpy.types.Operator):
    bl_idname = "rvio.toggle_w_parent_meshes"
    bl_label = "Toggle Parent Meshes"
    
    def execute(self, context):
        context.scene.w_parent_meshes = not context.scene.w_parent_meshes
        self.report({'INFO'}, f"Toggle Parent Meshes: {'ON' if context.scene.w_parent_meshes else 'OFF'}")
        return {'FINISHED'}

class RVIO_OT_ToggleWImportBoundBoxes(bpy.types.Operator):
    bl_idname = "rvio.toggle_w_import_bound_boxes"
    bl_label = "Toggle Import Bound Boxes"
    
    def execute(self, context):
        context.scene.w_import_bound_boxes = not context.scene.w_import_bound_boxes
        self.report({'INFO'}, f"Toggle Import Bound Boxes: {'ON' if context.scene.w_import_bound_boxes else 'OFF'}")
        return {'FINISHED'}

class RVIO_OT_ToggleWImportCubes(bpy.types.Operator):
    bl_idname = "rvio.toggle_w_import_cubes"
    bl_label = "Toggle Import Cubes"
    
    def execute(self, context):
        context.scene.w_import_cubes = not context.scene.get("w_import_cubes", False)
        self.report({'INFO'}, f"Toggle Import Cubes: {'ON' if context.scene.w_import_cubes else 'OFF'}")
        return {'FINISHED'}

class RVIO_OT_ToggleWImportBigCubes(bpy.types.Operator):
    bl_idname = "rvio.toggle_w_import_big_cubes"
    bl_label = "Toggle Import Big Cubes"
    
    def execute(self, context):
        context.scene.w_import_big_cubes = not context.scene.get("w_import_big_cubes", False)
        self.report({'INFO'}, f"Toggle Import Big Cubes: {'ON' if context.scene.w_import_big_cubes else 'OFF'}")
        return {'FINISHED'}

class RVIO_OT_NCPExportSelected(bpy.types.Operator):
    bl_idname = "rvio.ncp_export_selected"
    bl_label = "Toggle NCP Export Selected"
    
    def execute(self, context):
        scene = context.scene
        # Toggle the ncp_export_selected property
        scene.ncp_export_selected = not scene.ncp_export_selected
        
        # Conditional message based on the toggled state
        if scene.ncp_export_selected:
            self.report({'INFO'}, "Will export selected as .ncp")
        else:
            self.report({'INFO'}, ".ncp exporting disabled for object")
            
        return {'FINISHED'}

class RVIO_OT_NCPExportCollgrid(bpy.types.Operator):
    bl_idname = "rvio.ncp_export_collgrid"
    bl_label = "Toggle NCP Export Collision Grid"
    
    def execute(self, context):
        scene = context.scene
        # Toggle the ncp_export_collgrid property
        scene.ncp_export_collgrid = not scene.ncp_export_collgrid
        
        # Conditional message based on the toggled state
        if scene.ncp_export_collgrid:
            self.report({'INFO'}, "Exporting collgrid for .ncp")
        else:
            self.report({'INFO'}, "Collgrid export disabled")
            
        return {'FINISHED'}
    
class RVIO_OT_NCPGridSize(bpy.types.Operator):
    bl_idname = "rvio.ncp_grid_size"
    bl_label = "Set NCP Grid Size"
    bl_options = {'REGISTER', 'UNDO'}

    grid_size: bpy.props.IntProperty(
        name="Grid Size",
        default=1024,
        min=512,
        max=8192,
        description="Size of the lookup grid",
        subtype='UNSIGNED'
    )

    def execute(self, context):
        scene = context.scene
        scene.ncp_collgrid_size = self.grid_size
        self.report({'INFO'}, f"Collgrid size set to {self.grid_size}")
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        self.layout.prop(self, "grid_size", text="Grid Size", slider=True)


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
            self.report({'ERROR'}, "Name too long. Max 8 characters.")
            return {'CANCELLED'}

        base_name = self.new_name[:7] if len(selected_objects) > 1 else self.new_name

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

class BatchBake(bpy.types.Operator):
    bl_idname = "helpers.batch_bake_model"
    bl_label = "Bake all selected"
    bl_description = (
        "Bakes the light cast by lamps in the current scene to the Instance"
        "model colors"
    )

    def execute(self, context):
        n = tools.batch_bake(self, context)
        msg_box("Baked {} objects".format(n))
        return{"FINISHED"}

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
    bl_label = "Copy project textures"
    bl_description = (
        "Saves all used track texture files to desired project directory and takes a care of correct files names"
    )
    bl_options = {'REGISTER'}
    
    directory = bpy.props.StringProperty(
        name="Outdir Path",
        description="Where to save all the textures",
        subtype='DIR_PATH' 
    )

    def execute(self, context):
        dirname = os.path.basename(os.path.dirname(self.directory))
        # try to copy each image to selected project directory
        for image in bpy.data.images:
            if ".bmp" in image.name:
                base, ext = image.name.split(".", 1)
            try:
                if image.source == 'FILE':
                    dst = os.path.join(self.directory, int_to_texture(int(base), dirname))
                    shutil.copyfile(image.filepath, dst)                 
            except:
                print("Failed to copy image %s" % image.name)
                
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class TexturesRename(bpy.types.Operator):
    bl_idname = "helpers.texture_rename"
    bl_label = "Rename Texture"
    bl_description = (
        "Rename selected object's texture(s) with a base name and a letter suffix for multiple textures"
    )

    base_name: bpy.props.StringProperty(
        name="Base Name",
        description="Base name for the textures",
        maxlen=8  # Maximum length is 8 characters
    )

    def execute(self, context):
        textures = self.get_textures(context)

        if not textures:
            self.report({'WARNING'}, "No textures found in selected objects")
            return {'CANCELLED'}

        if len(textures) == 1:
            # If only one texture, use the full base name
            textures[0].name = self.base_name[:8]
        else:
            # If multiple textures, limit base name to 7 characters and add a suffix
            for i, texture in enumerate(textures):
                suffix = self.number_to_letter(i)
                texture.name = self.base_name[:7] + suffix

        return {'FINISHED'}

    def get_textures(self, context):
        # Retrieve all textures from selected objects
        textures = []
        for obj in context.selected_objects:
            for slot in obj.material_slots:
                if slot.material and slot.material.use_nodes:
                    for node in slot.material.node_tree.nodes:
                        if node.type == 'TEX_IMAGE' and node.image and node.image.source == 'FILE':
                            textures.append(node.image)
        return textures

    def number_to_letter(self, number):
        # Convert a number to a letter, starting from 'a'
        return chr(97 + number % 26)  # Modulo 26 to loop back after 'z'
    
class UseTextureNumber(bpy.types.Operator):
    """Toggle Use Texture Number"""
    bl_idname = "helpers.use_texture_number"
    bl_label = "Use Texture Number"
    bl_description = "Toggle the use of texture number for the active object"

    def execute(self, context):
        scene = context.scene
        if context.selected_objects:  # This ensures it affects all selected objects, not just the active one
            for obj in context.selected_objects:
                obj.use_tex_num = scene.use_tex_num
        else:
            self.report({'INFO'}, "No object selected")
            return {'CANCELLED'}

        return {'FINISHED'}

class CarParametersExport(bpy.types.Operator):
    bl_idname = "helpers.car_parameters_export"
    bl_label = "Car parameters to clipboard"
    bl_description = (
        "Copies most important parameters into clipboard"
    )

    def execute(self, context):
        from . import parameters_out
        parameters_out.export_file()
        return{"FINISHED"}
    
"""
INSTANCES -----------------------------------------------------------------------
"""

class SetInstanceProperty(bpy.types.Operator):
    bl_idname = "instances.set_instance_property"
    bl_label = "Mark as Instance"
    bl_description = "Marks all selected objects as instances"

    def execute(self, context):
        for obj in context.selected_objects:
            # Set 'is_instance' as a custom property
            obj["is_instance"] = True

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
    
class InstanceColor(bpy.types.Operator):
    bl_idname = "object.use_fin_col"
    bl_label = "Apply Fin Color"
    bl_options = {'REGISTER', 'UNDO'}

    fin_col: bpy.props.FloatVectorProperty(
        name="Fin Color",
        subtype='COLOR',
        default=(0.5, 0.5, 0.5),
        min=0.0, max=1.0,
        description="Set the object's color"
    )

    def execute(self, context):
        obj = context.active_object

        if obj is None:
            self.report({'WARNING'}, "No active object")
            return {'CANCELLED'}

        # Store the color directly in the object's custom properties
        obj["fin_col"] = self.fin_col[:3]  # Store RGB values

        if hasattr(obj, "color"):
            obj.color = (self.fin_col[0], self.fin_col[1], self.fin_col[2], 1.0)  # Set RGBA

        color_values = tuple(round(val, 3) for val in self.fin_col[:3])
        self.report({'INFO'}, f"Fin color applied to {obj.name}: {color_values}")
        return {'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

"""
OBJECTS -----------------------------------------------------------------------
"""
    
class ToggleEnvironmentMap(bpy.types.Operator):
    bl_idname = "object.toggle_environment_map"
    bl_label = "Environment Map On/Off"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        for obj in context.selected_objects:
            # Check if the 'fin_env' property exists and is a boolean.
            # If it doesn't exist or isn't a boolean, assume it's True by default.
            current_state = obj.get("fin_env", True)

            # Toggle the fin_env property for the object.
            obj["fin_env"] = not current_state
            
            self.report({'INFO'}, f"Environment map {'enabled' if obj['fin_env'] else 'disabled'} for {obj.name}")

        return {'FINISHED'}
                
class SetEnvironmentMapColor(bpy.types.Operator):
    bl_idname = "object.set_environment_map_color"
    bl_label = "Set Environment Map Color"
    bl_options = {'REGISTER', 'UNDO'}

    fin_envcol: bpy.props.FloatVectorProperty(
        name="EnvMap Color",
        subtype='COLOR',
        default=(1.0, 1.0, 1.0, 1.0),
        size=4,  # Include alpha
        min=0.0, max=1.0,
        description="Set the environment map's color and alpha"
    )

    def execute(self, context):
        obj = context.active_object

        if obj is None:
            self.report({'WARNING'}, "No active object")
            return {'CANCELLED'}

        # Store the RGBA color directly in the object's custom properties
        obj["fin_envcol"] = [self.fin_envcol[0], self.fin_envcol[1], self.fin_envcol[2], self.fin_envcol[3]]

        # Correctly format the message to display color values
        color_values = tuple(round(val, 3) for val in obj["fin_envcol"])
        self.report({'INFO'}, f"Environment map color set to {color_values} for {obj.name}")

        return {'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

class SetBCubeMeshIndices(bpy.types.Operator):
    bl_idname = "object.set_bcube_mesh_indices"
    bl_label = "Set Mesh Indices"
    
    def execute(self, context):
        obj = context.object
        
        # Clear any previous mesh indices
        obj["bcube_mesh_indices"] = ""
        
        # Iterate through child meshes and add their indices
        for child_obj in obj.children:
            if child_obj.type == 'MESH':
                if obj["bcube_mesh_indices"]:
                    obj["bcube_mesh_indices"] += ","
                # Ensure you're getting the right index or identifier for the child mesh here
                obj["bcube_mesh_indices"] += str(child_obj.data.index)  # Verify if 'data.index' is correct
        
        self.report({'INFO'}, f"BCube mesh indices set for {obj.name}.")
        return {'FINISHED'}

class ToggleModelRGB(bpy.types.Operator):
    bl_idname = "object.toggle_model_rgb"
    bl_label = "Toggle Model RGB"
    bl_description = "Toggle the 'Use Model Color' property"

    def execute(self, context):
        obj = context.object
        if obj and "is_instance" in obj and obj["is_instance"]:
            # Toggle the 'fin_model_rgb' property
            current_state = obj.get("fin_model_rgb", False)
            obj["fin_model_rgb"] = not current_state
            # Report the new state of 'fin_model_rgb'
            self.report({'INFO'}, f"Use Model Color {'enabled' if obj['fin_model_rgb'] else 'disabled'} for {obj.name}.")
        else:
            # Report if 'is_instance' is not found or not true
            self.report({'WARNING'}, "'is_instance' property not found or not true.")

        return {'FINISHED'}

class ToggleFinHide(bpy.types.Operator):
    bl_idname = "object.toggle_fin_hide"
    bl_label = "Toggle Hide Property"
    bl_description = "Toggle the 'Hide' property for the object"

    def execute(self, context):
        obj = context.object
        if obj and "is_instance" in obj and obj["is_instance"]:
            obj.fin_hide = not obj.fin_hide
            self.report({'INFO'}, f"Hide property {'enabled' if obj.fin_hide else 'disabled'} for {obj.name}.")
        else:
            self.report({'WARNING'}, "'is_instance' property not found or not true.")
        
        return {'FINISHED'}
    
class ToggleFinPriority(bpy.types.Operator):
    bl_idname = "object.toggle_fin_priority"
    bl_label = "Toggle Priority Property"
    bl_description = "Toggle the 'Priority' property for the object between 0 and 1"

    def execute(self, context):
        obj = context.object
        if obj and "is_instance" in obj and obj["is_instance"]:
            # Toggle the 'fin_priority' property between 0 and 1
            obj.fin_priority = 1 if obj.fin_priority == 0 else 0
            self.report({'INFO'}, f"Priority set to {obj.fin_priority} for {obj.name}.")
        else:
            self.report({'WARNING'}, "'is_instance' property not found or not true.")
        
        return {'FINISHED'}
    
class ResetFinLoDBias(bpy.types.Operator):
    bl_idname = "object.reset_fin_lod_bias"
    bl_label = "Reset LoD Bias"
    bl_description = "Reset the 'LoD Bias' to its default value"

    def execute(self, context):
        obj = context.object
        if obj and "is_instance" in obj and obj["is_instance"]:
            obj.fin_lod_bias = 1024  # Reset to default
            self.report({'INFO'}, f"LoD Bias reset to 1024 for {obj.name}.")
        else:
            self.report({'WARNING'}, "'is_instance' property not found or not true.")
        
        return {'FINISHED'}
    
class ToggleNoMirror(bpy.types.Operator):
    bl_idname = "object.toggle_no_mirror"
    bl_label = "Toggle No Mirror Mode"
    bl_description = "Toggle the 'Don't show in Mirror Mode' property"

    def execute(self, context):
        obj = context.object
        if obj and "is_instance" in obj and obj["is_instance"]:
            current_state = obj.get("fin_no_mirror", False)
            obj["fin_no_mirror"] = not current_state
            self.report({'INFO'}, f"No Mirror Mode {'enabled' if not current_state else 'disabled'} for {obj.name}.")
        else:
            self.report({'WARNING'}, "'is_instance' property not found or not true.")
        return {'FINISHED'}

class ToggleNoLights(bpy.types.Operator):
    bl_idname = "object.toggle_no_lights"
    bl_label = "Is Affected by Light"
    bl_description = "Toggle the 'Is affected by Light' property"

    def execute(self, context):
        obj = context.object
        if obj and "is_instance" in obj and obj["is_instance"]:
            # Directly toggle the fin_no_lights property on the object
            current_state = obj.get("fin_no_lights", False)
            obj["fin_no_lights"] = not current_state
            self.report({'INFO'}, f"'Is affected by Light' property {'enabled' if not current_state else 'disabled'} for {obj.name}.")
        else:
            self.report({'WARNING'}, "'is_instance' property not found or not set to True.")
        return {'FINISHED'}
        
class ToggleNoCameraCollision(bpy.types.Operator):
    bl_idname = "object.toggle_no_cam_coll"
    bl_label = "No Camera Collision"
    bl_description = "Toggle the 'No Camera Collision' property"

    def execute(self, context):
        obj = context.object
        if obj and "is_instance" in obj and obj["is_instance"]:
            current_state = obj.get("fin_no_cam_coll", False)
            obj["fin_no_cam_coll"] = not current_state
            self.report({'INFO'}, f"No Camera Collision property {'enabled' if not current_state else 'disabled'} for {obj.name}.")
        else:
            self.report({'WARNING'}, "'is_instance' property not found or not true.")
        return {'FINISHED'}
    
class ToggleNoObjectCollision(bpy.types.Operator):
    bl_idname = "object.toggle_no_obj_coll"
    bl_label = "No Object Collision"
    bl_description = "Toggle the 'No Object Collision' property"

    def execute(self, context):
        obj = context.object
        if obj and "is_instance" in obj and obj["is_instance"]:
            current_state = obj.get("fin_no_obj_coll", False)
            obj["fin_no_obj_coll"] = not current_state
            self.report({'INFO'}, f"No Object Collision property {'enabled' if not current_state else 'disabled'} for {obj.name}.")
        else:
            self.report({'WARNING'}, "'is_instance' property not found or not true.")
        return {'FINISHED'}
   
class ToggleMirrorPlane(bpy.types.Operator):
    bl_idname = "object.toggle_mirror_plane"
    bl_label = "Toggle Mirror Plane"
    bl_description = "Toggle Mirror Plane property for the selected object"

    @classmethod
    def poll(cls, context):
        return context.selected_objects

    def execute(self, context):
        for obj in context.selected_objects:
            if "is_mirror_plane" not in obj.keys():
                obj["is_mirror_plane"] = True
            else:
                obj["is_mirror_plane"] = not obj["is_mirror_plane"]
            
            status = "tagged" if obj["is_mirror_plane"] else "untagged"
            self.report({'INFO'}, f"Object is {status} as Mirror Plane")
        
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
            hull_object.name = f"is_hull_convex"
            hull_object.revolt.is_hull_convex = True  # Marking the object as a convex hull
            self.report({'INFO'}, "Convex hull generated successfully.")
        else:
            self.report({'ERROR'}, "Convex hull generation failed.")
        return {'FINISHED'}

"""
TEXTURE ANIMATIONS -------------------------------------------------------
"""

class OBJECT_OT_add_texanim_uv(bpy.types.Operator):
    """Add a new texanim UV layer with an associated image"""
    bl_idname = "object.add_texanim_uv"
    bl_label = "Add Texanim UV Layer and Image"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object

        if not obj or not obj.type == 'MESH':
            self.report({'ERROR'}, "Active object is not a mesh")
            return {'CANCELLED'}

        uv_layers = obj.data.uv_layers

        # Find the highest existing texan index
        highest_index = 0
        for uv_layer in uv_layers:
            if uv_layer.name.startswith("texan"):
                try:
                    # Assuming the format "texan001", the index starts from character 5 to the end
                    index = int(uv_layer.name[5:])
                    highest_index = max(highest_index, index)
                except ValueError:
                    self.report({'WARNING'}, f"Found improperly formatted layer name: {uv_layer.name}")

        # Create new UV layer
        new_index = highest_index + 1
        base_name = f"texan{new_index:03}"
        new_uv_layer = uv_layers.new(name=base_name)

        # Create a new image
        new_image = bpy.data.images.new(name=base_name, width=1024, height=1024)

        # Ensure there is at least one material on the object
        if not obj.material_slots:
            new_mat = bpy.data.materials.new(name="Material_" + base_name)
            obj.data.materials.append(new_mat)
        else:
            new_mat = obj.material_slots[0].material

        # Assign the image to the material's texture slot
        if new_mat.use_nodes:
            bsdf = new_mat.node_tree.nodes.get('Principled BSDF')
            if bsdf:
                tex_image = new_mat.node_tree.nodes.new('ShaderNodeTexImage')
                tex_image.image = new_image
                new_mat.node_tree.links.new(bsdf.inputs['Base Color'], tex_image.outputs['Color'])
        else:
            tex_slot = new_mat.texture_slots.add()
            tex_slot.texture = bpy.data.textures.new(base_name, 'IMAGE')
            tex_slot.texture.image = new_image

        self.report({'INFO'}, f"Created new UV layer and image: {base_name}")
        return {'FINISHED'}
    
class ButtonCopyUvToFrame(bpy.types.Operator):
    bl_idname = "texanim.copy_uv_to_frame"
    bl_label = "UV to Frame"
    bl_description = "Copies the UV coordinates of the currently selected face to the texture animation frame"

    def execute(self, context):
        if not copy_uv_to_frame(context):
            self.report({'ERROR'}, "Failed to copy UVs to frame.")
            return {'CANCELLED'}
        
        self.report({'INFO'}, "Successfully copied UVs to frame.")
        return {'FINISHED'}

class ButtonCopyFrameToUv(bpy.types.Operator):
    bl_idname = "texanim.copy_frame_to_uv"
    bl_label = "Copy Frame to UV"
    bl_description = "Copies the UV coordinates of the frame to the currently selected face"

    def execute(self, context):
        copy_frame_to_uv(context)

        # Redraw all 3D views to reflect the changes
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()

        return {'FINISHED'}

class RVIO_OT_TexAnimTransform(bpy.types.Operator):
    bl_idname = "rvio.texanim_transform"
    bl_label = "Transform Animation"
    bl_description = "Assigns a linearly ordered texture sequence to animation frames"

    def execute(self, context):
        scene = context.scene

        # Deserialize the JSON string to a Python object
        ta = json.loads(scene.texture_animations)

        # Ensure 'ta' structure is properly initialized
        while len(ta) < scene.ta_max_slots + 1:  # +1 since we're using 1-based indexing
            ta.append({"frames": [{} for _ in range(scene.ta_max_frames)]})

        frame_start = scene.frame_start
        frame_end = scene.frame_end
        total_frames = frame_end - frame_start + 1

        # Calculate delay based on the total animation time and number of frames
        delay = scene.frame_duration / total_frames

        for frame_number in range(frame_start, frame_end + 1):
            # Find the corresponding image based on the frame number
            image_index = (frame_number - 1) % scene.ta_max_slots + 1  # Looping through images
            image_name = f"texan{image_index:03}"
            image = bpy.data.images.get(image_name)

            if image:
                slot_index = image_index  # Slot index directly from image name
                frame_index = frame_number - frame_start

                if slot_index < len(ta) and frame_index < len(ta[slot_index]["frames"]):
                    ta[slot_index]["frames"][frame_index]["duration"] = delay
                    ta[slot_index]["frames"][frame_index]["texture"] = image.name
                else:
                    self.report({'WARNING'}, f"Indexing error: slot {slot_index} or frame {frame_index} is out of range.")
            else:
                self.report({'WARNING'}, f"No image found for {image_name}")

        # Serialize and save the updated animation data
        scene.texture_animations = json.dumps(ta)

        self.report({'INFO'}, "Textures assigned to animation frames.")
        return {'FINISHED'}


class TexAnimGrid(bpy.types.Operator):
    bl_idname = "texanim.grid"
    bl_label = "Grid Animation"
    bl_description = "Creates an animation based on a grid texture."

    frame_start = bpy.props.IntProperty(
        name = "Start Frame",
        min = 0,
        description = "Start frame of the animation"
    )
    grid_x = bpy.props.IntProperty(
        name = "X Resolution",
        min = 1,
        default = 2,
        description = "Amount of frames along the X axis"
    )
    grid_y = bpy.props.IntProperty(
        name = "Y Resolution",
        min = 1,
        default = 2,
        description = "Amount of frames along the Y axis"
    )
    delay = bpy.props.FloatProperty(
        name = "Frame duration",
        description = "Duration of every frame",
        min = 0.0,
        default = 0.02,
    )
    texture = bpy.props.IntProperty(
        name = "Texture",
        default = 0,
        min = -1,
        max = TEX_PAGES_MAX-1,
        description = "Texture for every frame"
    )

    def execute(self, context):
        scene = context.scene

        ta = json(scene.texture_animations)
        slot = scene.ta_current_slot
        max_frames = scene.ta_max_frames

        frame_start = self.frame_start
        grid_x = self.grid_x
        grid_y = self.grid_y
        nframes = grid_x * grid_y

        if nframes > max_frames:
            msg_box(
                "Frame out of range.\n"
                "Please set the amount of frames to {}.".format(
                    frame_end + 1),
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

                ta[slot]["frames"][frame_start + i]["delay"] = self.delay
                ta[slot]["frames"][frame_start + i]["texture"] = self.texture

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

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout

        row = layout.row(align=True)
        row.prop(self, "frame_start")

        row = layout.row(align=True)
        row.prop(self, "grid_x")
        row.prop(self, "grid_y")

        row = layout.row()
        row.prop(self, "delay", icon="PREVIEW_RANGE")
        row.prop(self, "texture", icon="TEXTURE")

"""
TRACK ZONES & HULL SPHERE -------------------------------------------------------
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
    bl_description = (
        "Adds a new track zone under cursor location"
    )
    bl_options = {'UNDO'}
    
    def execute(self, context):
        from .taz_in import create_zone
        cursor_location = context.scene.cursor.location
        obj = create_zone(None, cursor_location)
        return {'FINISHED'}
    
class ButtonHullSphere(bpy.types.Operator):
    bl_idname = "scene.add_hull_sphere"
    bl_label = "Add Hull Sphere"
    bl_description = "Creates a hull sphere at the 3D cursor's location"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        center = bpy.context.scene.cursor.location
        radius = to_revolt_scale(0.1)
        filename = "Hull_Sphere"

        ob = create_sphere(context.scene, center, radius, filename)

        if ob.name not in context.collection.objects:
            context.collection.objects.link(ob)
        else:
            self.report({'WARNING'}, f"Object '{ob.name}' is already in the collection")
            return {'CANCELLED'}

        ob["is_hull_sphere"] = True

        ob.select_set(True)
        context.view_layer.objects.active = ob

        return {'FINISHED'}
    
    
"""
VERTEX COLORS -----------------------------------------------------------------
"""

class ButtonVertexColorCreateLayer(bpy.types.Operator):
    bl_idname = "vertexcolor.create_layer"
    bl_label = "Create Vertex Color Layer"
    bl_description = "Creates a new vertex color layer"

    def execute(self, context):
        obj = context.object
        if obj.type != 'MESH' or obj.mode != 'EDIT':
            self.report({'WARNING'}, "Operation requires an active mesh object in edit mode.")
            return {'CANCELLED'}

        mesh = obj.data
        bm = bmesh.from_edit_mesh(mesh)

        # Check if the color layer already exists
        if bm.loops.layers.color.active is not None:
            self.report({'INFO'}, "Vertex color layer already exists.")
            return {'CANCELLED'}

        # Create a new vertex color layer
        bm.loops.layers.color.new("VertexColor")
        bmesh.update_edit_mesh(mesh)
        self.report({'INFO'}, "New vertex color layer created.")
        return {'FINISHED'}

class ButtonVertexAlphaLayer(bpy.types.Operator):
    bl_idname = "vertexcolor.set_alpha"
    bl_label = "Set Vertex Alpha"
    bl_description = "Set alpha value for the vertex color layer"
    alpha: bpy.props.FloatProperty()  # Add an alpha property

    def set_vertex_alpha(self, context, alpha_value):
        obj = context.object
        if obj.type != 'MESH' or obj.mode != 'EDIT':
            self.report({'WARNING'}, "Operation requires an active mesh object in edit mode.")
            return False

        mesh = obj.data
        bm = bmesh.from_edit_mesh(mesh)
        color_layer = bm.loops.layers.color.active

        if color_layer is None:
            self.report({'WARNING'}, "No active vertex color layer found.")
            return False

        # Apply the alpha value to the vertex colors
        for face in bm.faces:
            for loop in face.loops:
                loop[color_layer][3] = alpha_value  # Set alpha for each vertex color

        bmesh.update_edit_mesh(mesh)
        return True

    def execute(self, context):
        success = self.set_vertex_alpha(context, self.alpha)
        if success:
            context.scene.vertex_alpha_value = self.alpha  # Store alpha value
            self.report({'INFO'}, "Alpha value set for vertex colors.")
        else:
            self.report({'WARNING'}, "Failed to set alpha value.")
        return {'FINISHED' if success else 'CANCELLED'}
    
class ButtonVertexColorSet(bpy.types.Operator):
    bl_idname = "vertexcolor.set"
    bl_label = "Set Color and Alpha"
    bl_description = "Apply color and alpha to selected faces"
   
class VertexColorRemove(bpy.types.Operator):
    bl_idname = "vertexcolor.remove"
    bl_label = "Remove Vertex Color"
    bl_description = "Remove the vertex colors from selected vertices"

    def execute(self, context):
        obj = context.object

        if obj.type != 'MESH' or obj.mode != 'EDIT':
            self.report({'WARNING'}, "Operation requires an active mesh object in edit mode.")
            return {'CANCELLED'}

        mesh = obj.data
        bm = bmesh.from_edit_mesh(mesh)
        color_layer = bm.loops.layers.color.active

        if color_layer is None:
            self.report({'WARNING'}, "No active vertex color layer found.")
            return {'CANCELLED'}

        for face in bm.faces:
            for loop in face.loops:
                loop[color_layer] = (1.0, 1.0, 1.0, 1.0)  # Setting color to white

        bmesh.update_edit_mesh(mesh)
        self.report({'INFO'}, "Vertex color removed.")
        return {'FINISHED'}
