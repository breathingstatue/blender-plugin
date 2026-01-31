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
from .common import TEX_PAGES_MAX, NCP_PROP_MASK, FACE_PROP_MASK, get_edit_bmesh, msg_box, COLORS, MATERIALS

def _safe_bm_from_edit_mesh(obj):
    try:
        if not obj or obj.type != 'MESH' or obj.mode != 'EDIT':
            return None
        bm = bmesh.from_edit_mesh(obj.data)
        # extra paranoia
        if not bm or not hasattr(bm, 'faces'):
            return None
        return bm
    except Exception:
        return None

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

def get_alpha_items():
    return [(f"{i}", f"{i}%", f"Set alpha to {i}%") for i in range(0, 101, 10)]

def get_face_texture(self):
    """Returns:
       -3 = no face selected / wrong mode
       -2 = mixed values
       -1 = layer missing / unset
       >=0 = single texture page index
    """
    obj = bpy.context.object
    bm = _safe_bm_from_edit_mesh(obj)
    if bm is None:
        return -3

    layer = bm.faces.layers.int.get("Texture Number")
    sel = [f for f in bm.faces if f.select]
    if not sel:
        return -3
    if layer is None:
        return -1

    first = sel[0][layer]
    return -2 if any(f[layer] != first for f in sel) else first

def set_face_texture(self, value):
    obj = bpy.context.object
    if not obj or obj.type != 'MESH' or obj.mode != 'EDIT':
        return

    bm = bmesh.from_edit_mesh(obj.data)
    layer = bm.faces.layers.int.get("Texture Number") or bm.faces.layers.int.new("Texture Number")

    if value == -1:
        return  # NONE, do nothing

    for face in bm.faces:
        if face.select:
            face[layer] = value

    bmesh.update_edit_mesh(obj.data, destructive=False)
            
def get_face_env(self):
    """Returns RGBA list. Defaults to [1,1,1,1] if no selection or layers missing."""
    obj = bpy.context.edit_object
    bm = _safe_bm_from_edit_mesh(obj)
    if bm is None:
        return [1.0, 1.0, 1.0, 1.0]

    env_layer = bm.loops.layers.color.get("Env")
    env_alpha_layer = bm.faces.layers.float.get("EnvAlpha")
    sel = [f for f in bm.faces if f.select]
    if not sel or env_layer is None or env_alpha_layer is None:
        return [1.0, 1.0, 1.0, 1.0]

    col = get_average_vcol2(sel, env_layer)
    return [*col, sel[0][env_alpha_layer]]

def set_face_env(self, value):
    obj = bpy.context.edit_object
    if not obj or obj.type != 'MESH' or obj.mode != 'EDIT':
        return

    bm = bmesh.from_edit_mesh(obj.data)

    # OK to create in a setter
    env_layer = bm.loops.layers.color.get("Env") or bm.loops.layers.color.new("Env")
    env_alpha_layer = bm.faces.layers.float.get("EnvAlpha") or bm.faces.layers.float.new("EnvAlpha")

    for face in bm.faces:
        if face.select:
            for loop in face.loops:
                loop[env_layer][0] = value[0]
                loop[env_layer][1] = value[1]
                loop[env_layer][2] = value[2]
            face[env_alpha_layer] = value[3]

    bmesh.update_edit_mesh(obj.data, destructive=False)
    obj.data.update()
    
def update_face_env(self, context):
    for obj in context.selected_objects:
        if obj.type == 'MESH':
            bm = bmesh.from_edit_mesh(obj.data) if obj.mode == 'EDIT' else bmesh.new()
            if obj.mode != 'EDIT':
                bm.from_mesh(obj.data)

            env_layer = bm.loops.layers.color.get("Env") or bm.loops.layers.color.new("Env")
            env_alpha_layer = bm.faces.layers.float.get("EnvAlpha") or bm.faces.layers.float.new("EnvAlpha")

            for face in bm.faces:
                if face.select:
                    for loop in face.loops:
                        loop[env_layer][:3] = obj.data.face_env[:3]
                    face[env_alpha_layer] = obj.data.face_env[3]

            if obj.mode == 'EDIT':
                bmesh.update_edit_mesh(obj.data)
            else:
                bm.to_mesh(obj.data)
                bm.free()

            obj.data.update()
    
def update_envmapping(self, context):
    obj = context.object
    if obj is None or obj.type != 'MESH':
        return

    is_edit_mode = obj.mode == 'EDIT'

    if is_edit_mode:
        try:
            bm = bmesh.from_edit_mesh(obj.data)
        except Exception:
            return
    else:
        bm = bmesh.new()
        bm.from_mesh(obj.data)

        # Find or create the _Env material
        base_name, suffix = get_base_name_for_layers(obj)
        prefixed_mat_name = f"{base_name}_Env"
        generic_mat_name = "_Env"
        material = bpy.data.materials.get(prefixed_mat_name) or bpy.data.materials.get(generic_mat_name)

        if not material:
            material = bpy.data.materials.new(name=generic_mat_name)
            material.use_nodes = True
            nodes = material.node_tree.nodes
            links = material.node_tree.links

            material_output = nodes.get('Material Output') or nodes.new(type='ShaderNodeOutputMaterial')
            attr_node = nodes.new(type='ShaderNodeAttribute')
            attr_node.attribute_name = "Env"

            principled_bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
            links.new(attr_node.outputs['Color'], principled_bsdf.inputs['Base Color'])
            links.new(principled_bsdf.outputs['BSDF'], material_output.inputs['Surface'])

        # Ensure the material is added to the object if not already present
        if material.name not in obj.data.materials:
            obj.data.materials.append(material)

        # Assign the material to selected faces and set the Type layer
        mat_index = obj.data.materials.find(material.name)
        type_layer = bm.faces.layers.int.get("Type") or bm.faces.layers.int.new("Type")

        if is_edit_mode:
            bmesh.update_edit_mesh(obj.data)
        else:
            bm.to_mesh(obj.data)
            bm.free()

        obj.data.update()

        # Force update the viewport
        bpy.context.view_layer.update()

def update_no_envmapping(self, context):
    obj = context.object
    if obj is None or obj.type != 'MESH':
        return

    is_edit_mode = obj.mode == 'EDIT'

    if is_edit_mode:
        try:
            bm = bmesh.from_edit_mesh(obj.data)
        except Exception:
            return
    else:
        bm = bmesh.new()
        bm.from_mesh(obj.data)

        # Find the _Env material
        base_name, suffix = get_base_name_for_layers(obj)
        prefixed_mat_name = f"{base_name}_Env"
        generic_mat_name = "_Env"
        material = bpy.data.materials.get(prefixed_mat_name) or bpy.data.materials.get(generic_mat_name)

        if material:
            # Remove material from selected faces and clear the Type layer
            mat_index = obj.data.materials.find(material.name)
            type_layer = bm.faces.layers.int.get("Type")

            if is_edit_mode:
                bmesh.update_edit_mesh(obj.data)
            else:
                bm.to_mesh(obj.data)
                bm.free()

            obj.data.update()

            # Force update the viewport
            bpy.context.view_layer.update()
            
def get_fin_envcol(self):
    return self.get("fin_envcol", (1.0, 1.0, 1.0, 1.0))

def set_fin_envcol(self, value):
    self["fin_envcol"] = value
    print(f"fin_envcol set to {value}")
    update_fin_envcol(self, bpy.context)
    
def update_fin_envcol(self, context):
    selected_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']

    if not selected_objects:
        print("No mesh objects selected.")
        return

    obj = selected_objects[0]  # Ensure only one mesh is updated at a time

    is_edit_mode = obj.mode == 'EDIT'
    bm = bmesh.from_edit_mesh(obj.data) if is_edit_mode else bmesh.new()
    if not is_edit_mode:
        bm.from_mesh(obj.data)

    env_layer = bm.loops.layers.color.get("Env") or bm.loops.layers.color.new("Env")
    env_alpha_layer = bm.faces.layers.float.get("EnvAlpha") or bm.faces.layers.float.new("EnvAlpha")

    fin_envcol = self["fin_envcol"]

    for face in bm.faces:
        if face.select:
            for loop in face.loops:
                loop[env_layer][:3] = fin_envcol[:3]
            face[env_alpha_layer] = fin_envcol[3]

    if is_edit_mode:
        bmesh.update_edit_mesh(obj.data)
    else:
        bm.to_mesh(obj.data)
        bm.free()

    obj.data.update()
    
def update_fin_env(self, context):
    for obj in context.selected_objects:
        if obj.type == 'MESH':
            if obj.fin_env:
                create_or_assign_env_material(obj)
            else:
                remove_env_material(obj)

def create_or_assign_env_material(obj):
    def setup_material(material):
        material.use_nodes = True
        nodes = material.node_tree.nodes
        links = material.node_tree.links

        material_output = nodes.get('Material Output') or nodes.new(type='ShaderNodeOutputMaterial')
        attr_node = nodes.get('ShaderNodeAttribute') or nodes.new(type='ShaderNodeAttribute')
        attr_node.attribute_name = "Env"

        principled_bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
        links.new(attr_node.outputs['Color'], principled_bsdf.inputs['Base Color'])
        links.new(principled_bsdf.outputs['BSDF'], material_output.inputs['Surface'])

    base_name, suffix = get_base_name_for_layers(obj)
    prefixed_mat_name = f"{base_name}_Env"
    generic_mat_name = "_Env"

    # Check for the material with the base name prefix or the generic name
    material = bpy.data.materials.get(prefixed_mat_name) or bpy.data.materials.get(generic_mat_name)

    if not material:
        # Create the material with the generic name if neither exists
        material = bpy.data.materials.new(name=generic_mat_name)
        setup_material(material)

    # Ensure the material is added to the object if not already present
    if material.name not in obj.data.materials:
        obj.data.materials.append(material)

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    env_layer = bm.loops.layers.color.get("Env") or bm.loops.layers.color.new("Env")
    env_alpha_layer = bm.faces.layers.float.get("EnvAlpha") or bm.faces.layers.float.new("EnvAlpha")
    type_layer = bm.faces.layers.int.get("Type") or bm.faces.layers.int.new("Type")

    for face in bm.faces:
        for loop in face.loops:
            loop[env_layer] = (1.0, 1.0, 1.0, 1.0)  # Set default color
        face[env_alpha_layer] = 1.0
        face[type_layer] = 1  # Set Type layer for env mapping

    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()

def remove_env_material(obj):
    base_name, suffix = get_base_name_for_layers(obj)
    prefixed_mat_name = f"{base_name}_Env"
    generic_mat_name = "_Env"

    # Check for the material with the base name prefix or the generic name
    material = bpy.data.materials.get(prefixed_mat_name) or bpy.data.materials.get(generic_mat_name)

    if material:
        if obj.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        # Handle bmesh operations
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        mat_index = obj.data.materials.find(material.name)
        type_layer = bm.faces.layers.int.get("Type")

        if mat_index != -1:
            for face in bm.faces:
                if face.material_index == mat_index:
                    face.material_index = 0  # Assign to a default material index or keep empty
                    if type_layer:
                        face[type_layer] = 0  # Reset Type layer

            bm.to_mesh(obj.data)
            bm.free()

            # Remove material from the object
            if material.name in obj.data.materials.keys():
                obj.data.materials.pop(index=mat_index)

        obj.data.update()

def update_rgb(self, context):
    for obj in context.selected_objects:
        if obj.type == 'MESH':
            if obj.fin_model_rgb:
                create_or_assign_rgb_material(obj)
            else:
                remove_rgb_material(obj)

def create_or_assign_rgb_material(obj):
    def setup_material(material):
        material.use_nodes = True
        nodes = material.node_tree.nodes
        links = material.node_tree.links

        material_output = nodes.get('Material Output') or nodes.new(type='ShaderNodeOutputMaterial')
        attr_node = nodes.new(type='ShaderNodeAttribute')
        attr_node.attribute_name = "RGBModelColor"

        principled_bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
        links.new(attr_node.outputs['Color'], principled_bsdf.inputs['Base Color'])
        links.new(principled_bsdf.outputs['BSDF'], material_output.inputs['Surface'])

    base_name, suffix = get_base_name_for_layers(obj)
    prefixed_mat_name = f"{base_name}_RGBModelColor"
    generic_mat_name = "_RGBModelColor"

    # Check for the material with the base name prefix or the generic name
    material = bpy.data.materials.get(prefixed_mat_name) or bpy.data.materials.get(generic_mat_name)

    if not material:
        # Create the material with the generic name if neither exists
        material = bpy.data.materials.new(name=generic_mat_name)
        setup_material(material)

    # Ensure the material is added to the object if not already present
    if material.name not in obj.data.materials:
        obj.data.materials.append(material)

    # Handle bmesh operations
    is_edit_mode = obj.mode == 'EDIT'
    if is_edit_mode:
        bm = bmesh.from_edit_mesh(obj.data)
    else:
        bm = bmesh.new()
        bm.from_mesh(obj.data)
    
    mat_index = obj.data.materials.find(material.name)

    for face in bm.faces:
        face.material_index = mat_index

    if is_edit_mode:
        bmesh.update_edit_mesh(obj.data)
    else:
        bm.to_mesh(obj.data)
        bm.free()

    obj.data.update()

def remove_rgb_material(obj):
    base_name, suffix = get_base_name_for_layers(obj)
    prefixed_mat_name = f"{base_name}_RGBModelColor"
    generic_mat_name = "_RGBModelColor"

    # Check for the material with the base name prefix or the generic name
    material = bpy.data.materials.get(prefixed_mat_name) or bpy.data.materials.get(generic_mat_name)

    if material:
        # Handle bmesh operations
        is_edit_mode = obj.mode == 'EDIT'
        if is_edit_mode:
            bm = bmesh.from_edit_mesh(obj.data)
        else:
            bm = bmesh.new()
            bm.from_mesh(obj.data)

        mat_index = obj.data.materials.find(material.name)

        if mat_index != -1:
            for face in bm.faces:
                if face.material_index == mat_index:
                    face.material_index = 0  # Assign to a default material index or keep empty

            if is_edit_mode:
                bmesh.update_edit_mesh(obj.data)
            else:
                bm.to_mesh(obj.data)
                bm.free()

            # Remove material from the object
            if material.name in obj.data.materials.keys():
                obj.data.materials.pop(index=mat_index)

        obj.data.update()

def get_rgb(self):
    return self.get("fin_col", (0.5, 0.5, 0.5))

def set_rgb(self, value):
    self["fin_col"] = value
    print(f"fin_col set to {value}")

def update_fin_col(self, context):
    obj = getattr(context, "object", None)
    if not obj or obj.type != 'MESH':
        print("No active mesh object to update fin color.")
        return

    is_edit_mode = obj.mode == 'EDIT'
    bm = bmesh.from_edit_mesh(obj.data) if is_edit_mode else bmesh.new()
    if not is_edit_mode:
        bm.from_mesh(obj.data)

    fin_col = self.get("fin_col", [0.5, 0.5, 0.5])
    
    if not fin_col:
        print("RGB Model Color not found")
        if obj.mode != 'EDIT':
            bm.free()
        return

    rgbcol_layer = bm.loops.layers.color.get('RGBModelColor')
    if not rgbcol_layer:
        rgbcol_layer = bm.loops.layers.color.new('RGBModelColor')

    for face in bm.faces:
        if face.select:
            for loop in face.loops:
                loop[rgbcol_layer][:3] = fin_col[:3]

    if is_edit_mode:
        bmesh.update_edit_mesh(obj.data)
    else:
        bm.to_mesh(obj.data)
        bm.free()

    obj.data.update()
        
def get_face_property(mesh, prop_mask):
    """Boolean; False if layer missing/no selection/wrong mode."""
    obj = bpy.context.object
    bm = _safe_bm_from_edit_mesh(obj)
    if bm is None:
        return False

    layer = bm.faces.layers.int.get("Type")
    if layer is None:
        return False

    sel = [f for f in bm.faces if f.select]
    if not sel:
        return False

    return all((f[layer] & prop_mask) == prop_mask for f in sel)

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
    """Boolean; False if layer missing/no selection/wrong mode."""
    obj = bpy.context.object
    bm = _safe_bm_from_edit_mesh(obj)
    if bm is None:
        return False

    layer = bm.faces.layers.int.get("NCPType")
    if layer is None:
        return False

    sel = [f for f in bm.faces if f.select]
    if not sel:
        return False

    return all((f[layer] & prop_mask) == prop_mask for f in sel)

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
    """Returns:
       -1 = unset / none selected / layer missing / mixed
       >=0 = single material index stored in the 'Material' face layer
    """
    edit_object = bpy.context.edit_object
    bm = _safe_bm_from_edit_mesh(edit_object)
    if bm is None:
        return -1

    material_layer = bm.faces.layers.int.get("Material")
    if material_layer is None:
        return -1

    sel = [f for f in bm.faces if f.select]
    if not sel:
        return -1

    first = sel[0][material_layer]
    return -1 if any(f[material_layer] != first for f in sel) else first

def set_face_material(self, value):
    edit_object = bpy.context.edit_object
    if edit_object is None or edit_object.type != 'MESH' or edit_object.mode != 'EDIT':
        return

    bm = bmesh.from_edit_mesh(edit_object.data)
    # OK to create in a setter
    material_layer = bm.faces.layers.int.get("Material") or bm.faces.layers.int.new("Material")

    material_info = next((item for item in MATERIALS if item[0] == str(value)), None)
    material_name = material_info[1] if material_info else f"Material_{value}"

    for face in bm.faces:
        if face.select:
            face[material_layer] = value
            mat_index = edit_object.data.materials.find(material_name)
            if mat_index == -1:
                mat = bpy.data.materials.get(material_name)
                if not mat:
                    mat = bpy.data.materials.new(name=material_name)
                    mat.use_nodes = True
                    bsdf = mat.node_tree.nodes.get('Principled BSDF')
                    if bsdf:
                        bsdf.inputs['Base Color'].default_value = (*COLORS[value], 1.0)
                edit_object.data.materials.append(mat)
                mat_index = edit_object.data.materials.find(material_name)
            face.material_index = mat_index

    bmesh.update_edit_mesh(edit_object.data, destructive=False)

def select_ncp_material(self, context):
    edit_object = bpy.context.edit_object

    if edit_object is None or edit_object.type != 'MESH' or not edit_object.mode == 'EDIT':
        return

    bm = get_edit_bmesh(edit_object)
    if bm is None or not hasattr(bm, 'faces'):
        return

    material_layer = bm.faces.layers.int.get("Material")
    if material_layer is None:
        material_layer = bm.faces.layers.int.new("Material")

    mat = int(self.select_material)
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
        material_name = MATERIALS[mat + 1][1] if mat + 1 < len(MATERIALS) else "Unknown"
        msg_box(f"No {material_name} materials found.")
    else:
        print(f"Selected {count} faces with the material '{material_name}'.")

    bmesh.update_edit_mesh(edit_object.data, destructive=False)
        
def get_base_name_for_layers(obj):
    name_parts = obj.name.split('.')
    base_name = name_parts[0]
    suffix = ""

    # Check if the last part of the name is a number (suffix like .001, .002)
    if len(name_parts) > 1 and name_parts[-1].isdigit():
        suffix = f".{name_parts[-1]}"

    extension = ""
    specific_parts = ["body", "wheel", "axle", "spring"]

    if ".w" in obj.name:
        extension = ".w"
    elif ".prm" in obj.name or any(part in obj.name for part in specific_parts):
        extension = ".prm"

    return f"{base_name}{extension}", suffix