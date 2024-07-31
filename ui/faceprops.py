import bpy
import bmesh

class RVIO_PT_RevoltFacePropertiesPanel(bpy.types.Panel):
    bl_label = "Face Properties"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "object"
    bl_options = {"HIDE_HEADER"}
    
    def draw(self, context):
        layout = self.layout
        obj = context.object

        if not obj or obj.type != 'MESH':
            layout.label(text="No mesh selected.")
            return

        mesh = obj.data
        
        box = layout.box()
        box.label(text="Texture / Material")
        col = box.column(align=True)
        col.prop(mesh, "material_choice")
        col.operator("object.assign_materials", text= "Set")

        if obj.mode == 'EDIT':
            box = layout.box()
            box.label(text="PRM Properties:")
            col = box.column(align=True)
            col.prop(mesh, "face_double_sided", text="Double sided")
            col.prop(mesh, "face_translucent", text="Translucent")
            col.prop(mesh, "face_mirror", text="Mirror")
            col.prop(mesh, "face_additive", text="Additive blending")
            col.prop(mesh, "face_no_envmapping", text="No EnvMap")
            col.prop(mesh, "face_envmapping", text="EnvMap")
        
            if getattr(mesh, "face_envmapping", False):
                col.prop(mesh, "face_env", text="EnvMap Color")
            
            col.prop(mesh, "face_cloth", text="Cloth effect")
            col.prop(mesh, "face_skip", text="Do not export")

            box = layout.box()
            box.label(text="NCP Properties:")
            col = box.column(align=True)
            col.prop(mesh, "face_ncp_double", text="Double sided NCP")
            col.prop(mesh, "face_ncp_no_skid", text="No Skid Marks")
            col.prop(mesh, "face_ncp_oil", text="Oil")
            col.prop(mesh, "face_ncp_object_only", text="Object Only")
            col.prop(mesh, "face_ncp_camera_only", text="Camera Only")
            col.prop(mesh, "face_ncp_nocoll", text="No Collision")

            box = layout.box()
            box.label(text="Material Settings:")
            col = box.column(align=True)
            col.prop(mesh, "face_material", text="Set")
            col.prop(mesh, "select_material", text="Find")
            
            box = layout.box()
            box.label(text="Texture Settings:")
            col = box.column(align=True)
            col.prop(mesh, "face_texture", text="Texture Number")
        else:
            box =layout.box()
            box.label(text="SWITCH TO EDIT MODE FOR PROPERTIES.")