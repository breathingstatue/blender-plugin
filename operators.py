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

from mathutils import Vector as BlenderVector
from . import tools
from .hul_in import create_sphere
from .layers import *
from .texanim import *
from .tools import generate_chull
from .rvstruct import *
from . import carinfo
from .common import get_format, FORMAT_PRM, FORMAT_FIN, FORMAT_NCP, FORMAT_HUL, FORMAT_W, FORMAT_RIM, FORMAT_TA_CSV, FORMAT_TAZ, FORMAT_UNK
from .common import get_errors, msg_box, FORMATS, to_revolt_scale, FORMAT_CAR

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
            w_in.import_file(self.filepath, scene, context)

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
        return exec_export(self, self.filepath, context)

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
     
        return {'RUNNING_MODAL'}
    
def exec_export(self, filepath, context):
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
    props.last_exported_filepath = filepath
    
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
        ncp_out.export_file(filepath, scene, context)

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

    # Gets any encountered errors
    errors = get_errors()

    # Display export results
    end_time = time.time() - start_time

    # Define an icon (replace 'ICON_NAME' with the actual icon name you want to use)
    icon = 'INFO'  # You can change this to 'ERROR' if needed

    self.report({'INFO'}, "Export to {} done in {:.3f} seconds.\n{}".format(FORMATS[frmt], end_time, errors))

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
        props = context.scene.revolt
        res = exec_export(props.last_exported_filepath, context)
        return res
    
# Operator for toggling w_parent_meshes
class RVIO_OT_ToggleWParentMeshes(bpy.types.Operator):
    bl_idname = "rvio.toggle_w_parent_meshes"
    bl_label = "Toggle Parent Meshes"
    
    def execute(self, context):
        props = context.scene.revolt
        props.w_parent_meshes = not props.w_parent_meshes
        return {'FINISHED'}

# Operator for toggling w_import_bound_boxes
class RVIO_OT_ToggleWImportBoundBoxes(bpy.types.Operator):
    bl_idname = "rvio.toggle_w_import_bound_boxes"
    bl_label = "Toggle Import Bound Boxes"
    
    def execute(self, context):
        props = context.scene.revolt
        props.w_import_bound_boxes = not props.w_import_bound_boxes
        return {'FINISHED'}

class RVIO_OT_SetBoundBoxCollection(bpy.types.Operator):
    bl_idname = "rvio.set_bound_box_collection"
    bl_label = "Set Bound Box Collection"
    bl_options = {'REGISTER', 'UNDO'}

    num_collections: bpy.props.IntProperty(
        name="Number of Collections", 
        default=1, 
        min=1, 
        max=19, 
        description="Number of collections to assign bound boxes to"
    )

def assign_objects_to_collections(objects, num_collections, context):
    # Ensure there is at least one collection
    if num_collections < 1:
        return
    
    # Create or get existing collections
    collections = []
    for i in range(num_collections):
        collection_name = f"Collection_{i+1}"
        collection = bpy.data.collections.get(collection_name)
        if not collection:
            collection = bpy.data.collections.new(collection_name)
            context.scene.collection.children.link(collection)  # Link collection to the scene
        collections.append(collection)

    # Distribute objects across collections
    for index, obj in enumerate(objects):
        target_collection = collections[min(index, num_collections - 1)]
        # Link object to target collection and unlink from all others
        for collection in obj.users_collection:
            collection.objects.unlink(obj)
        target_collection.objects.link(obj)

def execute(self, context):
    props = context.scene.rvgl_props

    imported_bound_boxes = get_imported_bound_boxes()

    assign_objects_to_collections(imported_bound_boxes, self.num_collections, context)

    return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        self.layout.prop(self, "num_collections", text="Number of Collections")

# Operator for toggling w_import_cubes
class RVIO_OT_ToggleWImportCubes(bpy.types.Operator):
    bl_idname = "rvio.toggle_w_import_cubes"
    bl_label = "Toggle Import Cubes"
    
    def execute(self, context):
        props = context.scene.revolt
        props.w_import_cubes = not props.w_import_cubes
        return {'FINISHED'}

class RVIO_OT_SetCubeCollection(bpy.types.Operator):
    bl_idname = "rvio.set_cube_collection"
    bl_label = "Set Cube Collection"
    bl_options = {'REGISTER', 'UNDO'}

    num_collections: bpy.props.IntProperty(
        name="Number of Collections",
        default=1,
        min=1,
        max=19,
        description="Number of collections to assign cubes to"
    )

    def assign_objects_to_collections(self, objects, num_collections, context):
        if num_collections < 1:
            return
        
        # Create or get existing collections
        collections = []
        for i in range(num_collections):
            collection_name = f"Cube_Collection_{i+1}"
            collection = bpy.data.collections.get(collection_name)
            if not collection:
                collection = bpy.data.collections.new(collection_name)
                context.scene.collection.children.link(collection)
            collections.append(collection)

        # Distribute cubes across collections
        for index, obj in enumerate(objects):
            target_collection = collections[min(index, num_collections - 1)]
            for collection in obj.users_collection:
                collection.objects.unlink(obj)
            target_collection.objects.link(obj)

    def execute(self, context):
        props = context.scene.revolt

        imported_cubes = get_imported_cubes()

        self.assign_objects_to_collections(imported_cubes, self.num_collections, context)

        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        self.layout.prop(self, "num_collections", text="Number of Collections")

class RVIO_OT_ToggleWImportBigCubes(bpy.types.Operator):
    bl_idname = "rvio.toggle_w_import_big_cubes"
    bl_label = "Toggle Import Big Cubes"
    
    def execute(self, context):
        props = context.scene.revolt
        props.w_import_big_cubes = not props.w_import_big_cubes
        return {'FINISHED'}

class RVIO_OT_SetBigCubeCollection(bpy.types.Operator):
    bl_idname = "rvio.set_big_cube_collection"
    bl_label = "Set Big Cube Collection"
    bl_options = {'REGISTER', 'UNDO'}

    num_collections: bpy.props.IntProperty(
        name="Number of Collections",
        default=1,
        min=1,
        max=19,
        description="Number of collections to assign big cubes to"
    )

    def assign_objects_to_collections(self, objects, num_collections, context):
        if num_collections < 1:
            return
        
        # Create or get existing collections
        collections = []
        for i in range(num_collections):
            collection_name = f"Big_Cube_Collection_{i+1}"
            collection = bpy.data.collections.get(collection_name)
            if not collection:
                collection = bpy.data.collections.new(collection_name)
                context.scene.collection.children.link(collection)
            collections.append(collection)

        # Distribute big cubes across collections
        for index, obj in enumerate(objects):
            target_collection = collections[min(index, num_collections - 1)]
            for collection in obj.users_collection:
                collection.objects.unlink(obj)
            target_collection.objects.link(obj)

    def execute(self, context):
        props = context.scene.revolt

        imported_big_cubes = get_imported_big_cubes()

        self.assign_objects_to_collections(imported_big_cubes, self.num_collections, context)

        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        self.layout.prop(self, "num_collections", text="Number of Collections")

class RVIO_OT_ToggleNCPExportSelected(bpy.types.Operator):
    bl_idname = "rvio.toggle_ncp_export_selected"
    bl_label = "Toggle NCP Export Selected"
    
    def execute(self, context):
        scene = context.scene
        scene.ncp_export_selected = not scene.ncp_export_selected
        return {'FINISHED'}


class RVIO_OT_ToggleNCPExportCollgrid(bpy.types.Operator):
    bl_idname = "rvio.toggle_ncp_export_collgrid"
    bl_label = "Toggle NCP Export Collision Grid"
    
    def execute(self, context):
        scene = context.scene
        scene.ncp_export_collgrid = not scene.ncp_export_collgrid
        return {'FINISHED'}
    
class RVIO_OT_SetNCPGridSize(bpy.types.Operator):
    bl_idname = "rvio.set_ncp_grid_size"
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
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        self.layout.prop(self, "grid_size", text="Grid Size", slider=True)
    
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

class ToggleTriangulateNgons(bpy.types.Operator):
    """Toggle Triangulate Ngons"""
    bl_idname = "object.triangulate_ngons"
    bl_label = "Triangulate Ngons"

    # Property to act as a tickbox
    is_enabled: bpy.props.BoolProperty(
        name="Enable Triangulation",
        description="Toggle Triangulation",
        default=True
    )

    def execute(self, context):
        context.scene.triangulate_ngons_enabled = not context.scene.triangulate_ngons_enabled
        self.report({'INFO'}, "Triangulate Ngons: {}".format("Enabled" if context.scene.triangulate_ngons_enabled else "Disabled"))
        return {'FINISHED'}

    @classmethod
    def poll(cls, context):
        return True

class ToggleExportWithoutTexture(bpy.types.Operator):
    """Toggle Export w/o Texture"""
    bl_idname = "object.export_without_texture"
    bl_label = "Toggle Export w/o Texture"

    def execute(self, context):
        context.scene.export_without_texture = not context.scene.export_without_texture
        return {'FINISHED'}
    
class ToggleApplyScale(bpy.types.Operator):
    """Toggle Apply Scale on Export"""
    bl_idname = "object.toggle_apply_scale"
    bl_label = "Apply Scale on Export"

    def execute(self, context):
        context.scene.apply_scale_on_export = not context.scene.apply_scale_on_export
        return {'FINISHED'}

class ToggleApplyRotation(bpy.types.Operator):
    """Toggle Apply Rotation on Export"""
    bl_idname = "object.toggle_apply_rotation"
    bl_label = "Toggle Apply Rotation on Export"

    def execute(self, context):
        context.scene.apply_rotation_on_export = not context.scene.apply_rotation_on_export
        return {'FINISHED'}
    
class ButtonBakeShadow(bpy.types.Operator):
    bl_idname = "button.bake_shadow"
    bl_label = "Bake Shadow"
    bl_description = "Creates a shadow plane beneath the selected object"

    def execute(self, context):
        bake_shadow(context)
        return {"FINISHED"}

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
                obj.revolt.use_tex_num = scene.revolt.use_tex_num
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
    
"""
OBJECTS -----------------------------------------------------------------------
"""
    
class ToggleEnvironmentMap(bpy.types.Operator):
    bl_idname = "object.toggle_environment_map"
    bl_label = "Environment Map On/Off"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        for obj in context.selected_objects:
            # Toggle the fin_env property for the object.
            if "fin_env" in obj and isinstance(obj["fin_env"], bool):
                current_state = obj["fin_env"]
            else:
                current_state = False

            # Update the fin_env property to its new state
            obj["fin_env"] = not current_state
            
            self.report({'INFO'}, f"Environment map {'enabled' if obj['fin_env'] else 'disabled'} for {obj.name}")

        return {'FINISHED'}
                
class SetEnvironmentMapColor(bpy.types.Operator):
    bl_idname = "object.set_environment_map_color"
    bl_label = "Set EnvMap Color"
    bl_options = {'REGISTER', 'UNDO'}

    # Define a color property to use as a color picker in the UI
    color: bpy.props.FloatVectorProperty(
        name="EnvMap Color",
        subtype='COLOR',
        default=(1.0, 1.0, 1.0, 1.0),
        min=0.0,
        max=1.0,
        size=4,
        description="Pick a color for the environment map"
    )

    def execute(self, context):
        objs = context.selected_objects if context.selected_objects else [context.object]

        for obj in objs:
            # Directly access the custom property to set the color
            # Ensure that 'fin_envcol' is defined as a custom property for the object
            obj["fin_envcol"] = self.color

            self.report({'INFO'}, f"Environment map color set to {self.color} for {obj.name}")

        return {'FINISHED'}

    def invoke(self, context, event):
        # This method is called when the operator is invoked to display the color picker
        return context.window_manager.invoke_props_dialog(self)
                            
class IgnoreNCP(bpy.types.Operator):
    bl_idname = "object.toggle_ignore_ncp"
    bl_label = "Toggle Ignore Collision (.ncp)"
    
    def execute(self, context):
        obj = context.object
        
        # Directly toggle the ignore_ncp property on the object
        if "ignore_ncp" in obj:
            obj["ignore_ncp"] = not obj["ignore_ncp"]
            self.report({'INFO'}, f"Ignore collision (.ncp) toggled for {obj.name}.")
        else:
            # Initialize the property if it doesn't exist
            obj["ignore_ncp"] = True
            self.report({'INFO'}, f"Ignore collision (.ncp) property initialized and set to True for {obj.name}.")

        return {'FINISHED'}  

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
        current_state = obj.get("fin_no_cam_coll", False)
        obj["fin_no_cam_coll"] = not current_state
        self.report({'INFO'}, f"No Camera Collision property {'enabled' if not current_state else 'disabled'} for {obj.name}.")
        return {'FINISHED'}
    
class ToggleNoObjectCollision(bpy.types.Operator):
    bl_idname = "object.toggle_no_obj_coll"
    bl_label = "No Object Collision"
    bl_description = "Toggle the 'No Object Collision' property"

    def execute(self, context):
        obj = context.object
        current_state = obj.get("fin_no_obj_coll", False)
        obj["fin_no_obj_coll"] = not current_state
        self.report({'INFO'}, f"No Object Collision property {'enabled' if not current_state else 'disabled'} for {obj.name}.")
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

class ButtonHullSphere(bpy.types.Operator):
    bl_idname = "object.add_hull_sphere"
    bl_label = "Add Hull Sphere"
    bl_description = "Creates a hull sphere at the 3D cursor's location"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        center = bpy.context.scene.cursor.location
        
        # Assuming to_revolt_scale(0.1) is the desired scale for the radius
        radius = to_revolt_scale(0.1)
        
        filename = "Hull_Sphere"

        # Create the sphere at the cursor location with the specified radius
        ob = create_sphere(context.scene, center, radius, filename)

        # Link the new object to the scene
        if context.collection:
            context.collection.objects.link(ob)
        else:
            context.scene.collection.objects.link(ob)

        # Assign the custom property 'is_hull_sphere' to the object
        ob["is_hull_sphere"] = True

        # Select the newly created object and make it active
        ob.select_set(True)
        context.view_layer.objects.active = ob

        return {'FINISHED'}
    
"""
VERTEX COLORS -----------------------------------------------------------------
"""

class ButtonVertexColorSet(bpy.types.Operator):
    bl_idname = "vertexcolor.set"
    bl_label = "Set Color and Alpha"
    bl_description = "Apply color and alpha to selected faces"

    def set_vertex_color(self, context, color, alpha):
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

        # Apply color and alpha to the vertex colors
        for face in bm.faces:
            if face.select:
                for loop in face.loops:
                    loop[color_layer] = (color[0], color[1], color[2], alpha)

        bmesh.update_edit_mesh(mesh)
        return True

    def execute(self, context):
        scene = context.scene
        color_props = scene.vertex_color_picker_props  # Fetch color
        alpha_value = getattr(scene, 'vertex_alpha_value', 1.0)  # Fetch alpha

        # Call set_vertex_color with both color and alpha
        success = self.set_vertex_color(context, color_props.vertex_color, alpha_value)

        if success:
            self.report({'INFO'}, "Color and alpha applied to selected faces.")
        else:
            self.report({'WARNING'}, "Failed to apply color and alpha.")
        return {"FINISHED"}

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

class ButtonVertexAlphaSetLayer(bpy.types.Operator):
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