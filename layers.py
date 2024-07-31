"""
Name:    layers
Purpose: Provides functions for accessing and modifying layer values.

Description:
These property getters and setters use the bmesh from the global dict that gets
updated by the scene update handler found in init.
Creating bmeshes in the panels is bad practice as it causes unexpected
behavior.

"""

from hmac import new
import bpy
import bmesh
from .common import NCP_PROP_MASK, FACE_PROP_MASK, objects_to_bmesh, get_edit_bmesh, msg_box, COLORS, MATERIALS

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
        alpha = float(self.vertex_alpha) / 100.0

        # Set the alpha value for each loop
        for face in bm.faces:
            for loop in face.loops:
                loop[va_layer] = (alpha, alpha, alpha)

        # Update the edit mesh
        bmesh.update_edit_mesh(active_object.data)

def get_face_texture(self):
    obj = bpy.context.object
    bm = bmesh.from_edit_mesh(obj.data) if obj.mode == 'EDIT' else bmesh.new()

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
    obj = bpy.context.object
    bm = bmesh.from_edit_mesh(obj.data) if obj.mode == 'EDIT' else bmesh.new()
    layer = (bm.faces.layers.int.get("Texture Number") or
             bm.faces.layers.int.new("Texture Number"))
    for face in bm.faces:
        if face.select:
            face[layer] = value

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
    
def update_face_env(self, context):
    obj = context.object
    bm = bmesh.from_edit_mesh(obj.data) if obj.mode == 'EDIT' else bmesh.new()
    if obj.mode != 'EDIT':
        bm.from_mesh(obj.data)

    env_layer = bm.loops.layers.color.get("Env") or bm.loops.layers.color.new("Env")
    env_alpha_layer = bm.faces.layers.float.get("EnvAlpha") or bm.faces.layers.float.new("EnvAlpha")

    for face in bm.faces:
        if face.select:
            for loop in face.loops:
                loop[env_layer][:3] = self.face_env[:3]
            face[env_alpha_layer] = self.face_env[3]

    if obj.mode == 'EDIT':
        bmesh.update_edit_mesh(obj.data)
    else:
        bm.to_mesh(obj.data)
        bm.free()

    obj.data.update()

def get_face_property(mesh, prop_mask):
    obj = bpy.context.object
    if obj.type != 'MESH' or bpy.context.mode != 'EDIT_MESH':
        return False  # Check if we are in the correct context and mode

    bm = bmesh.from_edit_mesh(mesh)  # Access bmesh of the current mesh
    layer = bm.faces.layers.int.get("Type") or bm.faces.layers.int.new("Type")

    selected_faces = [face for face in bm.faces if face.select]
    if not selected_faces:
        return False

    return all((face[layer] & prop_mask) == prop_mask for face in selected_faces)

def set_face_property(mesh, value, prop_mask):
    if bpy.context.mode != 'EDIT_MESH':
        return  # Ensure we are in edit mode

    bm = bmesh.from_edit_mesh(mesh)  # Access bmesh of the current mesh
    layer = bm.faces.layers.int.get("Type") or bm.faces.layers.int.new("Type")
    modified = False  # Initialize the modified flag

    for face in bm.faces:
        if face.select:
            current = face[layer]
            new = current | prop_mask if value else current & ~prop_mask
            if new != current:
                face[layer] = new
                modified = True

    if modified:
        bmesh.update_edit_mesh(mesh)  # Update mesh if modifications were made    

def get_face_ncp_property(mesh, prop_mask):
    if bpy.context.mode != 'EDIT_MESH':
        return False
    bm = bmesh.from_edit_mesh(mesh)
    layer = bm.faces.layers.int.get("NCPType") or bm.faces.layers.int.new("NCPType")

    selected_faces = [face for face in bm.faces if face.select]
    if not selected_faces:
        return False

    return all((face[layer] & prop_mask) == prop_mask for face in selected_faces)

def set_face_ncp_property(mesh, value, prop_mask):
    # Assume mesh is a bpy.types.Mesh
    if bpy.context.mode != 'EDIT_MESH':
        return
    bm = bmesh.from_edit_mesh(mesh)
    layer = bm.faces.layers.int.get("NCPType") or bm.faces.layers.int.new("NCPType")

    modified = False  # Initialize the modified flag

    for face in bm.faces:
        if face.select:
            current = face[layer]
            new = current | prop_mask if value else current & ~prop_mask
            if new != current:
                face[layer] = new
                modified = True

    if modified:
        bmesh.update_edit_mesh(mesh)

def get_face_material(self):
    edit_object = bpy.context.edit_object
    bm = get_edit_bmesh(edit_object)
    
    if edit_object is None or edit_object.type != 'MESH' or not edit_object.mode == 'EDIT':
        return 0
    
    if not bm or not hasattr(bm, 'faces'):
        return 0
    
    material_layer = bm.faces.layers.int.get("Material") or bm.faces.layers.int.new("Material")

    selected_faces = [face for face in bm.faces if face.select]

    if not selected_faces:
        return -1

    first_material = selected_faces[0][material_layer]
    materials_differ = any(face[material_layer] != first_material for face in selected_faces)
    
    return -1 if materials_differ else first_material

def set_face_material(self, value):
    edit_object = bpy.context.edit_object
    if edit_object is None or edit_object.type != 'MESH' or not edit_object.mode == 'EDIT':
        return

    bm = bmesh.from_edit_mesh(edit_object.data)
    material_layer = bm.faces.layers.int.get("Material") or bm.faces.layers.int.new("Material")

    # Initialize the dictionary to store materials
    materials_dict = {}

    for poly in bm.faces:
        # Fetch color and create material if not already existing
        color_key = COLORS[value]
        if color_key not in materials_dict:
            mat = bpy.data.materials.new(name=f"Material_{color_key}")
            mat.use_nodes = True
            bsdf = mat.node_tree.nodes.get('Principled BSDF')
            bsdf.inputs['Base Color'].default_value = (*color_key, 1.0)  # RGB + alpha
            materials_dict[color_key] = mat
            edit_object.data.materials.append(mat)

    for face in bm.faces:
        if face.select:
            face[material_layer] = value
            color_key = COLORS[value]
            mat_name = f"Material_{color_key}"
            mat_index = edit_object.data.materials.find(mat_name)
            if mat_index == -1:
                mat = bpy.data.materials.get(mat_name)
                if not mat:
                    mat = bpy.data.materials.new(name=mat_name)
                    mat.use_nodes = True
                    bsdf = mat.node_tree.nodes.get('Principled BSDF')
                    bsdf.inputs['Base Color'].default_value = (*color_key, 1.0)
                    edit_object.data.materials.append(mat)
                mat_index = edit_object.data.materials.find(mat_name)
            face.material_index = mat_index

    bmesh.update_edit_mesh(edit_object.data, destructive=False)

def select_ncp_material(self, context):
    edit_object = bpy.context.edit_object
    bm = get_edit_bmesh(edit_object)
    mat = int(self.select_material)

    material_layer = bm.faces.layers.int.get("Material") or bm.faces.layers.int.new("Material")
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