import bpy
import bmesh

class RVIO_PT_RevoltZonePanel(bpy.types.Panel):
    bl_label = "Track Zones"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"
    bl_options = {"HIDE_HEADER"}

    def draw(self, context):
        layout = self.layout
        
        box = layout.box()
        box.label(text="Track Zones:")
        col = box.column(align=True)
        col.operator("scene.add_track_zone", icon="MATCUBE", text="Create Track Zone")
        col.operator("scene.zone_hide", icon="RESTRICT_VIEW_ON")
             
        # Hull properties
        box = layout.box()
        box.label(text="Hull Properties:")
        col = box.column(align=True)
        col.operator("scene.add_hull_sphere")