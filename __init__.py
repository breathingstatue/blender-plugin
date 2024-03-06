"""
Name:    init
Purpose: Init file for the Blender Add-On

Description:
Marv's Add-On for Re-Volt with Theman's Update 
"""

# Global debug flag
DEBUG_MODE = True

from tokenize import Ignore
from xml.dom.domreg import well_known_implementations
import bpy
import bmesh
import os
import os.path
import importlib
from bpy.app.handlers import persistent  # For the scene update handler
from bpy.app.handlers import load_post

# Importing modules from the add-on's package
from . import (
    carinfo,
    common,
    fin_in,
    fin_out,
    hul_in,
    hul_out,
    img_in,
    layers,
    ncp_in,
    ncp_out,
    operators,
    parameters_in,
    parameters_out,
    prm_in,
    prm_out,
    rim_in,
    rim_out,
    rvstruct,
    taz_in,
    taz_out,
    ta_csv_in,
    ta_csv_out,
    texanim,
    tools,
    w_in,
    w_out,
)

from .props import (
    props_mesh,
    props_obj,
    props_scene,
)

from .ui import (
    faceprops,
    headers,
    helpers,
    instances,
    light,
    objectpanel,
    settings,
    texanim,
    vertex,
    zone,
)

# Reloads potentially changed modules on reload (F8 in Blender)
importlib.reload(common)
importlib.reload(layers)
importlib.reload(operators)
importlib.reload(texanim)
importlib.reload(tools)

importlib.reload(props_mesh)
importlib.reload(props_obj)
importlib.reload(props_scene)

# Reloads ui
importlib.reload(headers)
importlib.reload(faceprops)
importlib.reload(instances)
importlib.reload(light)
importlib.reload(objectpanel)
importlib.reload(vertex)
importlib.reload(texanim)
importlib.reload(helpers)
importlib.reload(settings)

if "bpy" in locals():
    importlib.reload(props_scene)
if "fin_in" in locals():
    importlib.reload(fin_in)
if "fin_out" in locals():
    importlib.reload(fin_out)
if "hul_in" in locals():
    importlib.reload(hul_in)
if "hul_out" in locals():
    importlib.reload(hul_out)
if "img_in" in locals():
    importlib.reload(img_in)
if "prm_in" in locals():
    importlib.reload(prm_in)
if "prm_out" in locals():
    importlib.reload(prm_out)
if "ncp_in" in locals():
    importlib.reload(ncp_in)
if "ncp_out" in locals():
    importlib.reload(ncp_out)
if "parameters_in" in locals():
    importlib.reload(parameters_in)
if "ta_csv_in" in locals():
    importlib.reload(ta_csv_in)
if "ta_csv_out" in locals():
    importlib.reload(ta_csv_out)
if "w_in" in locals():
    importlib.reload(w_in)
if "w_out" in locals():
    importlib.reload(w_out)
if "rim_in" in locals():
    importlib.reload(rim_in)
if "rim_out" in locals():
    importlib.reload(rim_out)

from .common import DialogOperator
from .operators import ImportRV, ExportRV, RVIO_OT_ReadCarParameters, RVIO_OT_SelectRevoltDirectory
from .operators import ButtonReExport, ButtonSelectFaceProp, ButtonSelectNCPFaceProp
from .operators import ButtonSelectNCPMaterial, ButtonVertexColorSet, VertexColorRemove
from .operators import ButtonVertexColorCreateLayer, ButtonVertexAlphaSetLayer
from .operators import ButtonRenameAllObjects, SelectByName, SelectByData, UseTextureNumber
from .operators import SetInstanceProperty, RemoveInstanceProperty, BatchBake, LaunchRV, TexturesSave
from .operators import TexturesRename, CarParametersExport, IgnoreNCP 
from .operators import ToggleTriangulateNgons, ToggleExportWithoutTexture, ToggleApplyScale, ToggleApplyRotation
from .operators import ButtonBakeShadow, ToggleEnvironmentMap, ToggleNoMirror
from .operators import SetEnvironmentMapColor, ToggleNoLights, ToggleNoCameraCollision
from .operators import ToggleNoObjectCollision, ToggleMirrorPlane
from .operators import SetBCubeMeshIndices, ButtonHullGenerate, ButtonHullSphere
from .rvstruct import World, PRM, Mesh, BoundingBox, Vector, Matrix, Polygon, Vertex, UV, BigCube, TexAnimation
from .rvstruct import Frame, Color, Instances, Instance, PosNodes, PosNode, NCP, Polyhedron, Plane, LookupGrid
from .rvstruct import LookupList, Hull, ConvexHull, Edge, Interior, Sphere, RIM, MirrorPlane, TrackZones, Zone
from .texanim import ButtonCopyUvToFrame, ButtonCopyFrameToUv, PreviewNextFrame, PreviewPrevFrame, TexAnimTransform, TexAnimGrid
from .props.props_mesh import RVMeshProperties
from .props.props_obj import RVObjectProperties
from .props.props_scene import RVSceneProperties
from .ui.faceprops import RVIO_PT_RevoltFacePropertiesPanel
from .ui.headers import RVIO_PT_RevoltIOToolPanel
from .ui.helpers import RVIO_PT_RevoltHelpersPanelMesh
from .ui.instances import RVIO_PT_RevoltInstancesPanel
from .ui.light import ButtonBakeLightToVertex, RVIO_PT_RevoltLightPanel
from .ui.texanim import RVIO_PT_AnimModesPanel
from .ui.objectpanel import RVIO_PT_RevoltObjectPanel
from .ui.settings import RVIO_PT_RevoltSettingsPanel
from .ui.vertex import VertexColorPickerProperties, RVIO_PT_VertexPanel
from .ui.zone import ButtonZoneHide, OBJECT_OT_add_revolt_track_zone, RVIO_PT_RevoltZonePanel

bl_info = {
"name": "Re-Volt",
"author": "Marvin Thiel & Theman",
"version": (20, 24, 3),
"blender": (4, 0, 1),
"location": "File > Import-Export",
"description": "Import and export Re-Volt file formats.",
"wiki_url": "https://re-volt.github.io/re-volt-addon/",
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

def menu_func_import(self, context):
    """Import function for the user interface."""
    self.layout.operator("import_scene.revolt", text="Re-Volt")


def menu_func_export(self, context):
    """Export function for the user interface."""
    self.layout.operator("export_scene.revolt", text="Re-Volt")
    
def load_handler(dummy):
    initialize_custom_properties()


classes = (    
       
    # Operator classes
    DialogOperator,
    ImportRV,
    ExportRV,
    RVIO_OT_ReadCarParameters,
    ButtonReExport,
    ButtonSelectFaceProp,
    ButtonSelectNCPFaceProp,
    ButtonSelectNCPMaterial,
    ButtonVertexColorSet,
    ButtonVertexColorCreateLayer,
    ButtonVertexAlphaSetLayer,
    ButtonRenameAllObjects,
    SelectByName,
    SelectByData,
    SetInstanceProperty,
    RemoveInstanceProperty,
    BatchBake,
    LaunchRV,
    TexturesSave,
    TexturesRename,
    UseTextureNumber,
    CarParametersExport,
    ButtonHullGenerate,  
    ButtonBakeShadow,
    ButtonBakeLightToVertex,
    ButtonHullSphere,
    ButtonCopyUvToFrame,
    ButtonCopyFrameToUv,
    PreviewNextFrame,
    PreviewPrevFrame,
    TexAnimTransform,
    TexAnimGrid,
    ButtonZoneHide,
    OBJECT_OT_add_revolt_track_zone,
    IgnoreNCP,
    ToggleTriangulateNgons,
    ToggleExportWithoutTexture,
    ToggleApplyScale,
    ToggleApplyRotation,
    SetBCubeMeshIndices,
    ToggleEnvironmentMap,
    SetEnvironmentMapColor,
    ToggleNoMirror,
    ToggleNoLights,
    ToggleNoCameraCollision,
    ToggleNoObjectCollision,
    ToggleMirrorPlane,
    VertexColorPickerProperties,
    VertexColorRemove,
    RVIO_OT_SelectRevoltDirectory,
    
    # rvstruct classes
    World, 
    PRM, 
    Mesh, 
    BoundingBox, 
    Vector, 
    Matrix, 
    Polygon, 
    Vertex, 
    UV, 
    BigCube, 
    TexAnimation,
    Frame, 
    Color, 
    Instances, 
    Instance, 
    PosNodes, 
    PosNode, 
    NCP, 
    Polyhedron, 
    Plane, 
    LookupGrid,
    LookupList, 
    Hull, 
    ConvexHull, 
    Edge, 
    Interior, 
    Sphere, 
    RIM, 
    MirrorPlane, 
    TrackZones, 
    Zone,    
    
    #Custom Properties
    RVSceneProperties,
    RVObjectProperties,
    RVMeshProperties,

    # UI Panel classes
    RVIO_PT_RevoltFacePropertiesPanel,
    RVIO_PT_RevoltIOToolPanel,
    RVIO_PT_RevoltHelpersPanelMesh,
    RVIO_PT_RevoltInstancesPanel,
    RVIO_PT_RevoltLightPanel,
    RVIO_PT_RevoltObjectPanel,
    RVIO_PT_RevoltSettingsPanel,
    RVIO_PT_AnimModesPanel,
    RVIO_PT_VertexPanel,
    RVIO_PT_RevoltZonePanel,
)

def register():
    
    # Register Classes
   
    #Register Custom Properties
    props_scene.register()
    props_obj.register()
    props_mesh.register()
    
    #Register Operators
    bpy.utils.register_class(DialogOperator)
    bpy.utils.register_class(ImportRV)
    bpy.utils.register_class(ExportRV)
    bpy.utils.register_class(RVIO_OT_ReadCarParameters)
    bpy.utils.register_class(ButtonReExport)
    bpy.utils.register_class(ButtonSelectFaceProp)
    bpy.utils.register_class(ButtonSelectNCPFaceProp)
    bpy.utils.register_class(ButtonSelectNCPMaterial)
    bpy.utils.register_class(ButtonVertexColorSet)
    bpy.utils.register_class(ButtonVertexColorCreateLayer)
    bpy.utils.register_class(ButtonVertexAlphaSetLayer)
    bpy.utils.register_class(ButtonRenameAllObjects)
    bpy.utils.register_class(SelectByName)
    bpy.utils.register_class(SelectByData)
    bpy.utils.register_class(SetInstanceProperty)
    bpy.utils.register_class(RemoveInstanceProperty)
    bpy.utils.register_class(BatchBake)
    bpy.utils.register_class(LaunchRV)
    bpy.utils.register_class(TexturesSave)
    bpy.utils.register_class(TexturesRename)
    bpy.utils.register_class(UseTextureNumber)
    bpy.utils.register_class(CarParametersExport)
    bpy.utils.register_class(ButtonHullGenerate)  
    bpy.utils.register_class(ButtonBakeShadow)
    bpy.utils.register_class(ButtonBakeLightToVertex)
    bpy.utils.register_class(ButtonHullSphere)
    bpy.utils.register_class(ButtonCopyUvToFrame)
    bpy.utils.register_class(ButtonCopyFrameToUv)
    bpy.utils.register_class(PreviewNextFrame)
    bpy.utils.register_class(PreviewPrevFrame)
    bpy.utils.register_class(TexAnimTransform)
    bpy.utils.register_class(TexAnimGrid)
    bpy.utils.register_class(ButtonZoneHide)
    bpy.utils.register_class(OBJECT_OT_add_revolt_track_zone)
    bpy.utils.register_class(IgnoreNCP)
    bpy.utils.register_class(ToggleTriangulateNgons)
    bpy.utils.register_class(ToggleExportWithoutTexture)
    bpy.utils.register_class(ToggleApplyScale)
    bpy.utils.register_class(ToggleApplyRotation)
    bpy.utils.register_class(SetBCubeMeshIndices)
    bpy.utils.register_class(ToggleEnvironmentMap)
    bpy.utils.register_class(SetEnvironmentMapColor)
    bpy.utils.register_class(ToggleNoMirror)
    bpy.utils.register_class(ToggleNoLights)
    bpy.utils.register_class(ToggleNoCameraCollision)
    bpy.utils.register_class(ToggleNoObjectCollision)
    bpy.utils.register_class(ToggleMirrorPlane)
    bpy.utils.register_class(VertexColorPickerProperties)
    bpy.utils.register_class(VertexColorRemove)
    bpy.utils.register_class(RVIO_OT_SelectRevoltDirectory)
    
    # Register UI
    bpy.utils.register_class(RVIO_PT_RevoltFacePropertiesPanel)
    bpy.utils.register_class(RVIO_PT_RevoltIOToolPanel)
    bpy.utils.register_class(RVIO_PT_RevoltHelpersPanelMesh)
    bpy.utils.register_class(RVIO_PT_RevoltSettingsPanel)
    bpy.utils.register_class(RVIO_PT_AnimModesPanel)
    bpy.utils.register_class(RVIO_PT_VertexPanel)
    bpy.utils.register_class(RVIO_PT_RevoltZonePanel)
    bpy.utils.register_class(RVIO_PT_RevoltInstancesPanel)
    bpy.utils.register_class(RVIO_PT_RevoltLightPanel)
    bpy.utils.register_class(RVIO_PT_RevoltObjectPanel)
    
    bpy.types.Scene.vertex_color_picker_props = bpy.props.PointerProperty(type=VertexColorPickerProperties)
    
    bpy.types.Scene.vertex_alpha_value = bpy.props.FloatProperty(
        name="Vertex Alpha Value",
        description="Alpha value for vertex colors",
        default=1.0,  # Default to fully opaque
        min=0.0, max=1.0
        )
    
    bpy.types.Scene.stored_vertex_color = bpy.props.FloatVectorProperty(
        name="Stored Vertex Color",
        subtype='COLOR',
        default=(1.0, 1.0, 1.0),  # Default to white
        min=0.0,
        max=1.0,
        description="Stored vertex color for later use"
    )
    
    bpy.types.Scene.triangulate_ngons_enabled = bpy.props.BoolProperty(
        name="Triangulate Ngons",
        description="Enable or disable ngon triangulation",
        default=True
    )
  
    bpy.types.Scene.export_without_texture = bpy.props.BoolProperty(
        name="Export w/o Texture",
        description="Export objects without textures",
        default=False
    )

    bpy.types.Scene.apply_scale_on_export = bpy.props.BoolProperty(
        name="Apply Scale on Export",
        default=True,
        description="Apply object scale during export"
    )
    
    bpy.types.Scene.apply_rotation_on_export = bpy.props.BoolProperty(
        name="Apply Rotation on Export",
        default=True,
        description="Apply object rotation during export"
    )
    
    bpy.types.Scene.rvgl_dir = bpy.props.StringProperty(
        name="RVGL Directory",
        subtype='DIR_PATH',
        description="Directory where RVGL is located"
    )
    
    # UI and Handlers Registration
    bpy.app.handlers.depsgraph_update_pre.append(edit_object_change_handler)
    bpy.app.handlers.load_post.append(load_handler)

def unregister():
    
    # UI and Handlers Unregistration
    if load_handler in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(load_handler)
    bpy.app.handlers.depsgraph_update_pre.remove(edit_object_change_handler)
    
    del bpy.types.Scene.rvgl_dir
    del bpy.types.Scene.apply_rotation_on_export
    del bpy.types.Scene.apply_scale_on_export
    del bpy.types.Scene.export_without_texture
    del bpy.types.Scene.triangulate_ngons_enabled
    del bpy.types.Scene.stored_vertex_color
    del bpy.types.Scene.vertex_alpha_value
    del bpy.types.Scene.vertex_color_picker_props
            
    # Unregister Classes

    # Unregister UI
    bpy.utils.unregister_class(RVIO_PT_RevoltObjectPanel)
    bpy.utils.unregister_class(RVIO_PT_RevoltLightPanel)
    bpy.utils.unregister_class(RVIO_PT_RevoltInstancesPanel)
    bpy.utils.unregister_class(RVIO_PT_RevoltZonePanel)
    bpy.utils.unregister_class(RVIO_PT_VertexPanel)
    bpy.utils.unregister_class(RVIO_PT_AnimModesPanel)
    bpy.utils.unregister_class(RVIO_PT_RevoltSettingsPanel)
    bpy.utils.unregister_class(RVIO_PT_RevoltHelpersPanelMesh)
    bpy.utils.unregister_class(RVIO_PT_RevoltIOToolPanel)
    bpy.utils.unregister_class(RVIO_PT_RevoltFacePropertiesPanel)
    
    # Unregister Operators
    bpy.utils.unregister_class(RVIO_OT_SelectRevoltDirectory)
    bpy.utils.unregister_class(VertexColorRemove)
    bpy.utils.unregister_class(VertexColorPickerProperties)
    bpy.utils.unregister_class(ToggleMirrorPlane)
    bpy.utils.unregister_class(ToggleNoObjectCollision)
    bpy.utils.unregister_class(ToggleNoCameraCollision)
    bpy.utils.unregister_class(ToggleNoLights)
    bpy.utils.unregister_class(ToggleNoMirror)
    bpy.utils.unregister_class(SetEnvironmentMapColor)
    bpy.utils.unregister_class(ToggleEnvironmentMap)
    bpy.utils.unregister_class(SetBCubeMeshIndices)
    bpy.utils.unregister_class(ToggleApplyRotation)
    bpy.utils.unregister_class(ToggleApplyScale)
    bpy.utils.unregister_class(ToggleExportWithoutTexture)
    bpy.utils.unregister_class(ToggleTriangulateNgons)
    bpy.utils.unregister_class(IgnoreNCP)
    bpy.utils.unregister_class(OBJECT_OT_add_revolt_track_zone)
    bpy.utils.unregister_class(ButtonZoneHide)
    bpy.utils.unregister_class(TexAnimGrid)
    bpy.utils.unregister_class(TexAnimTransform)
    bpy.utils.unregister_class(PreviewPrevFrame)
    bpy.utils.unregister_class(PreviewNextFrame)
    bpy.utils.unregister_class(ButtonCopyFrameToUv)
    bpy.utils.unregister_class(ButtonCopyUvToFrame)
    bpy.utils.unregister_class(ButtonHullSphere)
    bpy.utils.unregister_class(ButtonBakeLightToVertex)
    bpy.utils.unregister_class(ButtonBakeShadow)
    bpy.utils.unregister_class(ButtonHullGenerate) 
    bpy.utils.unregister_class(CarParametersExport)
    bpy.utils.unregister_class(UseTextureNumber)
    bpy.utils.unregister_class(TexturesRename)
    bpy.utils.unregister_class(TexturesSave)
    bpy.utils.unregister_class(LaunchRV)
    bpy.utils.unregister_class(BatchBake)
    bpy.utils.unregister_class(RemoveInstanceProperty)
    bpy.utils.unregister_class(SetInstanceProperty)
    bpy.utils.unregister_class(SelectByData)
    bpy.utils.unregister_class(SelectByName)
    bpy.utils.unregister_class(ButtonRenameAllObjects)
    bpy.utils.unregister_class(ButtonVertexAlphaSetLayer)
    bpy.utils.unregister_class(ButtonVertexColorCreateLayer)
    bpy.utils.unregister_class(ButtonVertexColorSet)
    bpy.utils.unregister_class(ButtonSelectNCPMaterial)
    bpy.utils.unregister_class(ButtonSelectNCPFaceProp)
    bpy.utils.unregister_class(ButtonSelectFaceProp)
    bpy.utils.unregister_class(ButtonReExport)
    bpy.utils.unregister_class(RVIO_OT_ReadCarParameters)
    bpy.utils.unregister_class(ExportRV)
    bpy.utils.unregister_class(ImportRV)
    bpy.utils.unregister_class(DialogOperator)
    
    # Unregister Custom Properties
    props_mesh.unregister()
    props_obj.unregister()
    props_scene.unregister()

if __name__ == "__main__":
    register()

def dprint(*args):
    """ Debug print function """
    if DEBUG_MODE:
        print("DEBUG:", *args)

dprint("Re-Volt addon successfully registered.")