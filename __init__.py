"""
Name:    init
Purpose: Init file for the Blender Add-On

Description:
Marv's Add-On for Re-Volt with Theman's update 
"""

import bpy
import bmesh
from bpy.app.handlers import persistent
from bpy.props import (
    BoolProperty,
    BoolVectorProperty,
    EnumProperty,
    FloatProperty,
    IntProperty,
    StringProperty,
    CollectionProperty,
    IntVectorProperty,
    FloatVectorProperty,
    PointerProperty
)
import importlib

# Importing modules from the add-on's package
from . import (
    carinfo,
    common,
    fin_in,
    fin_out,
    fob_in,
    fob_out,
    fob_subtypes,
    hul_in,
    hul_out,
    img_in,
    layers,
    m_in,
    m_out,
    ncp_in,
    ncp_out,
    operators,
    parameters_in,
    parameters_out_redux,
    prm_in,
    prm_in_for_fin,
    prm_in_for_w,
    prm_out,
    prm_out_for_fin,
    rim_in,
    rim_out,
    rvstruct,
    taz_in,
    taz_out,
    tri_in,
    tri_out,
    texanim,
    tools,
    w_in,
    w_out,
)

from .ui import (
    faceprops,
    headers,
    instances,
    light,
    migpanel,
    objectpanel,
    settings,
    texanim,
    vertex,
    viewlayer_panel,
)

from .common import DialogOperator, TEX_ANIM_MAX, MAX_MODEL_SLOTS
from .common import TEX_PAGES_MAX, FACE_DOUBLE, FACE_TRANSLUCENT, FACE_MIRROR, FACE_TRANSL_TYPE, FACE_TEXANIM, FACE_NOENV, FACE_ENV, FACE_CLOTH
from .common import FACE_SKIP, NCP_DOUBLE, NCP_NO_SKID, NCP_OIL, NCP_NON_PLANAR, NCP_OBJECT_ONLY, NCP_CAMERA_ONLY, NCP_NOCOLL, MATERIALS
from .fob_subtypes import OBJECT_TYPE_NAMES
from .layers import select_ncp_material, get_face_material, set_face_material, set_face_texture, get_face_texture, update_envmapping
from .layers import update_no_envmapping, set_face_ncp_property, get_face_ncp_property, get_face_env, set_face_env, update_face_env, get_fin_envcol, set_fin_envcol
from .layers import get_face_property, set_face_property, update_fin_envcol, set_rgb, get_rgb, update_fin_col, get_alpha_items
from .layers import update_fin_env, update_rgb, update_no_envmapping, update_envmapping, remove_env_material
from .operators import CopyAndRemoveAxles, ImportRV, ExportRV, ExportExtension, RVIO_OT_ReadCarParameters, RVIO_OT_SelectRevoltDirectory, ButtonReExport
from .operators import VertexAndAlphaLayer, VertexColorRemove, SetVertexColor, BakeShadow, BakeVertex, BatchBakeVertexToEnv, BakeVertexToRGBModelColor
from .operators import SetVertexAlpha, SetFaceTextureNumber, MFileExtension, TexturePrefixPrompt, SetFaceTextureDropdown, SetLevelTexturePrefix
from .operators import ButtonRenameAllObjects, SelectByName, SelectByData, MaterialAssignmentAuto, MaterialAssignment, MaterialAssignmentImportExport
from .operators import TextureAssigner, SetInstanceProperty, RemoveInstanceProperty, LaunchRV, TexturesSave, TexturesRename, ClearExtraAssignments
from .operators import CopyAerialParams, AxleMessageBox, ConfirmLoadOriginalAxle, CopyAndRemoveAxles, SpringMessageBox, ConfirmLoadOriginalSpring
from .operators import CopyAndRemoveSprings, PinMessageBox, ConfirmLoadOriginalPin, CopyAndRemovePins, CopyWheelParams, CreateVisibox
from .operators import ButtonZoneHide, AddTrackZone, ReverseTrackZone, ButtonTriggerHide, CreateTrigger, MarkAsModel, CreateFobObject
from .operators import DuplicateFobObject, DuplicateTrigger, CopyTrigger, PasteTrigger, SetBCubeMeshIndices, ButtonHullGenerate, ButtonHullSphere
from .operators import ButtonCopyUvToFrame, ButtonCopyFrameToUv, PreviewNextFrame, PreviewPrevFrame, TexAnimTransform, TexAnimGrid, CarAutoShader
from .operators import ToggleVisiboxVisibility, ToggleFOBVisibility, FindSpecialFile, BakeVertexBatch
from .operators import menu_func_import, menu_func_export
from .texanim import update_ta_max_frames, update_ta_current_slot, update_ta_current_frame, update_ta_current_frame_uv
from .texanim import update_ta_current_frame_delay, update_ta_current_frame_tex, update_ta_max_slots
from .tools import get_trigger_type_items, get_trigger_type, set_trigger_type, get_low_flag_items, get_low_flag, set_low_flag, get_high_flag_items
from .tools import get_high_flag, set_high_flag
from .ui.faceprops import RVIO_PT_RevoltFacePropertiesPanel
from .ui.headers import RVIO_PT_RevoltIOToolPanel
from .ui.instances import RVIO_PT_RevoltInstancesPanel
from .ui.light import RVIO_PT_RevoltLightPanel
from .ui.texanim import RVIO_PT_AnimModesPanel
from .ui.objectpanel import RVIO_PT_RevoltObjectPanel
from .ui.settings import RVIO_PT_RevoltSettingsPanel, update_actual_split_size, get_actual_split_size
from .ui.vertex import RVIO_PT_VertexPanel
from .ui.migpanel import RVIO_PT_RevoltMIGPanel
from .ui.viewlayer_panel import RVIO_PT_RevoltViewLayerPanel

bl_info = {
"name": "Re-Volt",
"author": "Marvin Thiel & Theman",
"version": (20, 25, 91),
"blender": (4, 5, 1),
"location": "File > Import-Export",
"description": "Import and export Re-Volt file formats.",
"wiki_url": "https://www.breathingstatue.com/blender-plugin",
"tracker_url": "https://github.com/breathingstatue/blender-plugin/issues",
"support": 'COMMUNITY',
"category": "Import-Export"
}

bmesh_dic = {}  # This global dictionary will store your BMesh objects

@persistent
def edit_object_change_handler(scene):
    """Makes the edit mode bmesh available for use in GUI panels."""
    obj = bpy.context.view_layer.objects.active

    # If no active object or the active object is not a mesh, clear the dictionary and return
    if obj is None or obj.type != 'MESH':
        bmesh_dic.clear()
        return

    # Handle the case where the object is in edit mode
    if obj.mode == 'EDIT':
        try:
            # Set default only if obj.name is not in bmesh_dic, to avoid creating a new bmesh each time
            if obj.name not in bmesh_dic:
                bmesh_dic[obj.name] = bmesh.from_edit_mesh(obj.data)
        except KeyError as e:
            print(f"Error accessing BMesh for object: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")
    else:
        # If the object is not in edit mode, clear the dictionary
        bmesh_dic.clear()

def register():
    
    #Register Custom Properties
    
    bpy.types.Scene.envidx = bpy.props.IntProperty(
        name="envidx",
        default=0,
        min=0,
        description="Current env color index for importing. Internal only"
    )
    
    bpy.types.Object.is_instance = bpy.props.BoolProperty(
        name = "Is Instance",
        default = False,
        description = "Object is an instanced mesh."
    )
    
    bpy.types.Object.fin_env = bpy.props.BoolProperty(
        name = "Use Environment Map",
        default = True,
        description = "If set on, instance is EnvMapped.",
        update=update_fin_env
    )
    
    bpy.types.Object.fin_no_mirror = bpy.props.BoolProperty(
        name = "Don't show in Mirror Mode",
        default = False,
        description = "If set on, instance doesn't show up in Mirror Mode."
    )
    
    bpy.types.Object.fin_no_lights = bpy.props.BoolProperty(
        name = "Is affected by Light",
        default = False,
        description = "If set on, instance is not affected by Light."
    )
    
    bpy.types.Object.fin_no_cam_coll = bpy.props.BoolProperty(
        name = "No Camera Collision",
        default = False,
        description = "If set on, instace has no camera collision."
    )
    
    bpy.types.Object.fin_no_obj_coll = bpy.props.BoolProperty(
        name = "No Object Collision",
        default = False,
        description = "If set on, instance has no object collision."
    )

    bpy.types.Object.fin_col = bpy.props.FloatVectorProperty(
        name="Model Color",
        subtype='COLOR',
        size=3,
        min=0.0,
        max=1.0,
        default=(0.5, 0.5, 0.5),
        description="Model RGB color to be used",
        get=get_rgb,
        set=set_rgb,
        update=update_fin_col
    )
    
    bpy.types.Object.fin_envcol = bpy.props.FloatVectorProperty(
        name="Env Color",
        subtype='COLOR',
        default=(1.0, 1.0, 1.0, 1.0),
        size=4,
        min=0.0, max=1.0,
        description="Instance EnvMap Color",
        get=get_fin_envcol,
        set=set_fin_envcol,
        update=update_fin_envcol
    )
    
    bpy.types.Object.fin_model_rgb = bpy.props.BoolProperty(
        name="Use Model Color",
        description="Toggle to use the model's color",
        default=False,
        update=update_rgb
    )
    
    bpy.types.Object.fin_hide = bpy.props.BoolProperty(
        name="Hide",
        description="Toggle to hide the object in a specific context",
        default=False
    )
    
    bpy.types.Object.fin_priority = bpy.props.IntProperty(
        name="Priority",
        description="Priority for instance. Instance will always be shown if set to 1, hidden if 0.",
        default=1,
        min=0,
        max=1
    )
    
    bpy.types.Object.fin_lod_bias = bpy.props.IntProperty(
        name="LoD Bias",
        description="Level of Detail Bias",
        default=1024,
        min=1,
        max=8192,
        soft_min=1,
        soft_max=8192,
        subtype='UNSIGNED'
    )
    
    bpy.types.Scene.w_parent_meshes = bpy.props.BoolProperty(
        name="Toggle Parent Meshes",
        description="Enable or disable parent meshes",
        default=False
    )
    
    bpy.types.Scene.w_import_bound_boxes = bpy.props.BoolProperty(
        name="Toggle Import Bound Boxes",
        description="Enable or disable import of bounding boxes",
        default=False
    )
    
    bpy.types.Scene.w_import_cubes = bpy.props.BoolProperty(
        name="Import Cubes",
        default=False
    )
    
    bpy.types.Scene.w_import_big_cubes = bpy.props.BoolProperty(
        name="Import Big Cubes",
        default=False
    )

    bpy.types.Scene.triangulate_ngons = bpy.props.BoolProperty(
        name="Triangulate Ngons",
        description="Enable or disable ngon triangulation",
        default=True
    )
  
    bpy.types.Scene.use_tex_num = bpy.props.BoolProperty(
        name = "Use Number for Texture",
        default = False,
        description = "Uses the texture number from the texture layer "
                      "accessible in the tool shelf in Edit mode.\n"
                      "Otherwise, it uses the texture from the texture file"
    )

    bpy.types.Scene.apply_scale = bpy.props.BoolProperty(
        name="Apply Scale on Export",
        default=True,
        description="Apply object scale during export"
    )
    
    bpy.types.Scene.apply_rotation = bpy.props.BoolProperty(
        name="Apply Rotation on Export",
        default=True,
        description="Apply object rotation during export. (disable for axle/pin/spring)"
    )
    
    bpy.types.Scene.apply_translation = bpy.props.BoolProperty(
        name = "Apply Translation",
        default = False,
        description = "Applies the object location on export. Should be disabled for single/instance ncp files"
    )
    
    bpy.types.Scene.export_camber = bpy.props.BoolProperty(
        name="Export Camber",
        description="Include camber values in the parameters.txt export",
        default=False
    )
    
    bpy.types.Object.bcube_mesh_indices = bpy.props.StringProperty(
        name="Mesh Indices",
        default="",
        description="Names of child meshes"
    )    

    bpy.types.Object.is_mirror_plane = bpy.props.BoolProperty(
        name = "Is Mirror Plane",
        default = False,
        description = "Object is a mirror plane (.rim)"
    )
    
    bpy.types.Scene.rvgl_dir = bpy.props.StringProperty(
        name="RVGL Directory",
        subtype='DIR_PATH',
        description="Directory where RVGL is located"
    )
    
    bpy.types.Scene.ncp_export_selected = bpy.props.BoolProperty(
        name = "Only export selected",
        default = False,
        description = "Only exports the selected objects"
    )
    
    bpy.types.Scene.ncp_export_collgrid = bpy.props.BoolProperty(
        name = "Export Collision Grid (.w)",
        default = True,
        description = "Export a collision grid to the .ncp file:\n\n"
                      "Enable this if you want to export a level (.w) "
                      ".ncp file"
    )

    bpy.types.Scene.ncp_collgrid_size = bpy.props.IntProperty(
        name="NCP Grid Size",
        default=1024,
        min=512,
        max=8192,
        description="Size of the lookup grid"
    )

    bpy.types.Scene.last_exported_filepath = bpy.props.StringProperty(
        name="Last Exported Filepath",
        description="Filepath used for the last export",
        default="",
        subtype='FILE_PATH'
    )

    bpy.types.Scene.last_exported_format = bpy.props.StringProperty(
        name="Last Exported Format",
        description="Format of the last exported file",
        default="",
    )
    
    bpy.types.Object.is_bcube = bpy.props.BoolProperty(
        name="Object is a BigCube",
        description="Makes BigCube properties visible for this object",
        default=False
    )

    bpy.types.Object.is_cube = bpy.props.BoolProperty(
        name="Object is a Cube",
        description="Makes Cube properties visible for this object",
        default=False
    )

    bpy.types.Object.is_bbox = bpy.props.BoolProperty(
        name="Object is a Boundary Box",
        description="Makes BoundBox properties visible for this object",
        default=False
    )
    
    bpy.types.Object.ignore_ncp = bpy.props.BoolProperty(
        name="Ignore Collision (.ncp)",
        description="Ignores the object when exporting to NCP",
        default=False
    )
    
    bpy.types.Scene.shadow_quality = bpy.props.EnumProperty(
        name = "Quality",
        items = [
            ('32', "32 Samples", "Render with 32 samples"),
            ('64', "64 Samples", "Render with 64 samples"),
            ('128', "128 Samples", "Render with 128 samples"),
            ('256', "256 Samples", "Render with 256 samples"),
            ('512', "512 Samples", "Render with 512 samples"),
        ],
        default = '128',
        description = "The amount of samples the shadow is rendered with "
                      "(number of samples taken extra)"
    )
    
    bpy.types.Scene.shadow_resolution = bpy.props.EnumProperty(
        name = "Resolution",
        description = "The resolution of the shadow.bmp",
        items = [
            ('128', "128x128", "128x128 Resolution"),
            ('256', "256x256", "256x256 Resolution"),
            ('512', "512x512", "512x512 Resolution")
        ],
        default = '128'
    )

    bpy.types.Scene.shadow_strength = bpy.props.IntProperty(
        name="Shadow Strength",
        description="Controls shadow boldness (1 = thin, 7 = bold)",
        default=4,
        min=1,
        max=7
    )
    
    bpy.types.Scene.shadow_table = bpy.props.StringProperty(
        name = "Shadowtable",
        default = "",
        description = "Shadow coordinates for use in parameters.txt of cars.\n"
                      "Click to select all, then CTRL C to copy"
    )
    
    bpy.types.Scene.texture_animations = bpy.props.StringProperty(
        name="Texture Animations",
        default="[]",
        description="Storage for Texture animations. Should not be changed by hand"
    )
    
    bpy.types.Scene.ta_max_frames = bpy.props.IntProperty(
        name = "Frames",
        min = 2,
        default = 2,
        update = update_ta_max_frames,
        description = "Total number of frames of the current slot. "
                      "All higher frames will be ignored on export"
    )
    
    bpy.types.Scene.ta_max_slots = bpy.props.IntProperty(
        name = "Slots",
        min = 0,
        max = TEX_ANIM_MAX,
        default = 0,
        update = update_ta_max_slots,
        description = "Total number of texture animation slots. "
                      "All higher slots will be ignored on export"
    )
    
    bpy.types.Scene.ta_frame_start = bpy.props.IntProperty(
        name = "Start Frame",
        min = 0,
        max = 32766,
        default = 0,
        description = "Start frame of the animation"
    )
    
    bpy.types.Scene.ta_frame_end = bpy.props.IntProperty(
        name = "End Frame",
        min = 0,
        max = 32766,
        default = 2,
        description = "End frame of the animation",
    )

    bpy.types.Scene.ta_texture = bpy.props.IntProperty(
        name = "Texture",
        default = 0,
        min = -1,
        max = TEX_PAGES_MAX-1,
        description = "The texture of every frame"
    )
    
    bpy.types.Scene.ta_delay = bpy.props.FloatProperty(
        name="Frame Duration",
        description="Duration of every frame",
        default=0.02,
        min=0.0,
        max=2.0
    )
    
    bpy.types.Scene.ta_current_slot = bpy.props.IntProperty(
        name = "Animation",
        default = 0,
        min = 0,
        max = TEX_ANIM_MAX-1,
        update = update_ta_current_slot,
        description = "Texture animation slot"
    )
    
    bpy.types.Scene.ta_current_frame = bpy.props.IntProperty(
        name = "Frame",
        default = 0,
        min = 0,
        update = update_ta_current_frame,
        description = "Current frame"
    )
    
    bpy.types.Scene.ta_current_frame_tex = bpy.props.IntProperty(
        name = "Texture",
        default = 0,
        min = -1,
        max = TEX_PAGES_MAX-1,
        update = update_ta_current_frame_tex,
        description = "Texture of the current frame"
    )
    
    bpy.types.Scene.ta_current_frame_delay = bpy.props.FloatProperty(
        name = "Duration",
        default = 0.01,
        min = 0,
        update = update_ta_current_frame_delay,
        description = "Duration of the current frame"
    )
    
    bpy.types.Scene.ta_current_frame_uv0 = bpy.props.FloatVectorProperty(
        name = "UV 0",
        size = 2,
        default = (0, 0),
        #min = 0.0,
        #max = 1.0,
        update = lambda self, context: update_ta_current_frame_uv(context, 0),
        description = "UV coordinate of the first vertex"
    )
    
    bpy.types.Scene.ta_current_frame_uv1 = bpy.props.FloatVectorProperty(
        name = "UV 1",
        size = 2,
        default = (0, 0),
        #min = 0.0,
        #max = 1.0,
        update = lambda self, context: update_ta_current_frame_uv(context, 1),
        description = "UV coordinate of the second vertex"
    )
    
    bpy.types.Scene.ta_current_frame_uv2 = bpy.props.FloatVectorProperty(
        name = "UV 2",
        size = 2,
        default = (0, 0),
        #min = 0.0,
        #max = 1.0,
        update = lambda self, context: update_ta_current_frame_uv(context, 2),
        description = "UV coordinate of the third vertex"
    )
    
    bpy.types.Scene.ta_current_frame_uv3 = bpy.props.FloatVectorProperty(
        name = "UV 3",
        size = 2,
        default = (0, 0),
        #min = 0.0,
        #max = 1.0,
        update = lambda self, context: update_ta_current_frame_uv(context, 3),
        description = "UV coordinate of the fourth vertex"
    )
    
    bpy.types.Scene.grid_x = bpy.props.IntProperty(
        name="X Resolution",
        min=1,
        default=2,
        max= 256,
        description="Amount of frames along the X axis"
    )
    bpy.types.Scene.grid_y = bpy.props.IntProperty(
        name="Y Resolution",
        min=1,
        default=2,
        max = 256,
        description="Amount of frames along the Y axis"
    )    

    bpy.types.Mesh.select_material = bpy.props.EnumProperty(
        name = "Select Material",
        items = MATERIALS,
        update = select_ncp_material,
        description = "Selects all faces with the selected material"
    )
    
    bpy.types.Mesh.face_material = bpy.props.EnumProperty(
        name = "Material",
        items = MATERIALS,
        get = get_face_material,
        set = set_face_material,
        description = "Surface Material"
    )
    
    bpy.types.Mesh.face_texture = bpy.props.IntProperty(
        name="Texture",
        get=get_face_texture,
        set=set_face_texture,
        description="Texture page number:\n-1 is none,\n0 is texture page A, 1 is B, etc.",
        min=-1,
        max=63
    )
    
    bpy.types.Scene.material_choice = bpy.props.EnumProperty(
        name="Layer",
        items=[
            ('TEX_VC', "Tex+VC+Alpha", "Assign Texture + Vertex Colour + Alpha"),
            ('UV_TEX', "Texture", "Assign UV Texture"),
            ('COL', "Vertex Color", "Assign Color Material"),
            ('ALPHA', "Vertex Alpha", "Assign Vertex Alpha Material"),
            ('ENV', "EnvMap", "Assign Env / EnvAlpha Material"),
            ('RGB', "Model Color (Instance)", "Assign RGB Model Color"),
            ('NCP', "NCP Material (Preview)", "Assign NCP Preview")
        ],
    )
    
    bpy.types.Mesh.face_double_sided = bpy.props.BoolProperty(
        name = "Double sided",
        description = "The polygon will be visible from both sides in-game",
        get=lambda self: bool(get_face_property(self, FACE_DOUBLE)),
        set=lambda self, value: set_face_property(self, value, FACE_DOUBLE)
    )
    
    bpy.types.Mesh.face_translucent = bpy.props.BoolProperty(
        name = "Translucent",
        description = "Renders the polyon transparent\n(takes transparency "
                      "from the \"Alpha\" vertex color layer or the alpha "
                      "layer of the texture",
        get=lambda self: bool(get_face_property(self, FACE_TRANSLUCENT)),
        set=lambda self, value: set_face_property(self, value, FACE_TRANSLUCENT)
    )
    
    bpy.types.Mesh.face_mirror = bpy.props.BoolProperty(
        name = "Mirror",
        description = "This polygon covers a mirror area. (?)",
        get=lambda self: bool(get_face_property(self, FACE_MIRROR)),
        set=lambda self, value: set_face_property(self, value, FACE_MIRROR)
    )
    
    bpy.types.Mesh.face_additive = bpy.props.BoolProperty(
        name = "Additive blending",
        description = "Renders the polygon with additive blending (black "
                      "becomes transparent, bright colors are added to colors "
                      "beneath)",
        get=lambda self: bool(get_face_property(self, FACE_TRANSL_TYPE)),
        set=lambda self, value: set_face_property(self, value, FACE_TRANSL_TYPE)
    )
    
    bpy.types.Mesh.face_texture_animation = bpy.props.BoolProperty(
        name = "Animated",
        description = "Uses texture animation for this poly (.w only)",
        get=lambda self: bool(get_face_property(self, FACE_TEXANIM)),
        set=lambda self, value: set_face_property(self, value, FACE_TEXANIM)
    )
    
    bpy.types.Mesh.face_no_envmapping = bpy.props.BoolProperty(
        name = "No EnvMap (.prm)",
        description = "Disables the environment map for this poly (.prm only)",
        get=lambda self: bool(get_face_property(self, FACE_NOENV)),
        set=lambda self, value: set_face_property(self, value, FACE_NOENV),
        update=update_no_envmapping
    )
    
    bpy.types.Mesh.face_envmapping = bpy.props.BoolProperty(
        name = "EnvMapping",
        description = "Enables the environment map for this poly (.w and .m files)",
        get=lambda self: bool(get_face_property(self, FACE_ENV)),
        set=lambda self, value: set_face_property(self, value, FACE_ENV),
        update=update_envmapping
    )
    
    bpy.types.Mesh.face_cloth = bpy.props.BoolProperty(
        name = "Cloth effect (.prm)",
        description = "Enables the cloth effect used on the Mystery car",
        get=lambda self: bool(get_face_property(self, FACE_CLOTH)),
        set=lambda self, value: set_face_property(self, value, FACE_CLOTH)
    )
    
    bpy.types.Mesh.face_skip = bpy.props.BoolProperty(
        name = "Do not export",
        description = "Skips the polygon when exporting (not Re-Volt related)",
        get=lambda self: bool(get_face_property(self, FACE_SKIP)),
        set=lambda self, value: set_face_property(self, value, FACE_SKIP)
    )
    
    bpy.types.Mesh.face_env = bpy.props.FloatVectorProperty(
        name="Environment Color",
        subtype="COLOR",
        size=4,
        min=0.0,
        max=1.0,
        default=(1.0, 1.0, 1.0, 1.0),
        description="Color of the environment map for World meshes",
        get=get_face_env,
        set=set_face_env,
        update=update_face_env
    )
    
    bpy.types.Mesh.face_ncp_double = bpy.props.BoolProperty(
        name = "Double-sided",
        description="Enables double-sided collision",
        get=lambda self: bool(get_face_ncp_property(self, NCP_DOUBLE)),
        set=lambda self, value: set_face_ncp_property(self, value, NCP_DOUBLE)
    )
    
    bpy.types.Mesh.face_ncp_object_only = bpy.props.BoolProperty(
        name = "Object Only",
        description="Enable collision for objects only (ignores camera)",
        get=lambda self: bool(get_face_ncp_property(self, NCP_OBJECT_ONLY)),
        set=lambda self, value: set_face_ncp_property(self, value, NCP_OBJECT_ONLY)
    )
    
    bpy.types.Mesh.face_ncp_camera_only = bpy.props.BoolProperty(
        name = "Camera Only",
        description="Enable collision for camera only",
        get=lambda self: bool(get_face_ncp_property(self, NCP_CAMERA_ONLY)),
        set=lambda self, value: set_face_ncp_property(self, value, NCP_CAMERA_ONLY)
    )
    
    bpy.types.Mesh.face_ncp_non_planar = bpy.props.BoolProperty(
        name = "Non-planar",
        description="Face is non-planar",
        get=lambda self: bool(get_face_ncp_property(self, NCP_NON_PLANAR)),
        set=lambda self, value: set_face_ncp_property(self, value, NCP_NON_PLANAR)
    )
    
    bpy.types.Mesh.face_ncp_no_skid = bpy.props.BoolProperty(
        name = "No Skid Marks",
        description="Disable skid marks",
        get=lambda self: bool(get_face_ncp_property(self, NCP_NO_SKID)),
        set=lambda self, value: set_face_ncp_property(self, value, NCP_NO_SKID)
    )
    
    bpy.types.Mesh.face_ncp_oil = bpy.props.BoolProperty(
        name = "Oil",
        description="Ground is oil",
        get=lambda self: bool(get_face_ncp_property(self, NCP_OIL)),
        set=lambda self, value: set_face_ncp_property(self, value, NCP_OIL)
    )
    
    bpy.types.Mesh.face_ncp_nocoll = bpy.props.BoolProperty(
        name = "No Collision",
        description="Face will be ignored when exporting",
        get=lambda self: bool(get_face_ncp_property(self, NCP_NOCOLL)),
        set=lambda self, value: set_face_ncp_property(self, value, NCP_NOCOLL)
    )    
    
    bpy.types.Scene.vertex_color_picker = bpy.props.FloatVectorProperty(
        name="Vertex Color Picker",
        subtype='COLOR',
        size=3,  # Only RGB components
        min=0.0,
        max=1.0,
        default=(1.0, 1.0, 1.0),
        description="Color picker for setting vertex colors"
    )

    bpy.types.Scene.vertex_alpha = bpy.props.FloatProperty(
        name="Vertex Alpha",
        description="Set the alpha value for vertex colors",
        default=1.0,
        min=0.0,
        max=1.0,
        subtype='FACTOR'
    )
    
    bpy.types.Scene.vertex_alpha_percentage = bpy.props.EnumProperty(
        name="Alpha Percentage",
        description="Choose an alpha percentage for the vertex color layer",
        items=get_alpha_items(),
        default='100'
    )
    
    bpy.types.Scene.car_shader_color = bpy.props.FloatVectorProperty(
        name="Shader Base Color",
        subtype='COLOR',
        min=0.0, max=1.0,
        default=(1.0, 1.0, 1.0),
        description="Base color used for vertex shading"
    )

    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)
    
    bpy.types.Scene.is_hull_sphere = bpy.props.BoolProperty(
        name="Is Interior Sphere",
        description="Enable Hull Sphere creation",
        default=False
    )
    
    bpy.types.Scene.is_hull_convex = bpy.props.BoolProperty(
        name="Is Hull Convex",
        description="Enable Convex Hull creation",
        default=False
    )
    
    bpy.types.Object.is_hull_sphere = bpy.props.BoolProperty(
        name="Is Hull Sphere",
        description="Marks object as hull sphere",
        default=False
    )
    
    bpy.types.Object.is_hull_convex = bpy.props.BoolProperty(
        name="Is Hull Convex",
        description="Marks object as hull convex",
        default=False
    )
    
    bpy.types.Scene.export_worldcut = bpy.props.BoolProperty(
        name="Export WorldCut",
        description="Export world as split meshes (.w)",
        default=False
    )

    bpy.types.Scene.split_size_faces = bpy.props.IntProperty(
        name="Split Size Faces",
        description="Number of faces per split",
        min=1,
        max=100,
        default=16,  # Set your default value
        update=update_actual_split_size  # Update actual_split_size when split_size_faces changes
    )

    bpy.types.Scene.actual_split_size = bpy.props.IntProperty(
        name="Actual Split Size",
        description="Calculated number of faces per split based on split_size_faces.",
        get=get_actual_split_size,
        options={'HIDDEN'}  # Hide this property in the UI as it will be displayed differently
    )

    bpy.types.Object.track_zone_id = bpy.props.IntProperty(
        name="Track Zone ID",
        description="ID of the Track Zone",
        default=0,
        min=0,
        max=1023
    )
    
    bpy.types.Object.is_track_zone = bpy.props.BoolProperty(
        name="Is Track Zone",
        description="Indicates if the object is a track zone",
        default=False
    )
    
    bpy.types.Object.is_trigger = bpy.props.BoolProperty(
        name="Is Trigger",
        description="Mark this object as a trigger",
        default=False
    )
    
    bpy.types.Scene.new_trigger_type = bpy.props.EnumProperty(
        name="New Trigger Type",
        description="Select the type of trigger to create",
        items=get_trigger_type_items
    )
    
    bpy.types.Object.trigger_type_enum = bpy.props.EnumProperty(
        name="Trigger Type",
        description="Select the trigger type",
        items=get_trigger_type_items,
        get=get_trigger_type,
        set=set_trigger_type
    )
    
    bpy.types.Object.low_flag_enum = bpy.props.EnumProperty(
        name="Low Flag",
        description="Select the low flag value",
        items=get_low_flag_items,
        get=get_low_flag,
        set=set_low_flag
    )

    bpy.types.Object.flag_low = bpy.props.IntProperty(
        name="Low Flag",
        description="Low Flag value for the trigger",
        default=0,
        min=0,
        max=1023
    )

    bpy.types.Object.flag_high = bpy.props.IntProperty(
        name="High Flag",
        description="Set the high flag value",
        default=0,
        min=0,
        max=63,
        get=get_high_flag,
        set=set_high_flag
    )
    
    bpy.types.Object.low_flag_slider = bpy.props.IntProperty(
        name="Low Flag",
        description="Set the low flag value",
        default=0,
        min=0,
        max=1023
    )
    
    bpy.types.Scene.copied_trigger_properties = bpy.props.PointerProperty(type=bpy.types.PropertyGroup)

    bpy.types.Object.is_fob_object = bpy.props.BoolProperty(
        name="Is FOB Object",
        description="Marks this object as a FOB object",
        default=False
    )
    
    bpy.types.Object.fob_type = bpy.props.IntProperty(name="Object ID")
    bpy.types.Object.fob_subtype_1 = bpy.props.IntProperty(name="Subtype 1")
    bpy.types.Object.fob_subtype_2 = bpy.props.IntProperty(name="Subtype 2")
    bpy.types.Object.fob_subtype_3 = bpy.props.IntProperty(name="Subtype 3")
    bpy.types.Object.fob_subtype_4 = bpy.props.IntProperty(name="Subtype 4")
    bpy.types.Object.fob_creation_index = bpy.props.IntProperty(name="Creation Index")

    bpy.types.Scene.selected_fob_object_id = bpy.props.EnumProperty(
        name="Select Object",
        description="Choose the type of object to create",
        items=[(str(k), f"{v} ({k})", "") for k, v in OBJECT_TYPE_NAMES.items()],
        default='0'
    )
    
    bpy.types.Scene.level_texture_base = bpy.props.StringProperty(
        name="Level Texture Base",
        description="Prefix used for level textures, like 'box', 'arena', etc.",
        default=""
    )
    
    bpy.types.Scene.default_texture_name = StringProperty(name="Default Texture Name")
    
    bpy.types.Scene.pending_import_filepath = bpy.props.StringProperty(name="Pending Import Filepath")
    
    bpy.types.Object.is_model = bpy.props.BoolProperty(
        name="Is Model (.m)",
        description="Marks the instance as referencing a .m (Model) file instead of .prm",
        default=False
    )
    
    bpy.types.Scene.selected_car_texture = bpy.props.StringProperty(
        name="Selected Car Texture",
        description="Fallback texture for car material assignment"
    )

    for i in range(MAX_MODEL_SLOTS):
        setattr(bpy.types.Scene, f"m_texture_path_{i}", bpy.props.StringProperty(subtype="FILE_PATH"))
        setattr(bpy.types.Scene, f"m_texture_mode_{i}", bpy.props.EnumProperty(
            items=[
                ("LEVEL_TEXTURES", "Level Textures", ""),
                ("TEXTURE_NAME", "Single Texture", ""),
                ("VERTEX_COLOR", "Vertex Color", "")
            ],
            name=f"Texture Mode {i}",
            default="VERTEX_COLOR"
        ))
        setattr(bpy.types.Scene, f"m_model_name_{i}", bpy.props.StringProperty())
        
    bpy.types.Scene.prompt_required = bpy.props.BoolProperty(default=False)
    
    bpy.types.Object.is_visibox = bpy.props.BoolProperty(
        name="Is Visibox",
        description="Marks this object as a Visibox",
        default=False
    )
    
    bpy.types.Object.visibox_type = EnumProperty(
        name="Type",
        description="Type of the visibox",
        items=[
            ('1', "Camera", "Camera visibility box"),
            ('2', "Cubes", "Cubes visibility box")
        ],
        default='1'
    )

    bpy.types.Object.visibox_id = IntProperty(
        name="ID",
        description="ID of the visibox (-128 to 127)",
        default=0,
        min=-128,
        max=127
    )
    
    bpy.types.Scene.visibox_create_type = bpy.props.EnumProperty(
        name="Visibox Type",
        description="Type of visibox to create",
        items=[
            ('1', "Camera", "Camera visibility box"),
            ('2', "Cubes", "Cubes visibility box")
        ],
        default='1'
    )

    bpy.types.Scene.visibox_create_id = bpy.props.IntProperty(
        name="Visibox ID",
        description="ID of visibox to create",
        min=-128,
        max=127,
        default=0
    )

    #Register Operators
    bpy.utils.register_class(DialogOperator)
    bpy.utils.register_class(ImportRV)
    bpy.utils.register_class(ExportRV)
    bpy.utils.register_class(RVIO_OT_ReadCarParameters)
    bpy.utils.register_class(ButtonReExport)
    bpy.utils.register_class(VertexAndAlphaLayer)
    bpy.utils.register_class(VertexColorRemove)
    bpy.utils.register_class(SetVertexColor)
    bpy.utils.register_class(ButtonRenameAllObjects)
    bpy.utils.register_class(SelectByName)
    bpy.utils.register_class(SelectByData)
    bpy.utils.register_class(SetInstanceProperty)
    bpy.utils.register_class(RemoveInstanceProperty)
    bpy.utils.register_class(LaunchRV)
    bpy.utils.register_class(TexturesSave)
    bpy.utils.register_class(TexturesRename)
    bpy.utils.register_class(ClearExtraAssignments)
    bpy.utils.register_class(MaterialAssignmentAuto)
    bpy.utils.register_class(MaterialAssignment)
    bpy.utils.register_class(MaterialAssignmentImportExport)
    bpy.utils.register_class(TextureAssigner)
    bpy.utils.register_class(CopyWheelParams)
    bpy.utils.register_class(CreateVisibox)
    bpy.utils.register_class(ExportExtension)
    bpy.utils.register_class(AxleMessageBox)
    bpy.utils.register_class(ConfirmLoadOriginalAxle)
    bpy.utils.register_class(CopyAndRemoveAxles)
    bpy.utils.register_class(SpringMessageBox)
    bpy.utils.register_class(ConfirmLoadOriginalSpring)
    bpy.utils.register_class(CopyAndRemoveSprings)
    bpy.utils.register_class(PinMessageBox)
    bpy.utils.register_class(ConfirmLoadOriginalPin)
    bpy.utils.register_class(CopyAndRemovePins)
    bpy.utils.register_class(CopyAerialParams)
    bpy.utils.register_class(ButtonHullGenerate)  
    bpy.utils.register_class(BakeShadow)
    bpy.utils.register_class(BakeVertex)
    bpy.utils.register_class(BatchBakeVertexToEnv)
    bpy.utils.register_class(BakeVertexToRGBModelColor)
    bpy.utils.register_class(ButtonHullSphere)
    bpy.utils.register_class(ButtonCopyUvToFrame)
    bpy.utils.register_class(ButtonCopyFrameToUv)
    bpy.utils.register_class(PreviewNextFrame)
    bpy.utils.register_class(PreviewPrevFrame)
    bpy.utils.register_class(TexAnimTransform)
    bpy.utils.register_class(TexAnimGrid)
    bpy.utils.register_class(CarAutoShader)
    bpy.utils.register_class(ToggleVisiboxVisibility)
    bpy.utils.register_class(ToggleFOBVisibility)
    bpy.utils.register_class(FindSpecialFile)
    bpy.utils.register_class(BakeVertexBatch)
    bpy.utils.register_class(ButtonZoneHide)
    bpy.utils.register_class(AddTrackZone)
    bpy.utils.register_class(ReverseTrackZone)
    bpy.utils.register_class(ButtonTriggerHide)
    bpy.utils.register_class(CreateTrigger)
    bpy.utils.register_class(MarkAsModel)
    bpy.utils.register_class(CreateFobObject)
    bpy.utils.register_class(DuplicateFobObject)
    bpy.utils.register_class(DuplicateTrigger)
    bpy.utils.register_class(CopyTrigger)
    bpy.utils.register_class(PasteTrigger)
    bpy.utils.register_class(SetBCubeMeshIndices)
    bpy.utils.register_class(SetVertexAlpha)
    bpy.utils.register_class(SetFaceTextureNumber)
    bpy.utils.register_class(MFileExtension)
    bpy.utils.register_class(TexturePrefixPrompt)
    bpy.utils.register_class(SetFaceTextureDropdown)
    bpy.utils.register_class(SetLevelTexturePrefix)
    bpy.utils.register_class(RVIO_OT_SelectRevoltDirectory)
    
    # Register UI
    bpy.utils.register_class(RVIO_PT_RevoltFacePropertiesPanel)
    bpy.utils.register_class(RVIO_PT_RevoltIOToolPanel)
    bpy.utils.register_class(RVIO_PT_RevoltSettingsPanel)
    bpy.utils.register_class(RVIO_PT_AnimModesPanel)
    bpy.utils.register_class(RVIO_PT_VertexPanel)
    bpy.utils.register_class(RVIO_PT_RevoltMIGPanel)
    bpy.utils.register_class(RVIO_PT_RevoltInstancesPanel)
    bpy.utils.register_class(RVIO_PT_RevoltLightPanel)
    bpy.utils.register_class(RVIO_PT_RevoltObjectPanel)
    bpy.utils.register_class(RVIO_PT_RevoltViewLayerPanel)
    
    # UI and Handlers Registration
    bpy.app.handlers.depsgraph_update_pre.append(edit_object_change_handler)

def unregister():
    
    # UI and Handlers Unregistration
    bpy.app.handlers.depsgraph_update_pre.remove(edit_object_change_handler)
     
    # Unregister UI
    bpy.utils.unregister_class(RVIO_PT_RevoltViewLayerPanel)
    bpy.utils.unregister_class(RVIO_PT_RevoltObjectPanel)
    bpy.utils.unregister_class(RVIO_PT_RevoltLightPanel)
    bpy.utils.unregister_class(RVIO_PT_RevoltInstancesPanel)
    bpy.utils.unregister_class(RVIO_PT_RevoltMIGPanel)
    bpy.utils.unregister_class(RVIO_PT_VertexPanel)
    bpy.utils.unregister_class(RVIO_PT_AnimModesPanel)
    bpy.utils.unregister_class(RVIO_PT_RevoltSettingsPanel)
    bpy.utils.unregister_class(RVIO_PT_RevoltIOToolPanel)
    bpy.utils.unregister_class(RVIO_PT_RevoltFacePropertiesPanel)
    
    # Unregister Operators
    bpy.utils.unregister_class(RVIO_OT_SelectRevoltDirectory)
    bpy.utils.unregister_class(SetLevelTexturePrefix)
    bpy.utils.unregister_class(SetFaceTextureDropdown)
    bpy.utils.unregister_class(TexturePrefixPrompt)
    bpy.utils.unregister_class(MFileExtension)
    bpy.utils.unregister_class(SetFaceTextureNumber)
    bpy.utils.unregister_class(SetVertexAlpha)
    bpy.utils.unregister_class(SetBCubeMeshIndices)
    bpy.utils.unregister_class(PasteTrigger)
    bpy.utils.unregister_class(CopyTrigger)
    bpy.utils.unregister_class(DuplicateTrigger)
    bpy.utils.unregister_class(DuplicateFobObject)
    bpy.utils.unregister_class(CreateFobObject)
    bpy.utils.unregister_class(MarkAsModel)
    bpy.utils.unregister_class(CreateTrigger)
    bpy.utils.unregister_class(ButtonTriggerHide)
    bpy.utils.unregister_class(ReverseTrackZone)
    bpy.utils.unregister_class(AddTrackZone)
    bpy.utils.unregister_class(ButtonZoneHide)
    bpy.utils.unregister_class(BakeVertexBatch)
    bpy.utils.unregister_class(FindSpecialFile)
    bpy.utils.unregister_class(ToggleFOBVisibility)
    bpy.utils.unregister_class(ToggleVisiboxVisibility)
    bpy.utils.unregister_class(CarAutoShader)
    bpy.utils.unregister_class(TexAnimGrid)
    bpy.utils.unregister_class(TexAnimTransform)
    bpy.utils.unregister_class(PreviewPrevFrame)
    bpy.utils.unregister_class(PreviewNextFrame)
    bpy.utils.unregister_class(ButtonCopyFrameToUv)
    bpy.utils.unregister_class(ButtonCopyUvToFrame)
    bpy.utils.unregister_class(ButtonHullSphere)
    bpy.utils.unregister_class(BakeVertexToRGBModelColor)
    bpy.utils.unregister_class(BatchBakeVertexToEnv)
    bpy.utils.unregister_class(BakeVertex)
    bpy.utils.unregister_class(BakeShadow)
    bpy.utils.unregister_class(ButtonHullGenerate)
    bpy.utils.unregister_class(CopyAerialParams)
    bpy.utils.unregister_class(CopyAndRemovePins)
    bpy.utils.unregister_class(ConfirmLoadOriginalPin)
    bpy.utils.unregister_class(PinMessageBox)
    bpy.utils.unregister_class(CopyAndRemoveSprings)
    bpy.utils.unregister_class(ConfirmLoadOriginalSpring)
    bpy.utils.unregister_class(SpringMessageBox)
    bpy.utils.unregister_class(CopyAndRemoveAxles)
    bpy.utils.unregister_class(ConfirmLoadOriginalAxle)
    bpy.utils.unregister_class(AxleMessageBox)
    bpy.utils.unregister_class(ExportExtension)
    bpy.utils.unregister_class(CreateVisibox)
    bpy.utils.unregister_class(CopyWheelParams)
    bpy.utils.unregister_class(TextureAssigner)
    bpy.utils.unregister_class(MaterialAssignmentImportExport)
    bpy.utils.unregister_class(MaterialAssignment)
    bpy.utils.unregister_class(MaterialAssignmentAuto)
    bpy.utils.unregister_class(ClearExtraAssignments)
    bpy.utils.unregister_class(TexturesRename)
    bpy.utils.unregister_class(TexturesSave)
    bpy.utils.unregister_class(LaunchRV)
    bpy.utils.unregister_class(RemoveInstanceProperty)
    bpy.utils.unregister_class(SetInstanceProperty)
    bpy.utils.unregister_class(SelectByData)
    bpy.utils.unregister_class(SelectByName)
    bpy.utils.unregister_class(ButtonRenameAllObjects)
    bpy.utils.unregister_class(VertexAndAlphaLayer)
    bpy.utils.unregister_class(VertexColorRemove)
    bpy.utils.unregister_class(SetVertexColor)
    bpy.utils.unregister_class(ButtonReExport)
    bpy.utils.unregister_class(RVIO_OT_ReadCarParameters)
    bpy.utils.unregister_class(ExportRV)
    bpy.utils.unregister_class(ImportRV)
    bpy.utils.unregister_class(DialogOperator)
    
    del bpy.types.Scene.visibox_create_id
    del bpy.types.Scene.visibox_create_type
    del bpy.types.Object.visibox_id
    del bpy.types.Object.visibox_type
    del bpy.types.Object.is_visibox
    
    del bpy.types.Scene.prompt_required
    
    for i in range(MAX_MODEL_SLOTS):
        for key in (f"m_texture_path_{i}", f"m_texture_mode_{i}", f"m_model_name_{i}"):
            if key in bpy.types.Scene.__annotations__:
                del bpy.types.Scene.__annotations__[key]
    
    del bpy.types.Scene.selected_car_texture
    del bpy.types.Object.is_model
    del bpy.types.Scene.pending_import_filepath
    del bpy.types.Scene.default_texture_name
    del bpy.types.Scene.level_texture_base
    del bpy.types.Object.fob_creation_index
    del bpy.types.Object.fob_subtype_4
    del bpy.types.Object.fob_subtype_3
    del bpy.types.Object.fob_subtype_2
    del bpy.types.Object.fob_subtype_1
    del bpy.types.Object.fob_type
    del bpy.types.Object.is_fob_object
    del bpy.types.Scene.copied_trigger_properties
    del bpy.types.Object.low_flag_slider
    del bpy.types.Object.flag_high
    del bpy.types.Object.flag_low
    del bpy.types.Object.low_flag_enum
    del bpy.types.Object.trigger_type_enum
    del bpy.types.Scene.new_trigger_type
    del bpy.types.Object.is_trigger

    del bpy.types.Object.is_track_zone
    del bpy.types.Object.track_zone_id

    del bpy.types.Scene.split_size_faces
    del bpy.types.Scene.actual_split_size
    del bpy.types.Scene.export_worldcut
    
    del bpy.types.Object.is_hull_convex    
    del bpy.types.Object.is_hull_sphere
    del bpy.types.Scene.is_hull_convex
    del bpy.types.Scene.is_hull_sphere

    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)

    del bpy.types.Scene.car_shader_color
    del bpy.types.Scene.vertex_alpha_percentage
    del bpy.types.Scene.vertex_alpha
    del bpy.types.Scene.vertex_color_picker
    del bpy.types.Mesh.face_ncp_nocoll
    del bpy.types.Mesh.face_ncp_oil
    del bpy.types.Mesh.face_ncp_no_skid
    del bpy.types.Mesh.face_ncp_non_planar
    del bpy.types.Mesh.face_ncp_camera_only
    del bpy.types.Mesh.face_ncp_object_only
    del bpy.types.Mesh.face_ncp_double
    del bpy.types.Mesh.face_env
    del bpy.types.Mesh.face_skip
    del bpy.types.Mesh.face_cloth
    del bpy.types.Mesh.face_envmapping
    del bpy.types.Mesh.face_no_envmapping
    del bpy.types.Mesh.face_texture_animation
    del bpy.types.Mesh.face_additive
    del bpy.types.Mesh.face_mirror
    del bpy.types.Mesh.face_translucent
    del bpy.types.Mesh.face_double_sided
    del bpy.types.Scene.material_choice
    del bpy.types.Mesh.face_texture
    del bpy.types.Mesh.face_material
    del bpy.types.Mesh.select_material
    del bpy.types.Scene.grid_y
    del bpy.types.Scene.grid_x
    del bpy.types.Scene.ta_current_frame_uv3
    del bpy.types.Scene.ta_current_frame_uv2
    del bpy.types.Scene.ta_current_frame_uv1
    del bpy.types.Scene.ta_current_frame_uv0
    del bpy.types.Scene.ta_current_frame_delay
    del bpy.types.Scene.ta_current_frame_tex
    del bpy.types.Scene.ta_current_frame
    del bpy.types.Scene.ta_current_slot  
    del bpy.types.Scene.ta_delay
    del bpy.types.Scene.ta_texture
    del bpy.types.Scene.ta_frame_end
    del bpy.types.Scene.ta_frame_start
    del bpy.types.Scene.ta_max_frames
    del bpy.types.Scene.ta_max_slots
    del bpy.types.Scene.texture_animations
    del bpy.types.Scene.shadow_table
    del bpy.types.Scene.shadow_resolution
    del bpy.types.Scene.shadow_quality
    del bpy.types.Object.ignore_ncp
    del bpy.types.Object.is_bbox
    del bpy.types.Object.is_cube
    del bpy.types.Object.is_bcube
    del bpy.types.Scene.last_exported_format
    del bpy.types.Scene.last_exported_filepath    
    del bpy.types.Scene.ncp_export_selected
    del bpy.types.Scene.ncp_export_collgrid
    del bpy.types.Scene.ncp_collgrid_size
    del bpy.types.Scene.rvgl_dir
    del bpy.types.Object.is_mirror_plane
    del bpy.types.Object.bcube_mesh_indices
    del bpy.types.Scene.export_camber
    del bpy.types.Scene.apply_rotation
    del bpy.types.Scene.apply_scale
    del bpy.types.Scene.use_tex_num
    del bpy.types.Scene.triangulate_ngons
    
    del bpy.types.Scene.w_import_cubes
    del bpy.types.Scene.w_import_big_cubes
    del bpy.types.Scene.w_import_bound_boxes
    del bpy.types.Scene.w_parent_meshes
    
    del bpy.types.Object.fin_lod_bias
    del bpy.types.Object.fin_priority
    del bpy.types.Object.fin_hide
    del bpy.types.Object.fin_model_rgb
    del bpy.types.Object.fin_envcol
    del bpy.types.Object.fin_col
    del bpy.types.Scene.envidx
    del bpy.types.Object.is_instance
    del bpy.types.Object.fin_no_obj_coll
    del bpy.types.Object.fin_no_cam_coll
    del bpy.types.Object.fin_no_lights
    del bpy.types.Object.fin_no_mirror
    del bpy.types.Object.fin_env
    
if __name__ == "__main__":
    register()

print("Re-Volt addon successfully registered.")
