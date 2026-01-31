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
        
        # Hull properties
        box = layout.box()
        box.label(text="Car Hull:")
        col = box.column(align=True)
        col.operator("scene.add_hull_sphere")
        
        box = layout.box()
        box.label(text="Track Zones:")
        col = box.column(align=True)
        col.operator("scene.add_track_zone", icon="MATCUBE", text="Create Track Zone")
        col.operator("scene.zone_hide", icon="HIDE_OFF")
        col.operator("object.reverse_track_zones", icon='ARROW_LEFTRIGHT', text="Reverse Zone IDs")
        
        box = layout.box()
        box.label(text="Objects")
        col = box.column(align=True)
        col.prop(context.scene, "selected_fob_object_id", text="Object")
        col.operator("object.create_fob", icon="PLUS")
        col.operator("object.toggle_fob_visibility", icon="HIDE_OFF")

        box = layout.box()
        box.label(text="Triggers")
        col = box.column(align=True)        
        # Dropdown menu for selecting trigger type for new triggers
        col.prop(scene, "new_trigger_type", text="Trigger")
        
        # Example button to create a trigger using the selected type
        col.operator("mesh.create_trigger", icon="PLUS", text="Create Trigger")
        col.operator("scene.trigger_hide", icon="HIDE_OFF")
        
        box = layout.box()
        box.label(text="Visiboxes")
        col = box.column(align=True)  
        col.prop(scene, "visibox_create_type", text="Visibox")
        col.prop(scene, "visibox_create_id", text="ID")
        col.operator("object.create_visibox", icon="PLUS", text="Create Visibox")
        col.operator("object.toggle_visibox_visibility", icon="HIDE_OFF")