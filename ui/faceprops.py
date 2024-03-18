import bpy

class RVIO_PT_RevoltFacePropertiesPanel(bpy.types.Panel):
    bl_label = "Face Properties"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "object"

    def draw(self, context):
        layout = self.layout
        obj = context.object
        scene = context.scene

        if not obj or not obj.type == 'MESH':
            layout.label(text="No mesh selected.")
            return

        mesh = obj.data

        # Assuming 'count' needs to be defined or fetched from somewhere
        count = [0] * 10  # Placeholder; replace or calculate actual counts as needed

        layout.label(text="PRM Properties:")
        col = layout.column(align=True)
        col.prop(mesh, "face_double_sided", text="{}: Double sided".format(count[1]))
        col.prop(mesh, "face_translucent", text="{}: Translucent".format(count[2]))
        col.prop(mesh, "face_mirror", text="{}: Mirror".format(count[3]))
        col.prop(mesh, "face_additive", text="{}: Additive blending".format(count[4]))
        col.prop(mesh, "face_texture_animation", text="{}: Texture animation".format(count[5]))
        col.prop(mesh, "face_no_envmapping", text="{}: No EnvMap".format(count[6]))

        if mesh.get("face_envmapping"):  # Check if 'face_envmapping' exists and is true
            scol.prop(mesh, "face_envmapping", text="{}: EnvMap".format(count[7]))
            scol.prop(mesh, "face_env", text="")
        else:
            col.prop(mesh, "face_envmapping", text="{}: EnvMap".format(count[7]))

        col.prop(mesh, "face_cloth", text="{}: Cloth effect".format(count[8]))
        col.prop(mesh, "face_skip", text="{}: Do not export".format(count[9]))

        box = layout.box()
        box.label(text="NCP Properties:")
        col = box.column(align=True)
        col.prop(mesh, "face_ncp_double", text="{}: Double sided".format(count[1]))
        col.prop(mesh, "face_ncp_no_skid", text="{}: No Skid Marks".format(count[5]))
        col.prop(mesh, "face_ncp_oil", text="{}: Oil".format(count[6]))
        col.prop(mesh, "face_ncp_object_only", text="{}: Object Only".format(count[2]))
        col.prop(mesh, "face_ncp_camera_only", text="{}: Camera Only".format(count[3]))
        col.prop(mesh, "face_ncp_nocoll", text="{}: No Collision".format(count[7]))

        layout.label(text="Set NCP Material:")
        layout.prop(mesh, "face_material", text="")
        layout.label(text="Select Material:")
        layout.prop(mesh, "select_material", text="")
