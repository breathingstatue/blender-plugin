"""
Name:    init
Purpose: Init file for the Blender Add-On

Description:
Marv's Add-On for Re-Volt with Theman's Update 
"""

# Global debug flag
DEBUG_MODE = True

import bpy
import os
import os.path
import importlib
from bpy.app.handlers import persistent  # For the scene update handler

# Importing modules from the add-on's package
from . import (
    common,
    layers,
    operators,
    texanim,
    tools,
)

from .props import (
    props_mesh,
    props_obj,
    props_scene,
)

from .ui import (
    menu_add,
    headers,
    faceprops,
    instances,
    light,
    hull,
    object,
    scene,
    vertex,
    texanim,
    helpers,
    settings,
)

# Reloads potentially changed modules on reload (F8 in Blender)
importlib.reload(common)
importlib.reload(layers)
importlib.reload(props_mesh)
importlib.reload(props_obj)
importlib.reload(props_scene)
importlib.reload(operators)
importlib.reload(texanim)
importlib.reload(tools)

# Reloads ui
importlib.reload(menu_add)
importlib.reload(headers)
importlib.reload(faceprops)
importlib.reload(instances)
importlib.reload(light)
importlib.reload(hull)
importlib.reload(object)
importlib.reload(scene)
importlib.reload(vertex)
importlib.reload(texanim)
importlib.reload(helpers)
importlib.reload(settings)

# Reloaded here because it's used in a class which is instanced here
# Include conditional reloads for any other local modules here...

from. texanim import ButtonCopyUvToFrame, ButtonCopyFrameToUv, PreviewNextFrame, PreviewPrevFrame, TexAnimTransform, TexAnimGrid
from .props.props_mesh import RVMeshProperties
from .props.props_obj import RVObjectProperties
from .props.props_scene import RVSceneProperties
from .ui.faceprops import RevoltFacePropertiesPanel
from .ui.headers import EditModeHeader, RevoltIOToolPanel
from .ui.helpers import RevoltHelpersPanelObj, RevoltHelpersPanelMesh
from .ui.hull import RevoltHullPanel, ButtonHullGenerate, OBJECT_OT_add_revolt_hull_sphere
from .ui.instances import RevoltInstancesPanel
from .ui.light import RevoltLightPanel, ButtonBakeShadow, ButtonBakeLightToVertex
from .ui.menu_add import INFO_MT_revolt_add
from .ui.texanim import MenuAnimModes, RevoltAnimationPanel
from .ui.object import RevoltObjectPanel
from .ui.scene import RevoltScenePanel
from .ui.settings import RevoltSettingsPanel
from .ui.vertex import VertexPanel
from .ui.zone import RevoltZonePanel, ButtonZoneHide, OBJECT_OT_add_revolt_track_zone
from .operators import ImportRV, ExportRV, ButtonReExport, ButtonSelectFaceProp, ButtonSelectNCPFaceProp
from .operators import ButtonSelectNCPMaterial, ButtonColorFromActive, ButtonVertexColorSet
from .operators import ButtonVertexColorCreateLayer, ButtonVertexAlphaCreateLayer, ButtonEnableTextureMode
from .operators import ButtonEnableTexturedSolidMode, ButtonRenameAllObjects, SelectByName, SelectByData
from .operators import SetInstanceProperty, RemoveInstanceProperty, BatchBake, LaunchRV, TexturesSave
from .operators import TexturesRename, CarParametersExport

# Reloaded here because it's used in a class which is instanced here
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

@persistent
def edit_object_change_handler(scene):
    """Makes the edit mode bmesh available for use in GUI panels."""
    obj = scene.objects.active
    if obj is None:
        return
    # Adds an instance of the edit mode mesh to the global dict
    if obj.mode == 'EDIT' and obj.type == 'MESH':
        bm = dic.setdefault(obj.name, bmesh.from_edit_mesh(obj.data))
        return

    dic.clear()

def menu_func_import(self, context):
    """Import function for the user interface."""
    self.layout.operator("import_scene.revolt", text="Re-Volt")


def menu_func_export(self, context):
    """Export function for the user interface."""
    self.layout.operator("export_scene.revolt", text="Re-Volt")

classes = (
    
    # Menu classes
    INFO_MT_revolt_add,
    MenuAnimModes,

    # UI Panel classes
    RevoltFacePropertiesPanel,
    EditModeHeader,
    RevoltIOToolPanel,
    RevoltHelpersPanelObj,
    RevoltHelpersPanelMesh,
    RevoltHullPanel,
    RevoltInstancesPanel,
    RevoltLightPanel,
    RevoltObjectPanel,
    RevoltScenePanel,
    RevoltSettingsPanel,
    RevoltAnimationPanel,
    VertexPanel,
    RevoltZonePanel,

    # Operator classes
    ImportRV,
    ExportRV,
    ButtonReExport,
    ButtonSelectFaceProp,
    ButtonSelectNCPFaceProp,
    ButtonSelectNCPMaterial,
    ButtonColorFromActive,
    ButtonVertexColorSet,
    ButtonVertexColorCreateLayer,
    ButtonVertexAlphaCreateLayer,
    ButtonEnableTextureMode,
    ButtonEnableTexturedSolidMode,
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
)

def register():
    bpy.utils.register_class(RVSceneProperties)
    bpy.utils.register_class(RVObjectProperties)
    bpy.utils.register_class(RVMeshProperties)    
    # Register Properties
    bpy.types.Scene.revolt = bpy.props.PointerProperty(type=RVSceneProperties)
    bpy.types.Object.revolt = bpy.props.PointerProperty(type=RVObjectProperties)
    bpy.types.Mesh.revolt = bpy.props.PointerProperty(type=RVMeshProperties)

    # Register Classes
    for cls in classes:
        bpy.utils.register_class(cls)

    # UI and Handlers Registration
    bpy.types.TOPBAR_MT_file_import.prepend(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.prepend(menu_func_export)
    bpy.types.VIEW3D_MT_add.append(menu_add.menu_func_add)

    bpy.app.handlers.depsgraph_update_pre.append(edit_object_change_handler)

def unregister():
    # Unregister Classes
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    # Unregister Properties
    del bpy.types.Scene.revolt
    del bpy.types.Object.revolt
    del bpy.types.Mesh.revolt
    
    bpy.utils.unregister_class(RVSceneProperties)
    bpy.utils.unregister_class(RVObjectProperties)
    bpy.utils.unregister_class(RVSceneProperties)    

    # UI and Handlers Unregistration
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)
    bpy.types.VIEW3D_MT_add.remove(menu_add.menu_func_add)

    bpy.app.handlers.depsgraph_update_pre.remove(edit_object_change_handler)

if __name__ == "__main__":
    register()

def dprint(*args):
    """ Debug print function """
    if DEBUG_MODE:
        print("DEBUG:", *args)

dprint("Re-Volt addon successfully registered.")