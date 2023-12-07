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
    headers,
    faceprops,
    instances,
    light,
    hull,
    objectpanel,
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
importlib.reload(headers)
importlib.reload(faceprops)
importlib.reload(instances)
importlib.reload(light)
importlib.reload(hull)
importlib.reload(objectpanel)
importlib.reload(scene)
importlib.reload(vertex)
importlib.reload(texanim)
importlib.reload(helpers)
importlib.reload(settings)

# Reloaded here because it's used in a class which is instanced here
# Include conditional reloads for any other local modules here...

from .operators import ImportRV, ExportRV, ButtonReExport, ButtonSelectFaceProp, ButtonSelectNCPFaceProp
from .operators import ButtonSelectNCPMaterial, ButtonColorFromActive, ButtonVertexColorSet
from .operators import ButtonVertexColorCreateLayer, ButtonVertexAlphaCreateLayer, ButtonEnableMaterialMode
from .operators import ButtonEnableSolidMode, ButtonRenameAllObjects, SelectByName, SelectByData
from .operators import SetInstanceProperty, RemoveInstanceProperty, BatchBake, LaunchRV, TexturesSave
from .operators import TexturesRename, CarParametersExport
from. texanim import ButtonCopyUvToFrame, ButtonCopyFrameToUv, PreviewNextFrame, PreviewPrevFrame, TexAnimTransform, TexAnimGrid
from .props.props_mesh import RVMeshProperties
from .props.props_obj import RVObjectProperties
from .props.props_scene import RVSceneProperties
from .ui.faceprops import RVIO_PT_RevoltFacePropertiesPanel
from .ui.headers import RVIO_PT_EditModeHeader, RVIO_PT_RevoltIOToolPanel
from .ui.helpers import RVIO_PT_RevoltHelpersPanelMesh, RVIO_PT_RevoltHelpersPanelObj
from .ui.hull import ButtonHullGenerate, OBJECT_OT_add_revolt_hull_sphere, RVIO_PT_RevoltHullPanel
from .ui.instances import RVIO_PT_RevoltInstancesPanel
from .ui.light import ButtonBakeShadow, ButtonBakeLightToVertex, RVIO_PT_RevoltLightPanel
from .ui.texanim import RVIO_PT_AnimModesPanel, RVIO_PT_RevoltAnimationPanel
from .ui.objectpanel import RVIO_PT_RevoltObjectPanel
from .ui.scene import RVIO_PT_RevoltScenePanel
from .ui.settings import RVIO_PT_RevoltSettingsPanel
from .ui.vertex import RVIO_PT_VertexPanel
from .ui.zone import ButtonZoneHide, OBJECT_OT_add_revolt_track_zone, RVIO_PT_RevoltZonePanel

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

bmesh_dict = {}  # This global dictionary will store your BMesh objects

@persistent
def edit_object_change_handler(scene):
    """Makes the edit mode bmesh available for use in GUI panels."""
    obj = bpy.context.view_layer.objects.active

    # If no active object or the active object is not a mesh, clear the dictionary and return
    if obj is None or obj.type != 'MESH':
        bmesh_dict.clear()
        return

    # Handle the case where the object is in edit mode
    if obj.mode == 'EDIT':
        try:
            # Set default only if obj.name is not in bmesh_dict, to avoid creating a new bmesh each time
            if obj.name not in bmesh_dict:
                bmesh_dict[obj.name] = bmesh.from_edit_mesh(obj.data)
        except KeyError as e:
            print(f"Error accessing BMesh for object: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")
    else:
        # If the object is not in edit mode, clear the dictionary
        bmesh_dict.clear()

def menu_func_import(self, context):
    """Import function for the user interface."""
    self.layout.operator("import_scene.revolt", text="Re-Volt")


def menu_func_export(self, context):
    """Export function for the user interface."""
    self.layout.operator("export_scene.revolt", text="Re-Volt")

classes = (
    
    # UI Panel classes
    RVIO_PT_RevoltFacePropertiesPanel,
    RVIO_PT_EditModeHeader,
    RVIO_PT_RevoltIOToolPanel,
    RVIO_PT_RevoltHelpersPanelObj,
    RVIO_PT_RevoltHelpersPanelMesh,
    RVIO_PT_RevoltHullPanel,
    RVIO_PT_RevoltInstancesPanel,
    RVIO_PT_RevoltLightPanel,
    RVIO_PT_RevoltObjectPanel,
    RVIO_PT_RevoltScenePanel,
    RVIO_PT_RevoltSettingsPanel,
    RVIO_PT_RevoltAnimationPanel,
    RVIO_PT_VertexPanel,
    RVIO_PT_RevoltZonePanel,

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
)

def register():
    bpy.utils.register_class(RVSceneProperties)
    bpy.utils.register_class(RVObjectProperties)
    bpy.utils.register_class(RVMeshProperties)
    
    # Register Classes
    for cls in classes:
        bpy.utils.register_class(cls)

    # Register Properties
    bpy.types.Scene.revolt = bpy.props.PointerProperty(type=RVSceneProperties)
    bpy.types.Object.revolt = bpy.props.PointerProperty(type=RVObjectProperties)
    bpy.types.Mesh.revolt = bpy.props.PointerProperty(type=RVMeshProperties)
 
    # UI and Handlers Registration
    bpy.app.handlers.depsgraph_update_pre.append(edit_object_change_handler)

def unregister():
    
    # UI and Handlers Unregistration
    bpy.app.handlers.depsgraph_update_pre.remove(edit_object_change_handler)
    
    # Unregister Properties
    del bpy.types.Mesh.revolt
    del bpy.types.Object.revolt
    del bpy.types.Scene.revolt
        
    # Unregister Classes
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

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