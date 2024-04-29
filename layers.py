"""
Name:    layers
Purpose: Provides functions for accessing and modifying layer values.

Description:
These property getters and setters use the bmesh from the global dict that gets
updated by the scene update handler found in init.
Creating bmeshes in the panels is bad practice as it causes unexpected
behavior.

"""

import bpy
import bmesh
import mathutils
from .common import NCP_PROP_MASK, FACE_PROP_MASK, objects_to_bmesh, get_edit_bmesh, msg_box, COLORS, MATERIALS
from .prm_in import add_rvmesh_to_bmesh

def color_from_face(context):
    obj = context.object
    if not obj or obj.type != 'MESH':
        print("No mesh object selected.")
        return

    bm = get_edit_bmesh(obj)
    if not bm:
        print("BMesh could not be obtained.")
        return

    selmode = context.tool_settings.mesh_select_mode

    if selmode[0]:  # Vertex select mode
        verts = [v for v in bm.verts if v.select]
        if verts:
            layer = bm.loops.layers.color.get("Col")
            if layer:
                col = get_average_vcol0(verts, layer)
                context.scene.vertex_color_picker = col

    elif selmode[2]:  # Face select mode
        faces = [f for f in bm.faces if f.select]
        if faces:
            layer = bm.loops.layers.color.get("Col")
            if layer:
                col = get_average_vcol2(faces, layer)
                context.scene.vertex_color_picker = col

def get_average_vcol0(verts, layer):
    """ Gets the average vertex color of loops all given VERTS """
    len_cols = 0
    r = 0
    g = 0
    b = 0
    for vert in verts:
        cols = [loop[layer] for loop in vert.link_loops]
        r += sum([c[0] for c in cols])
        g += sum([c[1] for c in cols])
        b += sum([c[2] for c in cols])
        len_cols += len(cols)

    return (r / len_cols, g / len_cols, b / len_cols)

def get_average_vcol2(faces, layer):
    """ Gets the average vertex color of all loops of given FACES """
    len_cols = 0
    r = 0
    g = 0
    b = 0
    for face in faces:
        cols = [loop[layer] for loop in face.loops]
        r += sum([c[0] for c in cols])
        g += sum([c[1] for c in cols])
        b += sum([c[2] for c in cols])
        len_cols += len(cols)

    return (r / len_cols, g / len_cols, b / len_cols)


def set_vcol(faces, layer, color):
    for face in faces:
        for loop in face.loops:
            loop[layer][0] = color[0]
            loop[layer][1] = color[1]
            loop[layer][2] = color[2]


def set_vertex_color(context, number):
    eo = context.edit_object
    if not eo or eo.type != 'MESH':
        print("No mesh object in edit mode.")
        return

    bm = dic.setdefault(eo.name, bmesh.from_edit_mesh(eo.data))
    if not bm:
        print("Failed to get or create BMesh for the object.")
        return

    mesh = eo.data
    selmode = context.tool_settings.mesh_select_mode

    v_layer = bm.loops.layers.color.active
    if not v_layer:
        print("Active vertex color layer not found.")
        return

    # Define the color to set
    if number == -1:
        cpick = context.scene.vertex_color_picker
        color = mathutils.Color(cpick)
    else:
        color = mathutils.Color((number / 100, number / 100, number / 100))

    # Apply the color based on the selection mode
    for face in bm.faces:
        if face.select or any(vert.select for loop in face.loops for vert in [loop.vert]):
            for loop in face.loops:
                if selmode[0] and loop.vert.select or selmode[1] and (loop.edge.select or face.loops[loop.index - 1].edge.select) or selmode[2]:
                    loop[v_layer] = color

    bmesh.update_edit_mesh(mesh, tessface=False, destructive=False)
    
def update_vertex_color_picker(self, context):
    # Get the active object and its edit mesh
    active_object = context.active_object
    if active_object and active_object.mode == 'EDIT':
        bm = bmesh.from_edit_mesh(active_object.data)

        # Get or create the vertex color layer
        vc_layer = bm.loops.layers.color.get("Col")
        if not vc_layer:
            vc_layer = bm.loops.layers.color.new("Col")

        # Set the color value for each loop
        color_value = self.vertex_color_picker
        for face in bm.faces:
            for loop in face.loops:
                loop[vc_layer] = color_value

        # Update the edit mesh
        bmesh.update_edit_mesh(active_object.data)

# Define the alpha values
alpha_values = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]

# Property definition function for vertex alpha
def update_vertex_alpha(self, context):
    # Get the active object and its edit mesh
    active_object = context.active_object
    if active_object and active_object.mode == 'EDIT':
        bm = bmesh.from_edit_mesh(active_object.data)

        # Get or create the vertex alpha layer
        va_layer = bm.loops.layers.color.get("Alpha")
        if not va_layer:
            va_layer = bm.loops.layers.color.new("Alpha")

        # Convert the alpha value from the enum property to a float
        alpha_percentage = float(self.vertex_alpha) / 100.0

        # Set the alpha value for each loop
        for face in bm.faces:
            for loop in face.loops:
                loop[va_layer] = (alpha_percentage, alpha_percentage, alpha_percentage, alpha_percentage)

        # Update the edit mesh
        bmesh.update_edit_mesh(active_object.data)

def get_face_material(self):
    eo = bpy.context.edit_object
    bm = get_edit_bmesh(eo)
    
    if eo is None or eo.type != 'MESH' or not eo.mode == 'EDIT':
        return 0
    
    if not bm or not hasattr(bm, 'faces'):
        return 0
    
    layer = (bm.faces.layers.int.get("Material") or
             bm.faces.layers.int.new("Material"))

    selected_faces = [face for face in bm.faces if face.select]

    materials_differ = any(
        [face[layer] != selected_faces[0][layer] for face in selected_faces]
    )
    if len(selected_faces) == 0 or materials_differ:
        return -1
    else:
        return selected_faces[0][layer]


def set_face_material(self, value):
    eo = bpy.context.edit_object
    bm = get_edit_bmesh(eo)
    mesh = eo.data
    layer = (bm.faces.layers.int.get("Material") or
             bm.faces.layers.int.new("Material"))
    vc_layer = (bm.loops.layers.color.get("NCPPreview") or
                bm.loops.layers.color.new("NCPPreview"))

    for face in bm.faces:
        if face.select:
            face[layer] = value
            for loop in face.loops:
                loop[vc_layer][0] = COLORS[value][0]
                loop[vc_layer][1] = COLORS[value][1]
                loop[vc_layer][2] = COLORS[value][2]
    bmesh.update_edit_mesh(mesh, destructive=False)
 

def get_face_texture(self):
    eo = bpy.context.edit_object
    bm = get_edit_bmesh(eo)
    
    if eo is None or eo.type != 'MESH' or not eo.mode == 'EDIT':
        return 0

    layer = (bm.faces.layers.int.get("Texture Number") or
             bm.faces.layers.int.new("Texture Number"))

    selected_faces = [face for face in bm.faces if face.select]
    textures_differ = any(
        [face[layer] != selected_faces[0][layer] for face in selected_faces]
    )
    if len(selected_faces) == 0:
        return -3
    elif textures_differ:
        return -2
    else:
        return selected_faces[0][layer]


def set_face_texture(self, value):
    eo = bpy.context.edit_object
    bm = get_edit_bmesh(eo)
    layer = (bm.faces.layers.int.get("Texture Number") or
             bm.faces.layers.int.new("Texture Number"))
    for face in bm.faces:
        if face.select:
            face[layer] = value


def set_face_env(self, value):
    eo = bpy.context.edit_object
    bm = get_edit_bmesh(eo)
    env_layer = (bm.loops.layers.color.get("Env") or
                 bm.loops.layers.color.new("Env"))
    env_alpha_layer = (bm.faces.layers.float.get("EnvAlpha") or
                       bm.faces.layers.float.new("EnvAlpha"))
    for face in bm.faces:
        if face.select:
            for loop in face.loops:
                loop[env_layer][0] = value[:3][0]
                loop[env_layer][1] = value[:3][1]
                loop[env_layer][2] = value[:3][2]
            face[env_alpha_layer] = value[-1]


def get_face_env(self):
    eo = bpy.context.edit_object
    bm = get_edit_bmesh(eo)
    env_layer = (bm.loops.layers.color.get("Env")
                 or bm.loops.layers.color.new("Env"))
    env_alpha_layer = (bm.faces.layers.float.get("EnvAlpha")
                       or bm.faces.layers.float.new("EnvAlpha"))
    
    if eo is None or eo.type != 'MESH' or not eo.mode == 'EDIT':
        return 0

    # Gets the average color for all selected faces
    selected_faces = [face for face in bm.faces if face.select]
    col = get_average_vcol2(selected_faces, env_layer)

    return [*col, selected_faces[0][env_alpha_layer]]


def get_face_property(self):
    eo = bpy.context.edit_object
    
    if eo is None or eo.type != 'MESH' or not eo.mode == 'EDIT':
        return 0

    bm = get_edit_bmesh(eo)

    if not bm or not hasattr(bm, 'faces'):
        return 0

    layer = bm.faces.layers.int.get("Type") or bm.faces.layers.int.new("Type")
    selected_faces = [face for face in bm.faces if face.select]
    if not selected_faces:
        return 0

    prop = selected_faces[0][layer]
    for face in selected_faces[1:]:  # Avoid checking the first face again
        prop = prop & face[layer]

    return prop


def set_face_property(obj, value, FACE_PROP_MASK):
    eo = bpy.context.edit_object
    bm = get_edit_bmesh(eo)
    layer = bm.faces.layers.int.get("Type") or bm.faces.layers.int.new("Type")
    for face in bm.faces:
        if face.select:
            print("face[layer] before operation:", face[layer], "type:", type(face[layer]))
            face[layer] = face[layer] | FACE_PROP_MASK if value else face[layer] & ~FACE_PROP_MASK
            

def get_face_ncp_property(self):
    eo = bpy.context.edit_object
    
    # Ensure we have an edit object
    if eo is None or eo.type != 'MESH':
        return 0

    bm = get_edit_bmesh(eo)

    if not bm or not hasattr(bm, 'faces'):
        return 0

    layer = bm.faces.layers.int.get("NCPType") or bm.faces.layers.int.new("NCPType")
    selected_faces = [face for face in bm.faces if face.select]
    if not selected_faces:
        return 0

    prop = selected_faces[0][layer]
    for face in selected_faces[1:]:  # Skip the first as it's already included in prop
        prop = prop & face[layer]

    return prop


def set_face_ncp_property(obj, value, NCP_PROP_MASK):
    eo = bpy.context.edit_object
    bm = get_edit_bmesh(eo)
    layer = (bm.faces.layers.int.get("NCPType") or
             bm.faces.layers.int.new("NCPType"))
    for face in bm.faces:
        if face.select:
            face[layer] = face[layer] | NCP_PROP_MASK if value else face[layer] & ~NCP_PROP_MASK


def select_faces(context, prop):
    eo = bpy.context.edit_object
    bm = get_edit_bmesh(eo)
    flag_layer = (bm.faces.layers.int.get("Type") or
                  bm.faces.layers.int.new("Type"))

    for face in bm.faces:
        if face[flag_layer] & prop:
            face.select = not face.select


def select_ncp_faces(context, prop):
    eo = bpy.context.edit_object
    bm = get_edit_bmesh(eo)
    flag_layer = (bm.faces.layers.int.get("NCPType") or
                  bm.faces.layers.int.new("NCPType"))

    for face in bm.faces:
        if face[flag_layer] & prop:
            face.select = not face.select


def select_ncp_material(self, context):
    eo = bpy.context.edit_object
    bm = get_edit_bmesh(eo)
    mat = int(self.select_material)

    material_layer = (bm.faces.layers.int.get("Material") or
                      bm.faces.layers.int.new("Material"))
    count = 0
    count_sel = 0
    for face in bm.faces:
        if face[material_layer] == mat:
            count += 1
            if not face.select:
                face.select = True
            else:
                count_sel += 1

    if count == 0:
        msg_box("No {} materials found.".format(MATERIALS[mat+1][1]))    