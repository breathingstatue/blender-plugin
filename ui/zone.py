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
        layout.operator("object.add_track_zone", icon="MATCUBE", text="Create Track Zone")
        layout.operator("zone.hide", icon="RESTRICT_VIEW_ON")

    
class ButtonZoneHide(bpy.types.Operator):
    bl_idname = "zone.hide"
    bl_label = "Show / Hide Track Zones"
    bl_description = (
        "Shows or hides all track zones"
    )
    def execute(self, context):
        if bpy.data.groups.get('TRACK_ZONES'):
            for obj in bpy.data.groups['TRACK_ZONES'].objects:
                obj.hide = not obj.hide
        
        return{"FINISHED"}


class OBJECT_OT_add_revolt_track_zone(bpy.types.Operator):
    bl_idname = "object.add_track_zone"
    bl_label = "Track Zone"
    bl_description = (
        "Adds a new track zone under cursor location"
    )
    bl_options = {'UNDO'}
    
    def execute(self, context):
        from ..taz_in import create_zone
        obj = create_zone(None, bpy.context.scene.cursor_location)

        return {'FINISHED'}