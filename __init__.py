"""
Name:    init
Purpose: Init file for the Blender Add-On

Description:
Marv's Add-On for Re-Volt with Theman's Update 
"""

# Global debug flag
DEBUG_MODE = True

from tokenize import Ignore
import bpy
import bmesh
import os
import os.path
import importlib
from bpy.app.handlers import persistent  # For the scene update handler
from bpy.app.handlers import load_post

# Importing modules from the add-on's package
from . import (
    common,
    layers,
    operators,
    rvstruct,
    texanim,
    tools,
)

from .props import (
    props_mesh,
    props_obj,
    props_scene,
)

from .ui import (
    headers,
    faceprops,
    instances,
    light,
    hull,
    objectpanel,
    vertex,
    texanim,
    helpers,
    settings,
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
importlib.reload(hull)
importlib.reload(objectpanel)
importlib.reload(vertex)
importlib.reload(texanim)
importlib.reload(helpers)
importlib.reload(settings)

# Reloaded here because it's used in a class which is instanced here
# Include conditional reloads for any other local modules here...

from .common import DialogOperator
from .operators import ImportRV, ExportRV, ButtonReExport, ButtonSelectFaceProp, ButtonSelectNCPFaceProp
from .operators import ButtonSelectNCPMaterial, ButtonColorFromActive, ButtonVertexColorSet
from .operators import ButtonVertexColorCreateLayer, ButtonVertexAlphaSetLayer, ButtonEnableMaterialMode
from .operators import ButtonEnableSolidMode, ButtonRenameAllObjects, SelectByName, SelectByData
from .operators import SetInstanceProperty, RemoveInstanceProperty, BatchBake, LaunchRV, TexturesSave
from .operators import TexturesRename, CarParametersExport, IgnoreNCP, SetBCubeMeshIndices
from .operators import PickInstanceColor, SetModelColor, ToggleEnvironmentMap, ToggleHide, ToggleNoMirror
from .operators import SetEnvironmentMapColor, ToggleNoLights, ToggleNoCameraCollision
from .operators import ToggleNoObjectCollision, SetInstancePriority, SetLoDBias, ToggleMirrorPlane
from .operators import VertexColorRemove
from .rvstruct import World, PRM, Mesh, BoundingBox, Vector, Matrix, Polygon, Vertex, UV, BigCube, TexAnimation
from .rvstruct import Frame, Color, Instances, Instance, PosNodes, PosNode, NCP, Polyhedron, Plane, LookupGrid
from .rvstruct import LookupList, Hull, ConvexHull, Edge, Interior, Sphere, RIM, MirrorPlane, TrackZones, Zone
from .texanim import ButtonCopyUvToFrame, ButtonCopyFrameToUv, PreviewNextFrame, PreviewPrevFrame, TexAnimTransform, TexAnimGrid
from .tools import ButtonBakeShadow
from .props.props_mesh import RVMeshProperties
from .props.props_obj import RVObjectProperties
from .props.props_scene import RVSceneProperties
from .ui.faceprops import RVIO_PT_RevoltFacePropertiesPanel
from .ui.headers import RVIO_PT_EditModeHeader, RVIO_PT_RevoltIOToolPanel
from .ui.helpers import RVIO_PT_RevoltHelpersPanelMesh
from .ui.hull import ButtonHullGenerate, OBJECT_OT_add_revolt_hull_sphere, RVIO_PT_RevoltHullPanel
from .ui.instances import RVIO_PT_RevoltInstancesPanel
from .ui.light import ButtonBakeLightToVertex, RVIO_PT_RevoltLightPanel
from .ui.texanim import RVIO_PT_AnimModesPanel
from .ui.objectpanel import RVIO_PT_RevoltObjectPanel
from .ui.settings import RVIO_PT_RevoltSettingsPanel
from .ui.vertex import VertexColorPickerProperties, RVIO_PT_VertexPanel
from .ui.zone import ButtonZoneHide, OBJECT_OT_add_revolt_track_zone, RVIO_PT_RevoltZonePanel

# Reloaded here because it's used in a class which is instanced here
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


bl_info = {
"name": "Re-Volt",
"author": "Marvin Thiel & Theman",
"version": (20, 23, 12),
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
    
def initialize_custom_properties():
    for obj in bpy.data.objects:
        # Attach 'revolt' property group if not already attached
        if not hasattr(obj, 'revolt'):
            obj.revolt = bpy.props.PointerProperty(type=bpy.types.ObjectRevolt)

def load_handler(dummy):
    initialize_custom_properties()

classes = (    
       
    # Operator classes
    DialogOperator,
    ImportRV,
    ExportRV,
    ButtonReExport,
    ButtonSelectFaceProp,
    ButtonSelectNCPFaceProp,
    ButtonSelectNCPMaterial,
    ButtonColorFromActive,
    ButtonVertexColorSet,
    ButtonVertexColorCreateLayer,
    ButtonVertexAlphaSetLayer,
    ButtonEnableMaterialMode,
    ButtonEnableSolidMode,
    ButtonRenameAllObjects,
    SelectByName,
    SelectByData,
    SetInstanceProperty,
    RemoveInstanceProperty,
    BatchBake,
    LaunchRV,
    TexturesSave,
    TexturesRename,
    CarParametersExport,
    ButtonHullGenerate,  
    ButtonBakeShadow,
    ButtonBakeLightToVertex,
    OBJECT_OT_add_revolt_hull_sphere,
    ButtonCopyUvToFrame,
    ButtonCopyFrameToUv,
    PreviewNextFrame,
    PreviewPrevFrame,
    TexAnimTransform,
    TexAnimGrid,
    ButtonZoneHide,
    OBJECT_OT_add_revolt_track_zone,
    IgnoreNCP,
    SetBCubeMeshIndices,
    PickInstanceColor,
    SetModelColor,
    ToggleEnvironmentMap,
    SetEnvironmentMapColor,
    ToggleHide,
    ToggleNoMirror,
    ToggleNoLights,
    ToggleNoCameraCollision,
    ToggleNoObjectCollision,
    SetInstancePriority,
    SetLoDBias,
    ToggleMirrorPlane,
    VertexColorPickerProperties,
    VertexColorRemove,
    
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
    RVIO_PT_EditModeHeader,
    RVIO_PT_RevoltIOToolPanel,
    RVIO_PT_RevoltHelpersPanelMesh,
    RVIO_PT_RevoltHullPanel,
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
    # for cls in classes:
       # bpy.utils.register_class(cls)

    props_scene.register()

    #Register Custom Properties
    bpy.utils.register_class(RVSceneProperties)
    bpy.utils.register_class(RVObjectProperties)
    bpy.utils.register_class(RVMeshProperties)
    
    #Register Operators
    bpy.utils.register_class(DialogOperator)
    bpy.utils.register_class(ImportRV)
    bpy.utils.register_class(ExportRV)
    bpy.utils.register_class(ButtonReExport)
    bpy.utils.register_class(ButtonSelectFaceProp)
    bpy.utils.register_class(ButtonSelectNCPFaceProp)
    bpy.utils.register_class(ButtonSelectNCPMaterial)
    bpy.utils.register_class(ButtonColorFromActive)
    bpy.utils.register_class(ButtonVertexColorSet)
    bpy.utils.register_class(ButtonVertexColorCreateLayer)
    bpy.utils.register_class(ButtonVertexAlphaSetLayer)
    bpy.utils.register_class(ButtonEnableMaterialMode)
    bpy.utils.register_class(ButtonEnableSolidMode)
    bpy.utils.register_class(ButtonRenameAllObjects)
    bpy.utils.register_class(SelectByName)
    bpy.utils.register_class(SelectByData)
    bpy.utils.register_class(SetInstanceProperty)
    bpy.utils.register_class(RemoveInstanceProperty)
    bpy.utils.register_class(BatchBake)
    bpy.utils.register_class(LaunchRV)
    bpy.utils.register_class(TexturesSave)
    bpy.utils.register_class(TexturesRename)
    bpy.utils.register_class(CarParametersExport)
    bpy.utils.register_class(ButtonHullGenerate)  
    bpy.utils.register_class(ButtonBakeShadow)
    bpy.utils.register_class(ButtonBakeLightToVertex)
    bpy.utils.register_class(OBJECT_OT_add_revolt_hull_sphere)
    bpy.utils.register_class(ButtonCopyUvToFrame)
    bpy.utils.register_class(ButtonCopyFrameToUv)
    bpy.utils.register_class(PreviewNextFrame)
    bpy.utils.register_class(PreviewPrevFrame)
    bpy.utils.register_class(TexAnimTransform)
    bpy.utils.register_class(TexAnimGrid)
    bpy.utils.register_class(ButtonZoneHide)
    bpy.utils.register_class(OBJECT_OT_add_revolt_track_zone)
    bpy.utils.register_class(IgnoreNCP)
    bpy.utils.register_class(SetBCubeMeshIndices)
    bpy.utils.register_class(PickInstanceColor)
    bpy.utils.register_class(SetModelColor)
    bpy.utils.register_class(ToggleEnvironmentMap)
    bpy.utils.register_class(SetEnvironmentMapColor)
    bpy.utils.register_class(ToggleHide)
    bpy.utils.register_class(ToggleNoMirror)
    bpy.utils.register_class(ToggleNoLights)
    bpy.utils.register_class(ToggleNoCameraCollision)
    bpy.utils.register_class(ToggleNoObjectCollision)
    bpy.utils.register_class(SetInstancePriority)
    bpy.utils.register_class(SetLoDBias)
    bpy.utils.register_class(ToggleMirrorPlane)
    bpy.utils.register_class(VertexColorPickerProperties)
    bpy.utils.register_class(VertexColorRemove)
    
    # Register UI
    bpy.utils.register_class(RVIO_PT_RevoltFacePropertiesPanel)
    bpy.utils.register_class(RVIO_PT_EditModeHeader)
    bpy.utils.register_class(RVIO_PT_RevoltIOToolPanel)
    bpy.utils.register_class(RVIO_PT_RevoltHelpersPanelMesh)
    bpy.utils.register_class(RVIO_PT_RevoltHullPanel)
    bpy.utils.register_class(RVIO_PT_RevoltSettingsPanel)
    bpy.utils.register_class(RVIO_PT_AnimModesPanel)
    bpy.utils.register_class(RVIO_PT_VertexPanel)
    bpy.utils.register_class(RVIO_PT_RevoltZonePanel)
    bpy.utils.register_class(RVIO_PT_RevoltInstancesPanel)
    bpy.utils.register_class(RVIO_PT_RevoltLightPanel)
    bpy.utils.register_class(RVIO_PT_RevoltObjectPanel)

    # Register Properties
    bpy.types.Scene.revolt = bpy.props.PointerProperty(type=RVSceneProperties)
    bpy.types.Object.revolt = bpy.props.PointerProperty(type=RVObjectProperties)
    bpy.types.Mesh.revolt = bpy.props.PointerProperty(type=RVMeshProperties)
    bpy.types.Scene.vertex_color_picker_props = bpy.props.PointerProperty(type=VertexColorPickerProperties)
    
    bpy.types.Scene.vertex_alpha_value = bpy.props.FloatProperty(
    name="Vertex Alpha Value",
    description="Alpha value for vertex colors",
    default=1.0,  # Default to fully opaque
    min=0.0, max=1.0
    )
  
    # UI and Handlers Registration
    bpy.app.handlers.depsgraph_update_pre.append(edit_object_change_handler)
    bpy.app.handlers.load_post.append(load_handler)

def unregister():
    
    # UI and Handlers Unregistration
    if load_handler in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(load_handler)
    bpy.app.handlers.depsgraph_update_pre.remove(edit_object_change_handler)
    
    del bpy.types.Scene.vertex_alpha_value
    del bpy.types.Scene.vertex_color_picker_props
    del bpy.types.Mesh.revolt
    del bpy.types.Object.revolt
    del bpy.types.Scene.revolt
    
    props_scene.unregister()
        
    # Unregister Classes
    # for cls in reversed(classes):
        # bpy.utils.unregister_class(cls)

    # Unregister UI
    bpy.utils.unregister_class(RVIO_PT_RevoltObjectPanel)
    bpy.utils.unregister_class(RVIO_PT_RevoltLightPanel)
    bpy.utils.unregister_class(RVIO_PT_RevoltInstancesPanel)
    bpy.utils.unregister_class(RVIO_PT_RevoltZonePanel)
    bpy.utils.unregister_class(RVIO_PT_VertexPanel)
    bpy.utils.unregister_class(RVIO_PT_AnimModesPanel)
    bpy.utils.unregister_class(RVIO_PT_RevoltSettingsPanel)
    bpy.utils.unregister_class(RVIO_PT_RevoltHullPanel)
    bpy.utils.unregister_class(RVIO_PT_RevoltHelpersPanelMesh)
    bpy.utils.unregister_class(RVIO_PT_RevoltIOToolPanel)
    bpy.utils.unregister_class(RVIO_PT_EditModeHeader)
    bpy.utils.unregister_class(RVIO_PT_RevoltFacePropertiesPanel)
    
    # Unregister Operators
    bpy.utils.unregister_class(VertexColorRemove)
    bpy.utils.unregister_class(VertexColorPickerProperties)
    bpy.utils.unregister_class(ToggleMirrorPlane)
    bpy.utils.unregister_class(SetLoDBias)
    bpy.utils.unregister_class(SetInstancePriority)
    bpy.utils.unregister_class(ToggleNoObjectCollision)
    bpy.utils.unregister_class(ToggleNoCameraCollision)
    bpy.utils.unregister_class(ToggleNoLights)
    bpy.utils.unregister_class(ToggleNoMirror)
    bpy.utils.unregister_class(ToggleHide)
    bpy.utils.unregister_class(SetEnvironmentMapColor)
    bpy.utils.unregister_class(ToggleEnvironmentMap)
    bpy.utils.unregister_class(SetModelColor)
    bpy.utils.unregister_class(PickInstanceColor)
    bpy.utils.unregister_class(SetBCubeMeshIndices)
    bpy.utils.unregister_class(IgnoreNCP)
    bpy.utils.unregister_class(OBJECT_OT_add_revolt_track_zone)
    bpy.utils.unregister_class(ButtonZoneHide)
    bpy.utils.unregister_class(TexAnimGrid)
    bpy.utils.unregister_class(TexAnimTransform)
    bpy.utils.unregister_class(PreviewPrevFrame)
    bpy.utils.unregister_class(PreviewNextFrame)
    bpy.utils.unregister_class(ButtonCopyFrameToUv)
    bpy.utils.unregister_class(ButtonCopyUvToFrame)
    bpy.utils.unregister_class(OBJECT_OT_add_revolt_hull_sphere)
    bpy.utils.unregister_class(ButtonBakeLightToVertex)
    bpy.utils.unregister_class(ButtonBakeShadow)
    bpy.utils.unregister_class(ButtonHullGenerate) 
    bpy.utils.unregister_class(CarParametersExport)
    bpy.utils.unregister_class(TexturesRename)
    bpy.utils.unregister_class(TexturesSave)
    bpy.utils.unregister_class(LaunchRV)
    bpy.utils.unregister_class(BatchBake)
    bpy.utils.unregister_class(RemoveInstanceProperty)
    bpy.utils.unregister_class(SetInstanceProperty)
    bpy.utils.unregister_class(SelectByData)
    bpy.utils.unregister_class(SelectByName)
    bpy.utils.unregister_class(ButtonRenameAllObjects)
    bpy.utils.unregister_class(ButtonEnableSolidMode)
    bpy.utils.unregister_class(ButtonEnableMaterialMode)
    bpy.utils.unregister_class(ButtonVertexAlphaSetLayer)
    bpy.utils.unregister_class(ButtonVertexColorCreateLayer)
    bpy.utils.unregister_class(ButtonVertexColorSet)
    bpy.utils.unregister_class(ButtonColorFromActive)
    bpy.utils.unregister_class(ButtonSelectNCPMaterial)
    bpy.utils.unregister_class(ButtonSelectNCPFaceProp)
    bpy.utils.unregister_class(ButtonSelectFaceProp)
    bpy.utils.unregister_class(ButtonReExport)
    bpy.utils.unregister_class(ExportRV)
    bpy.utils.unregister_class(ImportRV)
    bpy.utils.unregister_class(DialogOperator)
    # Unregister Custom Properties
    bpy.utils.unregister_class(RVMeshProperties)
    bpy.utils.unregister_class(RVObjectProperties)
    bpy.utils.unregister_class(RVSceneProperties)

if __name__ == "__main__":
    register()

def dprint(*args):
    """ Debug print function """
    if DEBUG_MODE:
        print("DEBUG:", *args)

dprint("Re-Volt addon successfully registered.")