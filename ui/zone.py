import bpy
import bmesh

class RVIO_PT_RevoltZonePanel(bpy.types.Panel):
    bl_label = "Track Zones"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"

    def draw_header(self, context):
        self.layout.label(text="Track Zones")

    def draw(self, context):
        view = context.space_data
        obj = context.object
        props = context.scene.revolt
        layout = self.layout
        layout.operator("scene.add_track_zone", icon="MATCUBE", text="Create Track Zone")
        layout.operator("scene.zone_hide", icon="RESTRICT_VIEW_ON")
             
        # Hull properties
        box.label(text="Hull Properties:")
        col = box.column(align=True)
        col.operator("scene.add_hull_sphere")