import bpy

class RVIO_PT_RevoltFacePropertiesPanel(bpy.types.Panel):
    bl_label = "Face Properties"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "object"

    def draw(self, context):
        layout = self.layout
        obj = context.object

        if not obj or obj.type != 'MESH':
            layout.label(text="No mesh selected.")
            return

        mesh = obj.data

        layout.label(text="PRM Properties:")
        col = layout.column(align=True)
        col.prop(mesh, "face_double_sided", text="Double sided")
        col.prop(mesh, "face_translucent", text="Translucent")
        col.prop(mesh, "face_mirror", text="Mirror")
        col.prop(mesh, "face_additive", text="Additive blending")
        col.prop(mesh, "face_no_envmapping", text="No EnvMap")
        if mesh.get("face_envmapping"):
            scol = col.column(align=True)
            scol.prop(mesh, "face_envmapping", text="EnvMap")
            scol.prop(mesh, "face_env", text="EnvMap Color")
        else:
            col.prop(mesh, "face_envmapping", text="EnvMap")
        col.prop(mesh, "face_cloth", text="Cloth effect")
        col.prop(mesh, "face_skip", text="Do not export")

        # Add additional sections for NCP Properties if necessary
        box = layout.box()
        box.label(text="NCP Properties:")
        col = box.column(align=True)
        col.prop(mesh, "face_ncp_double", text="Double sided NCP")
        col.prop(mesh, "face_ncp_no_skid", text="No Skid Marks")
        col.prop(mesh, "face_ncp_oil", text="Oil")
        col.prop(mesh, "face_ncp_object_only", text="Object Only")
        col.prop(mesh, "face_ncp_camera_only", text="Camera Only")
        col.prop(mesh, "face_ncp_nocoll", text="No Collision")

        layout.label(text="Material Settings:")
        layout.prop(mesh, "face_material", text="Set")
        layout.prop(mesh, "select_material", text="Find")
        
        box = layout.box()
        box.label(text="Texture")
        col = box.column(align=True)
        col.prop(mesh, "face_texture", text="Texture Number")