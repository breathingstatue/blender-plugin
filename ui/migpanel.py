import bpy
import bmesh

class RVIO_PT_RevoltMIGPanel(bpy.types.Panel):
    bl_label = "MAKEITGOOD Properties"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"
    bl_options = {"HIDE_HEADER"}

    def draw(self, context):
        layout = self.layout
        obj = context.object
        scene = context.scene
        
        box = layout.box()
        box.label(text="Track Zones:")
        col = box.column(align=True)
        col.operator("scene.add_track_zone", icon="MATCUBE", text="Create Track Zone")
        col.operator("scene.zone_hide", icon="RESTRICT_VIEW_ON")
        
        # Dropdown menu for selecting trigger type for new triggers
        col.prop(scene, "new_trigger_type", text="Trigger")
        
        # Example button to create a trigger using the selected type
        col.operator("mesh.create_trigger", text="Create Trigger")
        
        # Hull properties
        box = layout.box()
        box.label(text="Hull Properties:")
        col = box.column(align=True)
        col.operator("scene.add_hull_sphere")