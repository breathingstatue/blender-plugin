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

from . import tools
from .props.props_obj import RVObjectProperties
from .props.props_scene import RVSceneProperties
from .layers import *
from .texanim import *
from .rvstruct import *
from .ui.settings import RVGLAddonPreferences
from . import carinfo
from .common import get_format, FORMAT_PRM, FORMAT_FIN, FORMAT_NCP, FORMAT_HUL, FORMAT_W, FORMAT_RIM, FORMAT_TA_CSV, FORMAT_TAZ, FORMAT_UNK
from .common import get_errors, msg_box, FORMATS

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

def get_addon_preferences():
    revolt = __name__.split('.')[0]
    preferences = bpy.context.preferences
    return preferences.addons[revolt].preferences

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

        if frmt in [FORMAT_W, FORMAT_PRM, FORMAT_NCP]:
            box = layout.box()
            box.prop(props, "enable_tex_mode")

        if frmt == FORMAT_W:
            box = layout.box()
            box.prop(props, "w_parent_meshes")
            box.prop(props, "w_import_bound_boxes")
            if props.w_import_bound_boxes:
                box.prop(props, "w_bound_box_layers")
            box.prop(props, "w_import_cubes")
            if props.w_import_cubes:
                box.prop(props, "w_cube_layers")
            box.prop(props, "w_import_big_cubes")
            if props.w_import_big_cubes:
                box.prop(props, "w_big_cube_layers")

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

    if filepath == "":
        msg_box("File not specified.", "ERROR")
        return {"FINISHED"}

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
        prm_out.export_file(filepath)

    elif frmt == FORMAT_FIN:
        from . import fin_out
        print("Exporting to .fin...")
        fin_out.export_file(filepath)

    elif frmt == FORMAT_NCP:
        from . import ncp_out
        print("Exporting to .ncp...")
        ncp_out.export_file(filepath)

    elif frmt == FORMAT_HUL:   
        from . import hul_out
        print("Exporting to .hul...")
        hul_out.export_file(filepath)

    elif frmt == FORMAT_W:
        from . import w_out
        print("Exporting to .w...")
        w_out.export_file(filepath)

    elif frmt == FORMAT_RIM:
        from . import rim_out
        print("Exporting to .rim...")
        rim_out.export_file(filepath)

    elif frmt == FORMAT_TA_CSV:
        from . import ta_csv_out
        print("Exporting texture animation sheet...")
        ta_csv_out.export_file(filepath)

    elif frmt == FORMAT_TAZ:
        from . import taz_out
        taz_out.export_file(filepath)
        
    # Re-enables undo and cleanup
    bpy.context.preferences.edit.use_global_undo = use_global_undo
        
    context.window.cursor_set("DEFAULT")

    # Gets any encountered errors
    errors = get_errors()

    # Display export results
    end_time = time.time() - start_time
    msg_box("Export to {} done in {:.3f} seconds.\n{}".format(FORMATS[frmt], end_time, get_errors()),icon=ico)

    return {"FINISHED"}

class RVIO_OT_SelectRevoltDirectory(bpy.types.Operator):
    bl_idname = "rvio.select_revolt_dir"
    bl_label = "Select Re-Volt Directory"
    bl_description = "Select the directory where RVGL is located"

    directory: bpy.props.StringProperty(subtype='DIR_PATH')

    def execute(self, context):
        prefs = get_addon_preferences()
        prefs.revolt_dir = self.directory  # Update the revolt_dir with the selected directory
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
    
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
        # Get addon preferences
        prefs = get_addon_preferences()
        rvgl_dir = prefs.revolt_dir

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
    
"""
BUTTONS ------------------------------------------------------------------------
"""

class ButtonReExport(bpy.types.Operator):
    bl_idname = "export_scene.revolt_redo"
    bl_label = "Re-Export"
    bl_description = "Redo the same export again"

    def execute(self, context):
        props = context.scene.revolt
        res = exec_export(props.last_exported_filepath, context)
        return res


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
    
"""
VERTEX COLROS -----------------------------------------------------------------
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

"""
HELPERS -----------------------------------------------------------------------
"""

class ButtonEnableMaterialMode(bpy.types.Operator):
    bl_idname = "helpers.enable_material_mode"
    bl_label = "Enable Material Preview"
    bl_description = "Enables material preview mode to see textures and materials"

    def execute(self, context):
        enable_material_mode()  # This function should set the shading mode to 'MATERIAL'
        return {"FINISHED"}


class ButtonEnableSolidMode(bpy.types.Operator):
    bl_idname = "helpers.enable_solid_mode"
    bl_label = "Enable Solid Mode"
    bl_description = "Enables solid shading mode"

    def execute(self, context):
        enable_solid_mode()  # This function should set the shading mode to 'SOLID'
        return {"FINISHED"}


class ButtonRenameAllObjects(bpy.types.Operator):
    bl_idname = "object.rename_selected_objects"
    bl_label = "Rename Selected Objects"
    bl_description = "Renames all selected objects using a new name"

    new_name: bpy.props.StringProperty(
        name="New Name",
        default="NewName",
        description="Enter a new name for the selected objects"
    )

    def execute(self, context):
        # Loop through selected objects and rename them
        for obj in bpy.context.selected_objects:
            obj.name = self.new_name

        return {'FINISHED'}


class SelectByName(bpy.types.Operator):
    bl_idname = "helpers.select_by_name"
    bl_label = "Select by name"
    bl_description = (
        "Selects all objects that contain the name"
        )

    def execute(self, context):
        n = tools.select_by_name(self, context)
        msg_box("Selected {} objects".format(n))
        return{"FINISHED"}


class SelectByData(bpy.types.Operator):
    bl_idname = "helpers.select_by_data"
    bl_label = "Select by data"
    bl_description = (
        "Selects all objects with the same object data (mesh)"
    )

    def execute(self, context):
        n = tools.select_by_data(self, context)
        msg_box("Selected {} objects".format(n))
        return{"FINISHED"}


class SetInstanceProperty(bpy.types.Operator):
    bl_idname = "helpers.set_instance_property"
    bl_label = "Mark as Instance"
    bl_description = ("Marks all selected objects as instances")

    def set_property_to_selected(self, context, property_name, value):
        count = 0
        for obj in context.selected_objects:
            setattr(obj, property_name, value)
            count += 1
        return count

    def execute(self, context):
        for obj in context.selected_objects:
            obj.is_instance = True
        context.view_layer.update()
        self.report({'INFO'}, "Marked {} objects as instances".format(len(context.selected_objects)))
        return{'FINISHED'}


class RemoveInstanceProperty(bpy.types.Operator):
    bl_idname = "helpers.rem_instance_property"
    bl_label = "Remove Instance property"
    bl_description = ("")

    def set_property_to_selected(self, context, property_name, value):
        count = 0
        for obj in context.selected_objects:
            setattr(obj, property_name, value)
            count += 1
        return count

    def execute(self, context):
        for obj in context.selected_objects:
            obj.is_instance = False
        context.view_layer.update()
        self.report({'INFO'}, "Removed instance property from {} objects".format(len(context.selected_objects)))
        return{'FINISHED'}
    
class AssignEnvColorProperty(bpy.types.Operator):
    """Assign Environment Color Property to Selected Objects"""
    bl_idname = "object.assign_env_color_property"
    bl_label = "Assign Env Color Property"

    def execute(self, context):
        for obj in context.selected_objects:
            obj.fin_envcol = (1.0, 1.0, 1.0, 1.0)  # Default color
        return {'FINISHED'}

def get_addon_preferences():
    revolt = __name__.split('.')[0]
    preferences = bpy.context.preferences
    return preferences.addons[revolt].preferences

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
        prefs = get_addon_preferences()
        rvgl_dir = prefs.revolt_dir

        if not rvgl_dir or not os.path.isdir(rvgl_dir):
            self.report({'WARNING'}, f"RVGL directory '{rvgl_dir}' is not set or invalid.")
            return {'CANCELLED'}

        executable_path = None
        if "rvgl.exe" in os.listdir(rvgl_dir):
            executable_path = os.path.join(rvgl_dir, "rvgl.exe")
        elif "rvgl" in os.listdir(rvgl_dir):
            executable_path = os.path.join(rvgl_dir, "rvgl")

        if executable_path and os.path.isfile(executable_path):
            # Set the working directory to rvgl_dir when launching the subprocess
            subprocess.Popen([executable_path], cwd=rvgl_dir)
        else:
            self.report({'WARNING'}, f"RVGL executable not found in '{rvgl_dir}'.")
            return {'CANCELLED'}

        return {'FINISHED'}

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
    bl_label = "Rename track textures"
    bl_description = (
        "Assigns a proper name to each texture image used and makes their id numbers consistent"
    )

    def execute(self, context):
        number = 0
        for image in bpy.data.images:
            if image.source == 'FILE':
                image.name = f"{number:04d}.bmp"
                number += 1
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
    

class IgnoreNCP(bpy.types.Operator):
    bl_idname = "object.toggle_ignore_ncp"
    bl_label = "Toggle Ignore Collision (.ncp)"
    
    def execute(self, context):
        # Toggle the ignore_ncp property
        obj = context.object
        obj.revolt.ignore_ncp = not obj.revolt.ignore_ncp
        return {'FINISHED'}
    

class SetBCubeMeshIndices(bpy.types.Operator):
    bl_idname = "object.set_bcube_mesh_indices"
    bl_label = "Set Mesh Indices"
    
    def execute(self, context):
        obj = context.object
        revolt_props = obj.revolt
        
        # Clear any previous mesh indices
        revolt_props.bcube_mesh_indices = ""
        
        # Iterate through child meshes and add their indices
        for child_obj in obj.children:
            if child_obj.type == 'MESH':
                if revolt_props.bcube_mesh_indices:
                    revolt_props.bcube_mesh_indices += ","
                revolt_props.bcube_mesh_indices += str(child_obj.data.index)
        
        return {'FINISHED'}
    

class PickInstanceColor(bpy.types.Operator):
    bl_idname = "object.pick_instance_color"
    bl_label = "Pick Instance Color"
    
    def execute(self, context):
        # Check if there's a selected object
        if context.selected_objects:
            selected_object = context.selected_objects[0]
            
            # Check if the selected object is an instance (you can customize this check)
            if "instance" in selected_object.name.lower():
                # Open the color picker dialog
                bpy.context.window_manager.invoke_props_dialog(self)
                return {'RUNNING_MODAL'}
        
        # If no valid instance is selected, do nothing
        return {'CANCELLED'}
    
    # Properties for the color picker
    color: bpy.props.FloatVectorProperty(
        name="Color",
        subtype='COLOR',
        size=3,  # Set size to 3 for RGB color
        min=0.0,
        max=1.0,
        default=(1.0, 1.0, 1.0)
    )
    
    def draw(self, context):
        layout = self.layout
        layout.prop(self, "color")
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def finish(self, context):
        # Apply the picked color to the selected instance object
        if context.selected_objects:
            selected_object = context.selected_objects[0]
            
            # Check if the selected object is an instance (you can customize this check)
            if "instance" in selected_object.name.lower():
                selected_object.color = self.color
        
        return {'FINISHED'}
    
class SetModelColor(bpy.types.Operator):
    bl_idname = "object.set_model_color"
    bl_label = "Set Model Color"
    bl_description = "Open the color picker to set the Model Color"
    
    def execute(self, context):
        return {'RUNNING_MODAL'}
    
    def invoke(self, context, event):
        # Open the color picker dialog and set the result to update the color
        context.window_manager.invoke_props_dialog(self)
        return {'RUNNING_MODAL'}
    
    # Property for the color picker
    color: bpy.props.FloatVectorProperty(
        name="Model Color",
        subtype='COLOR',
        default=(0.5, 0.5, 0.5),
        min=0.0, max=1.0,
        description="Model RGB color to be added/subtracted:\n1.0: Bright, overrides vertex colors\n"
            "0.5: Default, leaves vertex colors intact\n"
            "0.0: Dark",
        size=3  # Ensure size is set to 3 for RGB color
    )
    
    def draw(self, context):
        layout = self.layout
        layout.prop(self, "color")
    
    def finish(self, context):
        # Check if there's a selected object
        if context.selected_objects:
            selected_object = context.selected_objects[0]
            
            # Check if the selected object is an instance (you can customize this check)
            if "instance" in selected_object.name.lower():
                selected_object.revolt.fin_col = self.color[:3]  # Set RGB values from the color picker
        
        return {'FINISHED'}

class ToggleEnvironmentMap(bpy.types.Operator):
    bl_idname = "object.toggle_environment_map"
    bl_label = "Toggle Environment Map"

    def execute(self, context):
        obj = context.active_object
        if obj is None:
            self.report({'WARNING'}, "No active object")
            return {'CANCELLED'}

        if obj.get("is_instance", False):
            # If object is an instance, handle 'env_layer' and 'env_alpha_layer'
            # This code assumes you have a way to handle these properties
            # For demonstration, just toggling a custom property
            if "env_layer_info" in obj:
                del obj["env_layer_info"]
                self.report({'INFO'}, "Environment layer info turned off for instance")
            else:
                obj["env_layer_info"] = True
                self.report({'INFO'}, "Environment layer info turned on for instance")
        else:
            # If object is not an instance, handle 'fin_env'
            if "fin_env" in obj:
                del obj["fin_env"]
                self.update_material_reflection(obj, False)
                self.report({'INFO'}, "Environment map turned off")
            else:
                obj["fin_env"] = True
                self.update_material_reflection(obj, True)
                self.report({'INFO'}, "Environment map turned on")

        return {'FINISHED'}

    def update_material_reflection(self, obj, enable_reflection):
        """Update material's reflection properties based on enable_reflection."""
        if obj.type == 'MESH' and obj.data.materials:
            for mat in obj.data.materials:
                if mat and mat.use_nodes:
                    for node in mat.node_tree.nodes:
                        if node.type == 'BSDF_PRINCIPLED':
                            node.inputs['Roughness'].default_value = 0.0 if enable_reflection else 0.5
                            node.inputs['Metallic'].default_value = 1.0 if enable_reflection else 0.0

class SetEnvironmentMapColor(bpy.types.Operator):
    bl_idname = "object.set_environment_map_color"
    bl_label = "Set EnvMap Color"

    def execute(self, context):
        props = context.scene.envmap_color_picker
        obj = context.active_object

        if obj is None:
            self.report({'WARNING'}, "No active object")
            return {'CANCELLED'}

        # Convert color to 0-255 range and store it
        color = tuple(int(c * 255) for c in props.envmap_color[:3])
        alpha = int((1 - props.envmap_color[3]) * 255)

        # Use your rvstruct.Color class to store the color and alpha
        env_color = rvstruct.Color(color=color, alpha=alpha)
        obj["fin_envcol"] = env_color.as_dict()

        # Update BSDF material color
        self.update_bsdf_color(obj, props.envmap_color)

        self.report({'INFO'}, "Environment map color set")
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=200)

    def update_bsdf_color(self, obj, color):
        """Update BSDF material color."""
        if obj.type == 'MESH' and obj.data.materials:
            for mat in obj.data.materials:
                if mat and mat.use_nodes:
                    for node in mat.node_tree.nodes:
                        if node.type == 'BSDF_PRINCIPLED':
                            # Set the Base Color of the BSDF node
                            node.inputs['Base Color'].default_value = [color[0], color[1], color[2], 1]
    
class ToggleHide(bpy.types.Operator):
    bl_idname = "object.toggle_hide"
    bl_label = "Toggle Hide"
    
    def execute(self, context):
        selected_object = context.active_object
        
        return {'FINISHED'}

class ToggleNoMirror(bpy.types.Operator):
    bl_idname = "object.toggle_no_mirror"
    bl_label = "Toggle No Mirror Mode"
    bl_description = "Toggle the 'Don't show in Mirror Mode' property"

    def execute(self, context):
        obj = context.object
        if obj and obj.type == 'MESH' and obj.get("is_instance", False):
            obj.revolt.fin_no_mirror = not obj.revolt.fin_no_mirror
        return {'FINISHED'}

class ToggleNoLights(bpy.types.Operator):
    bl_idname = "object.toggle_no_lights"
    bl_label = "Is Affected by Light"
    bl_description = "Toggle the 'Is affected by Light' property"

    def execute(self, context):
        obj = context.object
        if obj and obj.type == 'MESH' and obj.get("is_instance", False):
            obj.revolt.fin_no_lights = not obj.revolt.fin_no_lights
        return {'FINISHED'}

def menu_func(self, context):
    layout = self.layout
    obj = context.object

    if obj and obj.type == 'MESH' and obj.get("is_instance", False):
        layout.operator(ToggleNoLightsOperator.bl_idname)
        
class ToggleNoCameraCollision(bpy.types.Operator):
    bl_idname = "object.toggle_no_cam_coll"
    bl_label = "No Camera Collision"
    bl_description = "Toggle the 'No Camera Collision' property"

    def execute(self, context):
        obj = context.object
        if obj and "instance" in obj.name.lower():
            obj.revolt.fin_no_cam_coll = not obj.revolt.fin_no_cam_coll
        return {'FINISHED'}
    
class ToggleNoObjectCollision(bpy.types.Operator):
    bl_idname = "object.toggle_no_obj_coll"
    bl_label = "No Object Collision"
    bl_description = "Toggle the 'No Object Collision' property"

    def execute(self, context):
        obj = context.object
        if obj and "instance" in obj.name.lower():
            obj.revolt.fin_no_obj_coll = not obj.revolt.fin_no_obj_coll
        return {'FINISHED'}
    
class SetInstancePriority(bpy.types.Operator):
    bl_idname = "object.set_instance_priority"
    bl_label = "Set Instance Priority"
    bl_description = "Set the priority for the instance"

    fin_priority: bpy.props.IntProperty(
        name="Priority",
        default=1,
        description="Priority for instance. Instance will always be shown if set to 1."
    )

    def execute(self, context):
        obj = context.object
        if obj and "instance" in obj.name.lower():
            obj.revolt.fin_priority = self.fin_priority
        return {'FINISHED'}
    
class SetLoDBias(bpy.types.Operator):
    bl_idname = "object.set_lod_bias"
    bl_label = "Set LoD Bias (Unused)"
    bl_description = "Set the LoD Bias (Unused)"

    fin_lod_bias: bpy.props.IntProperty(
        name="LoD Bias",
        default=1024,
        description="Unused"
    )

    def execute(self, context):
        obj = context.object
        if obj and "instance" in obj.name.lower():
            obj.revolt.fin_lod_bias = self.fin_lod_bias
        return {'FINISHED'}
    
class ToggleMirrorPlane(bpy.types.Operator):
    bl_idname = "object.toggle_mirror_plane"
    bl_label = "Toggle Mirror Plane"
    bl_description = "Toggle Mirror Plane status for the selected object"

    def execute(self, context):
        # Check if there is an active object
        if context.active_object:
            obj = context.active_object

            # Check if the object is already a mirror plane
            is_mirror_plane = any(mp.object_name == obj.name for mp in rim_instance.mirror_planes)

            if not is_mirror_plane:
                # Create a new MirrorPlane instance and add it to the RIM instance
                new_mirror_plane = MirrorPlane()
                # Set properties of the mirror plane based on the object
                # Example: new_mirror_plane.object_name = obj.name
                rim_instance.mirror_planes.append(new_mirror_plane)
                rim_instance.num_mirror_planes += 1

                # Optionally set a custom property on the object for UI indication
                obj["is_mirror_plane"] = True

                self.report({'INFO'}, f"{obj.name} set as a new mirror plane")
            else:
                # Logic if you want to toggle or update the mirror plane status
                # Example: remove or update the mirror plane in rim_instance
                # Update or remove the custom property
                obj["is_mirror_plane"] = not obj.get("is_mirror_plane", False)

                self.report({'INFO'}, f"{obj.name} mirror plane status updated")

        else:
            self.report({'WARNING'}, "No active object selected")

        return {'FINISHED'}