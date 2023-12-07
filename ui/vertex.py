"""
Panel for setting vertex colors in Edit Mode.
If there is no vertex color layer, the user will be prompted to create one.
It includes buttons for setting vertex colors in different shades of grey and
a custom color which is chosen with a color picker.
"""

import bpy
from ..common import *
from .widgets import *

class RVIO_PT_VertexPanel(bpy.types.Panel):
    bl_label = "Vertex Colors"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "object"
    bl_options = {"HIDE_HEADER"}

    selection = None
    selected_face_count = None

    def draw_header(self, context):
        self.layout.label(text="Vertex Colors")

    def draw(self, context):
        obj = context.object
        if obj and obj.type == 'MESH':
            # Warns if texture mode is not enabled
            widget_texture_mode(self)

            bm = get_edit_bmesh(obj)
            if bm:
                vc_layer = bm.loops.layers.color.get("Col")

                if widget_vertex_color_channel(self, obj):
                    # No vertex color channel and the panel can't be used
                    pass
                else:
                    self.draw_vertex_color_ui(context, obj)
            else:
                # Handle the case where bm is None
                self.layout.label(text="Error: Unable to access BMesh data.")
        else:
            # Object is not a mesh
            self.layout.label(text="Please select a mesh object.")

    def draw_vertex_color_ui(self, context, obj):
        me = obj.data
        box = self.layout.box()
        row = box.row()
        col = row.column()
        col.template_list("MESH_UL_uvmaps_vcols", "vcols", me, "vertex_colors", 
                          me.vertex_colors, "active_index", rows=1)
        col = row.column(align=True)
        col.operator("mesh.vertex_color_add", icon='ZOOMIN', text="")
        col.operator("mesh.vertex_color_remove", icon='ZOOMOUT', text="")
        row = box.row()
        row.template_color_picker(context.scene.revolt, 
                                  "vertex_color_picker", value_slider=True)
        col = box.column(align=True)
        row = col.row(align=True)
        row.prop(context.scene.revolt, "vertex_color_picker", text = '')
        row = col.row(align=True)
        row.operator("vertexcolor.set", icon="PASTEDOWN").number=-1
        row.operator("vertexcolor.copycolor", icon="COPYDOWN")
        row = self.layout.row(align=True)
        row.operator("vertexcolor.set", text="Grey 50%").number=50
        row = self.layout.row()
        col = row.column(align=True)
        # col.alignment = 'EXPAND'
        col.operator("vertexcolor.set", text="Grey 45%").number=45
        col.operator("vertexcolor.set", text="Grey 40%").number=40
        col.operator("vertexcolor.set", text="Grey 35%").number=35
        col.operator("vertexcolor.set", text="Grey 30%").number=30
        col.operator("vertexcolor.set", text="Grey 20%").number=20
        col.operator("vertexcolor.set", text="Grey 10%").number=10
        col.operator("vertexcolor.set", text="Black").number=0
        col = row.column(align=True)
        # col.alignment = 'EXPAND'
        col.operator("vertexcolor.set", text="Grey 55%").number=55
        col.operator("vertexcolor.set", text="Grey 60%").number=60
        col.operator("vertexcolor.set", text="Grey 65%").number=65
        col.operator("vertexcolor.set", text="Grey 70%").number=70
        col.operator("vertexcolor.set", text="Grey 80%").number=80
        col.operator("vertexcolor.set", text="Grey 90%").number=90
        col.operator("vertexcolor.set", text="White").number=100
            
dprint