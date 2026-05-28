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

        mig_box = layout.box()
        mig_box.label(text="MAKEITGOOD")

        box = mig_box.box()
        box.label(text="Track Zones:")
        col = box.column(align=True)
        col.operator("scene.add_track_zone", icon="MATCUBE", text="Create Track Zone")
        col.operator("object.reverse_track_zones", icon='ARROW_LEFTRIGHT', text="Reverse Zone IDs")

        box = mig_box.box()
        box.label(text="AI Nodes")
        col = box.column(align=True)
        col.prop(scene, "ai_nodes_lane_width", text="New Width")
        col.prop(scene, "ai_nodes_default_property", text="New Type")
        row = col.row(align=True)
        row.prop(scene, "ai_nodes_default_left_wall", text="Left Wall")
        row.prop(scene, "ai_nodes_default_right_wall", text="Right Wall")
        col.prop(scene, "ai_nodes_connect_to_selected", text="Connect to Selected")
        col.prop(scene, "ai_nodes_secondary_path", text="Additional Route")
        if scene.ai_nodes_secondary_path:
            col.prop(scene, "ai_nodes_branch_start", text="Split From")
        col.operator("scene.add_ai_node", icon="PLUS", text="Create AI Node")
        col.operator("scene.generate_ai_nodes_from_track_zones", icon="MOD_BUILD", text="Automated AI Nodes")
        col.operator("scene.automate_ai_overtake_line", icon="MOD_BUILD", text="Automated Overtake Line")

        selected_box = box.box()
        selected_box.label(text="Selected Mesh Path")
        selected_col = selected_box.column(align=True)
        marker_row = selected_col.row(align=True)
        marker_row.operator("scene.mark_ai_selected_path_start", text="Starting Node")
        marker_row.operator("scene.mark_ai_selected_path_end", text="Ending Node")
        selected_col.operator("scene.generate_ai_nodes_to_selected", icon="MESH_DATA", text="AI Nodes to Selected")

        box = mig_box.box()
        box.label(text="Pos Nodes")
        col = box.column(align=True)
        col.prop(scene, "pos_nodes_split_route", text="Split Route")
        col.operator("scene.add_pos_node", icon="PLUS", text="Create Pos Node")
        col.prop(scene, "pos_nodes_auto_spacing", text="Auto Spacing", slider=True)
        col.operator("scene.generate_pos_nodes_from_track_zones", icon="MOD_BUILD", text="Automated Pos Nodes")
        
        box = mig_box.box()
        box.label(text="Objects")
        col = box.column(align=True)
        col.prop(context.scene, "selected_fob_object_id", text="Object")
        col.operator("object.create_fob", icon="PLUS")

        box = mig_box.box()
        box.label(text="Lights")
        col = box.column(align=True)
        col.prop(scene, "new_light_type", text="Type")
        col.operator("object.create_light", icon="LIGHT")

        box = mig_box.box()
        box.label(text="Force Fields")
        col = box.column(align=True)
        col.prop(scene, "new_force_field_type", text="Type")
        col.prop(scene, "new_force_field_shape", text="Shape")
        col.operator("object.create_force_field", icon="FORCE_FORCE", text="Create Force Field")

        box = mig_box.box()
        box.label(text="Triggers")
        col = box.column(align=True)        
        # Dropdown menu for selecting trigger type for new triggers
        col.prop(scene, "new_trigger_type", text="Trigger")
        
        # Example button to create a trigger using the selected type
        col.operator("mesh.create_trigger", icon="PLUS", text="Create Trigger")
        
        box = mig_box.box()
        box.label(text="Visiboxes")
        col = box.column(align=True)  
        col.prop(scene, "visibox_create_type", text="Visibox")
        col.prop(scene, "visibox_create_id", text="ID")
        col.operator("object.create_visibox", icon="PLUS", text="Create Visibox")
