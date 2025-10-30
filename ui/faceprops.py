import bpy
import bmesh
from ..common import int_to_texture, TEX_PAGES_MAX

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

        # ---------- Texture / Material (general) ----------
        box = layout.box()
        box.label(text="Texture / Material")
        col = box.column(align=True)
        col.prop(mesh, "material_choice")
        row = col.row(align=True)
        row.operator("object.assign_materials_auto", text="Set to All")
        row.operator("object.assign_materials", text="Set to Selected")
        col = box.column(align=True)
        col.operator("object.assign_texture", text="Car Skin")
        col = box.column(align=True)
        col.operator("mesh.set_face_texnum")
        col = box.column(align=True)
        col.operator("mesh.clear_extra_assignments")

        # Precompute selection info safely (read-only)
        has_selection = False
        if obj.mode == 'EDIT':
            try:
                bm = bmesh.from_edit_mesh(mesh)
                has_selection = any(f.select for f in bm.faces)
            except Exception:
                # If Blender is mid-topology op (e.g., Inset) and bmesh is unstable, stay graceful
                has_selection = False

        if obj.mode == 'EDIT':
            # ---------- Face Properties ----------
            box = layout.box()
            box.label(text="Face Properties:")
            col = box.column(align=True)
            # These toggles read getters that are now read-only. Enable only when selection exists.
            col.enabled = has_selection
            col.prop(mesh, "face_double_sided", text="Double sided")
            col.prop(mesh, "face_translucent", text="Translucent")
            col.prop(mesh, "face_texture_animation", text="Animated")
            col.prop(mesh, "face_mirror", text="Mirror")
            col.prop(mesh, "face_additive", text="Additive blending")
            col.prop(mesh, "face_no_envmapping", text="No EnvMap")
            col.prop(mesh, "face_envmapping", text="EnvMap")

            if getattr(mesh, "face_envmapping", False):
                try:
                    col.prop(mesh, "face_env", text="EnvMap Color")  # read-only getter now, safe
                except SystemError:
                    col.label(text="Unable to access EnvMap Color in current mode.")

            col.prop(mesh, "face_cloth", text="Cloth effect")
            col.prop(mesh, "face_skip", text="Do not export")

            # ---------- NCP Properties ----------
            box = layout.box()
            box.label(text="NCP Properties:")
            col = box.column(align=True)
            col.enabled = has_selection
            col.prop(mesh, "face_ncp_double", text="Double sided NCP")
            col.prop(mesh, "face_ncp_no_skid", text="No Skid Marks")
            col.prop(mesh, "face_ncp_oil", text="Oil")
            col.prop(mesh, "face_ncp_non_planar", text="Non-Planar")
            col.prop(mesh, "face_ncp_object_only", text="Object Only")
            col.prop(mesh, "face_ncp_camera_only", text="Camera Only")
            col.prop(mesh, "face_ncp_nocoll", text="No Collision")

            # ---------- Material Settings ----------
            box = layout.box()
            box.label(text="Material Settings:")
            col = box.column(align=True)
            col.enabled = has_selection
            # Guard against transient redraw errors during topology ops
            try:
                col.prop(mesh, "face_material", text="Set")  # getter is read-only now
            except Exception:
                row = col.row()
                row.enabled = False
                row.label(text="(Material not available during edit)")

            try:
                col.prop(mesh, "select_material", text="Find")
            except Exception:
                row = col.row()
                row.enabled = False
                row.label(text="(Find not available during edit)")

            # ---------- Texture Page (per-face) ----------
            box = layout.box()
            box.label(text="Set Texture")

            # Safe usage of the face texture getter (read-only now)
            tex_num = -3
            try:
                tex_num = mesh.face_texture
            except Exception:
                tex_num = -3

            if not has_selection or tex_num == -3:
                box.label(text="(No Face Selected)")
            elif tex_num == -2:
                box.label(text="(Multiple Textures Selected)")
            elif isinstance(tex_num, int) and 0 <= tex_num < TEX_PAGES_MAX:
                # Only show the operator if the page index is a single valid number
                box.operator("mesh.set_face_texture_dropdown", text="Change Texture Page")
            else:
                # Getter reported something unexpected — keep UI stable
                row = box.row()
                row.enabled = False
                row.label(text="(Texture layer missing/unset)")

        else:
            box = layout.box()
            box.label(text="SWITCH TO EDIT MODE FOR PROPERTIES.")
