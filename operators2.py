"""
Name:    operators2
Purpose: Shadow, texture animation, vertex color, and shader bake operators.
"""

import bpy
import bmesh
import math
import mathutils
from mathutils import Vector as BlenderVector

from . import rvstruct
from .common import FACE_TEXANIM, TEX_PAGES_MAX, msg_box
from .texanim import copy_frame_to_uv, copy_uv_to_frame, update_ta_current_frame

"""
SHADOW -----------------------------------------------------------------------
"""

class BakeShadow(bpy.types.Operator):
    bl_idname = "lighttools.bake_shadow"
    bl_label = "Bake Shadow"
    bl_description = "Creates a shadow plane beneath the selected object"

    def check_for_selected(self, context):
        """Checks if exactly one object is selected and it is the car's body. If not, prompts the user."""
        selected_objects = context.selected_objects
    
        # Check if no objects are selected
        if not selected_objects:
            msg_box("Select Car first", "INFO")
            return False  # Indicates that the operation should be canceled

        # Check if multiple objects are selected
        if len(selected_objects) > 1:
            msg_box("Select Car's body only", "INFO")
            return False  # Indicates that the operation should be canceled
        return True  # Indicates that there are selected objects and the operation can continue

    def create_unique_material(self, base_name="ShadowMaterial"):
        material_name = base_name
        index = 1
        while material_name in bpy.data.materials:
            material_name = f"{base_name}.{index:03d}"
            index += 1
        new_material = bpy.data.materials.new(name=material_name)
        new_material.use_nodes = True
        return new_material, material_name

    def assign_texture_to_material(self, mat, image):
        """Assigns a texture image to the material for baking."""
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links

        # Add image texture node
        tex_image_node = nodes.new('ShaderNodeTexImage')
        tex_image_node.image = image
        links.clear()  # Clear existing links to avoid any issues

        # Set the image node as active for baking
        mat.node_tree.nodes.active = tex_image_node

    def get_brightness_factor(self):
        return 1.6  # Fixed value — no scene property needed

    def blur_texture_edges(self, material, image):
        """Applies a blur on the shadow edges using a gradient texture with a fixed blur scale."""
        nodes = material.node_tree.nodes
        links = material.node_tree.links

        # Clear existing nodes
        nodes.clear()

        # Add the image texture node (this is the texture being blurred)
        tex_image_node = nodes.new('ShaderNodeTexImage')
        tex_image_node.image = image

        # Add a gradient texture for edge softening
        gradient_node = nodes.new('ShaderNodeTexGradient')
        gradient_node.gradient_type = 'RADIAL'

        # Add a mapping node to control the gradient scale (fixed blur strength)
        mapping_node = nodes.new('ShaderNodeMapping')
        mapping_node.inputs['Scale'].default_value = (1.5, 1.5, 1.5)  # Fixed blur scale, adjust if necessary

        # Add the color ramp to control the blending of black and white
        color_ramp_node = nodes.new('ShaderNodeValToRGB')
        color_ramp_node.color_ramp.interpolation = 'LINEAR'

        # Set the black (background) value
        color_ramp_node.color_ramp.elements[0].position = 0.5  # Adjust as needed
        color_ramp_node.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)  # Black

        # Set the white (shadow) value
        color_ramp_node.color_ramp.elements[1].position = 0.99  # Keep the shadow white
        color_ramp_node.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1.0)  # White

        # Add a mix node to blend the shadow and the gradient for softening edges
        mix_node = nodes.new('ShaderNodeMixRGB')
        mix_node.blend_type = 'MIX'
        mix_node.inputs['Fac'].default_value = 1.0  # Full opacity

        # Connect the gradient to the mix shader
        links.new(mapping_node.outputs['Vector'], gradient_node.inputs['Vector'])
        links.new(gradient_node.outputs['Color'], color_ramp_node.inputs['Fac'])  # Mask for edges

        # Connect the shadow texture to the mix shader
        links.new(tex_image_node.outputs['Color'], mix_node.inputs[2])

        # Connect the color ramp to the mix node to ensure the shadow stays white
        links.new(color_ramp_node.outputs['Color'], mix_node.inputs[1])

        # Connect the final mix to the material output
        output_node = nodes.new('ShaderNodeOutputMaterial')
        links.new(mix_node.outputs['Color'], output_node.inputs['Surface'])

    def bake_and_process(self, context, margin, texture_name_suffix, material, threshold):
        shadow_resolution = int(context.scene.shadow_resolution)
        shadow_tex = bpy.data.images.new(f"Shadow_{texture_name_suffix}", width=shadow_resolution, height=shadow_resolution, alpha=True)

        # Assign bake texture and get node
        tex_image_node = material.node_tree.nodes.new('ShaderNodeTexImage')
        tex_image_node.image = shadow_tex
        tex_image_node.name = "AO_BakeTarget"
        material.node_tree.nodes.active = tex_image_node

        # Ensure the active object is selected
        shadow_obj = context.active_object
        context.view_layer.objects.active = shadow_obj
        shadow_obj.select_set(True)

        # Ensure UV unwrap
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.unwrap(method='ANGLE_BASED', margin=margin)
        bpy.ops.object.mode_set(mode='OBJECT')

        print("[DEBUG] Baking AO...")
        bpy.ops.object.bake(type='AO')
        print("[DEBUG] AO bake done")

        self.fast_shadow_post_process(shadow_tex, threshold)

        return shadow_tex

    def fast_shadow_post_process(self, image, threshold):
        import numpy as np
        print(f"[DEBUG] Threshold used: {threshold}")

        pixels = np.array(image.pixels[:], dtype=np.float32).reshape((-1, 4))

        # 1. Invert AO: shadows become white
        pixels[:, :3] = 1.0 - pixels[:, :3]

        # 2. Thicken shadow via remap
        pixels[:, :3] = np.clip(pixels[:, :3] ** 0.25, 0.0, 1.0)

        # 3. Apply binary threshold — snap to pure black or white
        shadow_mask = pixels[:, :3] >= threshold
        pixels[:, :3] = np.where(shadow_mask, 1.0, 0.0)

        image.pixels[:] = pixels.flatten()
        image.update()
        print("[DEBUG] Shadow finalized (thresholded)")

    def bake_blurred_texture_to_image(self, context, shadow_plane, material):
        """Bakes the blurred shader output into a texture image."""
        shadow_resolution = int(context.scene.shadow_resolution)
        shadow_image = bpy.data.images.new(name="shadow", width=shadow_resolution, height=shadow_resolution, alpha=True)

        # Ensure UV map exists
        if not shadow_plane.data.uv_layers:
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.uv.unwrap(method='ANGLE_BASED', margin=0.001)
            bpy.ops.object.mode_set(mode='OBJECT')

        # Create and activate image node for bake target
        nodes = material.node_tree.nodes
        tex_image_node = nodes.get("Blurred_BakeTarget") or nodes.new('ShaderNodeTexImage')
        tex_image_node.name = "Blurred_BakeTarget"
        tex_image_node.image = shadow_image
        material.node_tree.nodes.active = tex_image_node

        # Set the shadow plane as active
        context.view_layer.objects.active = shadow_plane
        shadow_plane.select_set(True)

        # Bake shader result to texture
        bpy.ops.object.bake(type='COMBINED')

        # Pack image to avoid loss
        shadow_image.pack()

        # Assign final texture
        self.assign_final_texture(shadow_plane, shadow_image)

        return shadow_image

    def assign_final_texture(self, shadow_plane, shadow_tex):
        """Assigns the final baked shadow texture to the shadow plane."""
        mat = shadow_plane.active_material
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links

        # Reuse or create Image Texture node
        tex_image_node = nodes.get("FinalShadowTex") or nodes.new('ShaderNodeTexImage')
        tex_image_node.name = "FinalShadowTex"
        tex_image_node.image = shadow_tex

        # Reuse or find BSDF node
        bsdf_node = nodes.get("Principled BSDF")
        if not bsdf_node:
            for node in nodes:
                if node.type == 'BSDF_PRINCIPLED':
                    bsdf_node = node
                    break

        # Connect texture to Base Color
        if bsdf_node:
            links.new(tex_image_node.outputs['Color'], bsdf_node.inputs['Base Color'])

        mat.use_nodes = True

    def bake_shadow(self, context):
        from .tools import map_strength_to_threshold
        
        original_active = context.view_layer.objects.active
        scene = context.scene
        original_engine = scene.render.engine

        print("[DEBUG] Starting BakeShadow operator")
        
        # Check for selected objects
        if not self.check_for_selected(context):
            return {'CANCELLED'}

        # Use shadow quality from scene
        print("[DEBUG] Setting Cycles render settings")
        scene.render.engine = 'CYCLES'
        scene.cycles.samples = int(scene.shadow_quality)
        scene.cycles.max_bounces = 1
        scene.cycles.diffuse_bounces = 0
        scene.cycles.glossy_bounces = 0
        scene.cycles.transmission_bounces = 0
        scene.cycles.transparent_max_bounces = 0
        scene.cycles.volume_bounces = 0

        # Proceed with baking if objects are selected
        shade_obj = context.selected_objects[0]

        # Setup light
        lamp_data_pos = bpy.data.lights.new(name="ShadePositive", type="AREA")
        lamp_data_pos.energy = 1000.0
        lamp_data_pos.size = 2.0
        lamp_positive = bpy.data.objects.new(name="ShadePositive", object_data=lamp_data_pos)
        scene.collection.objects.link(lamp_positive)
        
        print("[DEBUG] Light setup complete")

        all_objs = [ob_child for ob_child in context.scene.objects if ob_child.parent == shade_obj] + [shade_obj]

        far_left = min([min([(ob.matrix_world[0][3] + ob.bound_box[i][0] * shade_obj.scale[0]) for i in range(0, 8)]) for ob in all_objs])
        far_right = max([max([(ob.matrix_world[0][3] + ob.bound_box[i][0] * shade_obj.scale[0]) for i in range(0, 8)]) for ob in all_objs])
        far_front = max([max([(ob.matrix_world[1][3] + ob.bound_box[i][1] * shade_obj.scale[1]) for i in range(0, 8)]) for ob in all_objs])
        far_back = min([min([(ob.matrix_world[1][3] + ob.bound_box[i][1] * shade_obj.scale[1]) for i in range(0, 8)]) for ob in all_objs])
        far_bottom = min([min([(ob.matrix_world[2][3] + ob.bound_box[i][2] * shade_obj.scale[2]) for i in range(0, 8)]) for ob in all_objs])
        far_top = max([(ob.matrix_world @ BlenderVector(corner))[2] for ob in all_objs for corner in ob.bound_box])

        dim_x = abs(far_left - far_right)
        dim_y = abs(far_front - far_back)

        loc = ((far_right + far_left) / 2, (far_front + far_back) / 2, far_bottom)

        object_height = far_top - far_bottom
        light_height = far_top + object_height * 0.5
        lamp_positive.location = (loc[0], loc[1], light_height)
        lamp_positive.rotation_euler = (math.radians(0), 0, 0)

        # Ensure we're in object mode before running selection
        if context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        # Deselect all objects
        bpy.ops.object.select_all(action='DESELECT')
        
        print("[DEBUG] Bounds calculated, creating shadow plane")

        bpy.ops.mesh.primitive_plane_add(size=1, enter_editmode=False, align='WORLD', location=loc)
        shadow_plane = context.active_object
        shadow_plane.name = 'ShadowPlane'

        sphor = (shadow_plane.location[0] - (shadow_plane.dimensions[0] / 2))
        spver = ((shadow_plane.dimensions[1] / 2) - shadow_plane.location[1])

        sleft = (sphor - shade_obj.location[0]) * 100
        sright = (shade_obj.location[0] - sphor) * 100
        sfront = (spver - shade_obj.location[1]) * 100
        sback = (shade_obj.location[1] - spver) * 100
        sheight = (far_bottom - shade_obj.location[2]) * 100
        shtable = ";)SHADOWTABLE {:.4f} {:.4f} {:.4f} {:.4f} {:.4f}".format(
            sleft, sright, sfront, sback, sheight)

        scene["shadow_table"] = shtable
        scene.shadow_table = shtable

        shadow_plane.scale.x *= 1.5
        shadow_plane.scale.y *= 1.5
        
        print(f"[DEBUG] ShadowPlane created at {shadow_plane.location}")

        # Apply scale
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

        print("[DEBUG] Applying material")
        mat, material_name = self.create_unique_material("ShadowMaterial")
        shadow_plane.data.materials.append(mat)

        # Prepare for first bake
        context.view_layer.objects.active = shadow_plane
        shadow_plane.select_set(True)
        bpy.ops.object.mode_set(mode='EDIT')

        # First bake
        strength = bpy.context.scene.shadow_strength
        threshold = map_strength_to_threshold(strength)
        print(f"[DEBUG] Mapped shadow_strength={strength} → threshold={threshold}")
        shadow_tex1 = self.bake_and_process(
            context,
            margin=0.01,
            texture_name_suffix="Bake1",
            material=mat,
            threshold=threshold
        )

        # Apply edge softening effect
        self.blur_texture_edges(mat, shadow_tex1)
        print("[DEBUG] Blur node setup complete")
        
        # Assign final texture to ShadowPlane material
        self.assign_final_texture(shadow_plane, shadow_tex1)
        print("[DEBUG] Final texture assigned")

        # Bake the blurred texture to a UV image and assign it to the shadow plane
        blurred_texture_image = self.bake_blurred_texture_to_image(context, shadow_plane, mat)
        print(f"[DEBUG] Blurred texture bake done, image: {blurred_texture_image.name}")

        # **Remove Shadow_bake1 texture after baking**
        print("[DEBUG] Cleanup phase started")
        if "Shadow_Bake1" in bpy.data.images:
            bpy.data.images.remove(bpy.data.images["Shadow_Bake1"])
            
        # Remove ShadowPlane after baking is done
        bpy.data.objects.remove(shadow_plane, do_unlink=True)

        # Cleanup
        bpy.data.objects.remove(lamp_positive)
        scene.render.engine = original_engine
        
        print("[DEBUG] BakeShadow operator complete")

        # Deselect objects
        if context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')

    def restore_selection(self, context, original_selection, original_active):
        """Restores the original selection and active object after baking."""
        # Deselect all objects first
        bpy.ops.object.select_all(action='DESELECT')
        
        # Reselect the original objects
        for obj in original_selection:
            obj.select_set(True)
            
        # Restore the original active object
        context.view_layer.objects.active = original_active

    def execute(self, context):
        if not self.check_for_selected(context):
            return {'CANCELLED'}

        original_active = context.view_layer.objects.active
        original_selection = context.selected_objects[:]

        self.bake_shadow(context)

        self.restore_selection(context, original_selection, original_active)

        # Replace confirm_shadow_save with a message box
        msg_box("'shadow' has been baked and\n can be found in the Texture Images list.", "INFO")

        return {"FINISHED"}
    
class BakeVertex(bpy.types.Operator):
    """Bake lighting to vertex colors and apply changes to the _Col material."""
    bl_idname = "object.bake_vertex"
    bl_label = "Bake Light to Vertex Color"
    bl_options = {'REGISTER', 'UNDO'}
    
    shadow_strength: bpy.props.FloatProperty(
        name="Shadow Strength",
        description="Strength of the shadows",
        default=5.0,
        min=0.0,
        max=10.0
    )

    light_strength: bpy.props.FloatProperty(
        name="Light Strength",
        description="Strength of the light rays",
        default=0.5,
        min=0.0,
        max=10.0
    )
    
    samples: bpy.props.IntProperty(
        name="Samples",
        description="Number of samples for baking",
        default=512,
        min=1,
        max=5000
    )
    
    def get_base_name_for_layers(self, obj):
        base_name = obj.name.split('.')[0]
        extension = ""

        specific_parts = ["body", "wheel", "axle", "spring"]

        if ".w" in obj.name:
            extension = ".w"
        elif ".prm" in obj.name or any(part in obj.name for part in specific_parts):
            extension = ".prm"

        return f"{base_name}{extension}"

    def execute(self, context):
        scene = context.scene
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            self.report({'WARNING'}, "Active object is not a mesh")
            return {'CANCELLED'}

        # Check if the object is in Object mode
        if obj.mode != 'OBJECT':
            self.report({'WARNING'}, "You must be in Object Mode to bake vertex colors.")
            msg_box("You must be in Object Mode to bake vertex colors.", 'ERROR')
            return {'CANCELLED'}

        # Ensure the object has a vertex color layer named 'Col'
        vc_layer = obj.data.vertex_colors.get('Col')
        if not vc_layer:
            vc_layer = obj.data.vertex_colors.new(name='Col')
        obj.data.vertex_colors.active = vc_layer

        # Preserve the original vertex colors
        original_vcols = [loop.color[:] for loop in vc_layer.data]

        # Create temporary vertex color layers for baking
        temp_ao_vc_layer = obj.data.vertex_colors.new(name='TempBakeAO')
        temp_direct_vc_layer = obj.data.vertex_colors.new(name='TempBakeDirect')
        obj.data.vertex_colors.active = temp_ao_vc_layer

        # Set render engine to Cycles and configure settings
        original_engine = scene.render.engine
        scene.render.engine = 'CYCLES'
        original_samples = scene.cycles.samples
        scene.cycles.samples = self.samples

        # Ensure the material setup is correct
        base_name = self.get_base_name_for_layers(obj)
        prefixed_mat_name = f"{base_name}_Col"
        generic_mat_name = "_Col"

        material = bpy.data.materials.get(prefixed_mat_name) or bpy.data.materials.get(generic_mat_name)
        if not material:
            self.report({'WARNING'}, f"Material {prefixed_mat_name} or {generic_mat_name} not found.")
            return {'CANCELLED'}

        # Ensure material is in object material slot
        if material.name not in obj.data.materials:
            obj.data.materials.append(material)

        # Prepare vertex color material node setup with Principled BSDF
        if not material.use_nodes:
            material.use_nodes = True
        nodes = material.node_tree.nodes
        links = material.node_tree.links
        nodes.clear()
        vcol_node = nodes.new(type='ShaderNodeVertexColor')
        bsdf_node = nodes.new(type='ShaderNodeBsdfPrincipled')
        output_node = nodes.new(type='ShaderNodeOutputMaterial')
        links.new(vcol_node.outputs['Color'], bsdf_node.inputs['Base Color'])
        links.new(bsdf_node.outputs['BSDF'], output_node.inputs['Surface'])

        # Ensure the active mesh object is selected
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.ops.object.mode_set(mode='OBJECT')

        # Bake the ambient occlusion (AO) to the temporary vertex color layer
        vcol_node.layer_name = temp_ao_vc_layer.name
        bpy.ops.object.bake(type='AO', use_clear=True, use_selected_to_active=False, margin=2, cage_extrusion=0.0, normal_space='TANGENT', target='VERTEX_COLORS')

        # Switch to the temporary direct lighting vertex color layer
        obj.data.vertex_colors.active = temp_direct_vc_layer

        # Bake the direct lighting to the temporary vertex color layer
        vcol_node.layer_name = temp_direct_vc_layer.name
        bpy.ops.object.bake(type='DIFFUSE', use_clear=True, use_selected_to_active=False, margin=2, cage_extrusion=0.0, normal_space='TANGENT', pass_filter={'DIRECT'}, target='VERTEX_COLORS')

        # Merge the baked AO and direct lighting with the original colors using bmesh
        bm = bmesh.new()
        bm.from_mesh(obj.data)

        # Access vertex color layers in bmesh
        vc_layer_bm = bm.loops.layers.color.get('Col')
        temp_ao_vc_layer_bm = bm.loops.layers.color.get('TempBakeAO')
        temp_direct_vc_layer_bm = bm.loops.layers.color.get('TempBakeDirect')

        for face in bm.faces:
            for loop in face.loops:
                original_color = loop[vc_layer_bm]
                ao_color = loop[temp_ao_vc_layer_bm]
                direct_color = loop[temp_direct_vc_layer_bm]
                # Blend the original color with the AO shadow and direct lighting
                blended_color = [
                    original_color[j] * (1 - self.shadow_strength * (1 - ao_color[j])) + self.light_strength * direct_color[j]
                    for j in range(3)
                ]
                loop[vc_layer_bm] = blended_color + [1.0]

        # Update the mesh
        bm.to_mesh(obj.data)
        bm.free()

        # Delete the temporary vertex color layers
        obj.data.vertex_colors.remove(temp_ao_vc_layer)
        obj.data.vertex_colors.remove(temp_direct_vc_layer)

        # Cleanup and restore settings
        scene.render.engine = original_engine
        scene.cycles.samples = original_samples

        # Restore the correct vertex color layer in the material
        vcol_node.layer_name = 'Col'

        obj.select_set(True)
        context.view_layer.objects.active = obj
        context.view_layer.update()

        self.report({'INFO'}, "Baking completed successfully")
        return {'FINISHED'}
    
    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

class BakeVertexBatch(bpy.types.Operator):
    """Bake lighting to vertex colors on all selected mesh objects."""
    bl_idname = "object.bake_vertex_batch"
    bl_label = "Bake Light to Vertex Color (Selected)"
    bl_options = {'REGISTER', 'UNDO'}

    shadow_strength: bpy.props.FloatProperty(
        name="Shadow Strength",
        description="Strength of the shadows",
        default=5.0,
        min=0.0,
        max=10.0
    )

    light_strength: bpy.props.FloatProperty(
        name="Light Strength",
        description="Strength of the light rays",
        default=0.5,
        min=0.0,
        max=10.0
    )

    # NEW — dropdown with allowed options only
    samples: bpy.props.EnumProperty(
        name="Samples",
        description="Number of samples for baking",
        items=[
            ('64',  "64",  "Fast preview"),
            ('128', "128", "Balanced"),
            ('256', "256", "High quality"),
            ('512', "512", "Very high quality"),
        ],
        default='64',
    )

    def execute(self, context):
        # Only mesh objects from the selection
        mesh_objects = [o for o in context.selected_objects if o.type == 'MESH']
        if not mesh_objects:
            self.report({'WARNING'}, "No mesh objects selected.")
            return {'CANCELLED'}

        prev_active = context.view_layer.objects.active

        # Loop all selected meshes and call the original operator on each
        for obj in mesh_objects:
            print(f"[BakeVertexBatch] Baking {obj.name}")
            context.view_layer.objects.active = obj

            # Call existing single-object bake operator without UI
            bpy.ops.object.bake_vertex(
                'EXEC_DEFAULT',
                shadow_strength=self.shadow_strength,
                light_strength=self.light_strength,
                samples=int(self.samples)       # IMPORTANT: convert enum string to int
            )

        # Restore previous active object
        context.view_layer.objects.active = prev_active

        self.report({'INFO'}, f"Baked {len(mesh_objects)} mesh object(s)")
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
    
class BatchBakeVertexToEnv(bpy.types.Operator):
    """Batch Bake lighting to vertex colors and apply changes to the _Env material."""
    bl_idname = "object.batch_bake_vertex_to_env"
    bl_label = "Batch Bake Light to Vertex Color for _Env"
    bl_options = {'REGISTER', 'UNDO'}
    
    shadow_strength: bpy.props.FloatProperty(
        name="Shadow Strength",
        description="Strength of the shadows",
        default=5.0,
        min=0.0,
        max=10.0
    )

    light_strength: bpy.props.FloatProperty(
        name="Light Strength",
        description="Strength of the light rays",
        default=0.5,
        min=0.0,
        max=10.0
    )
    
    # CHANGED: EnumProperty with fixed options
    samples: bpy.props.EnumProperty(
        name="Samples",
        description="Number of samples for baking",
        items=[
            ('64',  "64",  "Fast preview"),
            ('128', "128", "Balanced"),
            ('256', "256", "High quality"),
            ('512', "512", "Very high quality"),
        ],
        default='64',
    )
    
    def get_base_name_for_layers(self, obj):
        base_name = obj.name.split('.')[0]
        extension = ""

        specific_parts = ["body", "wheel", "axle", "spring"]

        if ".w" in obj.name:
            extension = ".w"
        elif ".prm" in obj.name or any(part in obj.name for part in specific_parts):
            extension = ".prm"

        return f"{base_name}{extension}"

    def batch_bake(self, context):
        scene = context.scene

        # Set render engine to Cycles and configure settings
        original_engine = scene.render.engine
        scene.render.engine = 'CYCLES'
        original_samples = scene.cycles.samples
        scene.cycles.samples = int(self.samples)  # CHANGED: cast enum string to int

        # Bakes all selected objects
        for obj in context.selected_objects:
            if (
                obj.type != 'MESH'
                or not hasattr(obj.data, "vertex_colors")
                or not (getattr(obj, "is_instance", False) or obj.get("is_instance", False))
            ):
                continue

            print(f"Baking at {obj.name}...")
            context.view_layer.objects.active = obj

            # Ensure the object has a vertex color layer named 'Env'
            env_layer = obj.data.vertex_colors.get('Env')
            if not env_layer:
                env_layer = obj.data.vertex_colors.new(name='Env')
            obj.data.vertex_colors.active = env_layer

            # Preserve the original vertex colors
            original_vcols = [loop.color[:] for loop in env_layer.data]

            # Create temporary vertex color layers for baking
            temp_ao_env_layer = obj.data.vertex_colors.new(name='TempBakeAO')
            temp_direct_env_layer = obj.data.vertex_colors.new(name='TempBakeDirect')
            obj.data.vertex_colors.active = temp_ao_env_layer

            # Ensure the material setup is correct
            base_name = self.get_base_name_for_layers(obj)
            prefixed_mat_name = f"{base_name}_Env"
            generic_mat_name = "_Env"

            material = bpy.data.materials.get(prefixed_mat_name) or bpy.data.materials.get(generic_mat_name)
            if not material:
                self.report({'WARNING'}, f"Material {prefixed_mat_name} or {generic_mat_name} not found.")
                continue

            # Ensure material is in object material slot
            if material.name not in obj.data.materials:
                obj.data.materials.append(material)

            # Prepare vertex color material node setup with Principled BSDF
            if not material.use_nodes:
                material.use_nodes = True
            nodes = material.node_tree.nodes
            links = material.node_tree.links
            nodes.clear()
            vcol_node = nodes.new(type='ShaderNodeVertexColor')
            vcol_node.layer_name = 'Env'
            bsdf_node = nodes.new(type='ShaderNodeBsdfPrincipled')
            output_node = nodes.new(type='ShaderNodeOutputMaterial')
            links.new(vcol_node.outputs['Color'], bsdf_node.inputs['Base Color'])
            links.new(bsdf_node.outputs['BSDF'], output_node.inputs['Surface'])

            # Ensure the active mesh object is selected
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            bpy.ops.object.mode_set(mode='OBJECT')

            # Bake the ambient occlusion (AO) to the temporary vertex color layer
            bpy.ops.object.bake(
                type='AO',
                use_clear=True,
                use_selected_to_active=False,
                margin=2,
                cage_extrusion=0.0,
                normal_space='TANGENT',
                target='VERTEX_COLORS'
            )

            # Switch to the temporary direct lighting vertex color layer
            obj.data.vertex_colors.active = temp_direct_env_layer

            # Bake the direct lighting to the temporary vertex color layer
            bpy.ops.object.bake(
                type='DIFFUSE',
                use_clear=True,
                use_selected_to_active=False,
                margin=2,
                cage_extrusion=0.0,
                normal_space='TANGENT',
                pass_filter={'DIRECT'},
                target='VERTEX_COLORS'
            )

            # Merge the baked AO and direct lighting with the original colors using bmesh
            bm = bmesh.new()
            bm.from_mesh(obj.data)

            # Access vertex color layers in bmesh
            env_layer_bm = bm.loops.layers.color.get('Env')
            temp_ao_env_layer_bm = bm.loops.layers.color.get('TempBakeAO')
            temp_direct_env_layer_bm = bm.loops.layers.color.get('TempBakeDirect')

            for face in bm.faces:
                for loop in face.loops:
                    original_color = loop[env_layer_bm]
                    ao_color = loop[temp_ao_env_layer_bm]
                    direct_color = loop[temp_direct_env_layer_bm]
                    blended_color = [
                        original_color[j] * (1 - self.shadow_strength * (1 - ao_color[j])) +
                        self.light_strength * direct_color[j]
                        for j in range(3)
                    ]
                    loop[env_layer_bm] = blended_color + [original_color[3]]  # Preserve original alpha

            # Update the mesh
            bm.to_mesh(obj.data)
            bm.free()

            # Delete the temporary vertex color layers
            obj.data.vertex_colors.remove(temp_ao_env_layer)
            obj.data.vertex_colors.remove(temp_direct_env_layer)

        # Cleanup and restore settings
        scene.render.engine = original_engine
        scene.cycles.samples = original_samples

    def execute(self, context):
        self.batch_bake(context)
        self.report({'INFO'}, "Batch baking completed successfully")
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

class BakeVertexToRGBModelColor(bpy.types.Operator):
    """Bake lighting to vertex colors and apply changes to the _RGBModelColor material."""
    bl_idname = "object.bake_vertex_to_rgbmodelcolor"
    bl_label = "Bake Light to Vertex Color for RGBModelColor"
    bl_options = {'REGISTER', 'UNDO'}
    
    shadow_strength: bpy.props.FloatProperty(
        name="Shadow Strength",
        description="Strength of the shadows",
        default=5.0,
        min=0.0,
        max=10.0
    )

    light_strength: bpy.props.FloatProperty(
        name="Light Strength",
        description="Strength of the light rays",
        default=0.5,
        min=0.0,
        max=10.0
    )
    
    # CHANGED: EnumProperty with fixed options
    samples: bpy.props.EnumProperty(
        name="Samples",
        description="Number of samples for baking",
        items=[
            ('64',  "64",  "Fast preview"),
            ('128', "128", "Balanced"),
            ('256', "256", "High quality"),
            ('512', "512", "Very high quality"),
        ],
        default='64',
    )
    
    def get_base_name_for_layers(self, obj):
        base_name = obj.name.split('.')[0]
        extension = ""

        specific_parts = ["body", "wheel", "axle", "spring"]

        if ".w" in obj.name:
            extension = ".w"
        elif ".prm" in obj.name or any(part in obj.name for part in specific_parts):
            extension = ".prm"

        return f"{base_name}{extension}"

    def batch_bake(self, context):
        scene = context.scene

        # Set render engine to Cycles and configure settings
        original_engine = scene.render.engine
        scene.render.engine = 'CYCLES'
        original_samples = scene.cycles.samples
        scene.cycles.samples = int(self.samples)  # CHANGED: cast enum string to int

        # Bakes all selected objects
        for obj in context.selected_objects:
            if (
                obj.type != 'MESH'
                or not hasattr(obj.data, "vertex_colors")
                or not (getattr(obj, "is_instance", False) or obj.get("is_instance", False))
            ):
                continue

            print(f"Baking at {obj.name}...")
            context.view_layer.objects.active = obj

            # Ensure the object has a vertex color layer named 'RGBModelColor'
            rgb_layer = obj.data.vertex_colors.get('RGBModelColor')
            if not rgb_layer:
                rgb_layer = obj.data.vertex_colors.new(name='RGBModelColor')
            obj.data.vertex_colors.active = rgb_layer

            # Preserve the original vertex colors
            original_vcols = [loop.color[:] for loop in rgb_layer.data]

            # Create temporary vertex color layers for baking
            temp_ao_rgb_layer = obj.data.vertex_colors.new(name='TempBakeAO')
            temp_direct_rgb_layer = obj.data.vertex_colors.new(name='TempBakeDirect')
            obj.data.vertex_colors.active = temp_ao_rgb_layer

            # Ensure the material setup is correct
            base_name = self.get_base_name_for_layers(obj)
            prefixed_mat_name = f"{base_name}_RGBModelColor"
            generic_mat_name = "_RGBModelColor"

            material = bpy.data.materials.get(prefixed_mat_name) or bpy.data.materials.get(generic_mat_name)
            if not material:
                self.report({'WARNING'}, f"Material {prefixed_mat_name} or {generic_mat_name} not found.")
                continue

            # Ensure material is in object material slot
            if material.name not in obj.data.materials:
                obj.data.materials.append(material)

            # Prepare vertex color material node setup with Principled BSDF
            if not material.use_nodes:
                material.use_nodes = True
            nodes = material.node_tree.nodes
            links = material.node_tree.links
            nodes.clear()
            vcol_node = nodes.new(type='ShaderNodeVertexColor')
            vcol_node.layer_name = 'RGBModelColor'
            bsdf_node = nodes.new(type='ShaderNodeBsdfPrincipled')
            output_node = nodes.new(type='ShaderNodeOutputMaterial')
            links.new(vcol_node.outputs['Color'], bsdf_node.inputs['Base Color'])
            links.new(bsdf_node.outputs['BSDF'], output_node.inputs['Surface'])

            # Ensure the active mesh object is selected
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            bpy.ops.object.mode_set(mode='OBJECT')

            # Bake the ambient occlusion (AO) to the temporary vertex color layer
            bpy.ops.object.bake(
                type='AO',
                use_clear=True,
                use_selected_to_active=False,
                margin=2,
                cage_extrusion=0.0,
                normal_space='TANGENT',
                target='VERTEX_COLORS'
            )

            # Switch to the temporary direct lighting vertex color layer
            obj.data.vertex_colors.active = temp_direct_rgb_layer

            # Bake the direct lighting to the temporary vertex color layer
            bpy.ops.object.bake(
                type='DIFFUSE',
                use_clear=True,
                use_selected_to_active=False,
                margin=2,
                cage_extrusion=0.0,
                normal_space='TANGENT',
                pass_filter={'DIRECT'},
                target='VERTEX_COLORS'
            )

            # Merge the baked AO and direct lighting with the original colors using bmesh
            bm = bmesh.new()
            bm.from_mesh(obj.data)

            # Access vertex color layers in bmesh
            rgb_layer_bm = bm.loops.layers.color.get('RGBModelColor')
            temp_ao_rgb_layer_bm = bm.loops.layers.color.get('TempBakeAO')
            temp_direct_rgb_layer_bm = bm.loops.layers.color.get('TempBakeDirect')

            for face in bm.faces:
                for loop in face.loops:
                    original_color = loop[rgb_layer_bm]
                    ao_color = loop[temp_ao_rgb_layer_bm]
                    direct_color = loop[temp_direct_rgb_layer_bm]
                    blended_color = [
                        original_color[j] * (1 - self.shadow_strength * (1 - ao_color[j])) +
                        self.light_strength * direct_color[j]
                        for j in range(3)
                    ]
                    loop[rgb_layer_bm] = blended_color + [1.0]

            # Update the mesh
            bm.to_mesh(obj.data)
            bm.free()

            # Delete the temporary vertex color layers
            obj.data.vertex_colors.remove(temp_ao_rgb_layer)
            obj.data.vertex_colors.remove(temp_direct_rgb_layer)

        # Cleanup and restore settings
        scene.render.engine = original_engine
        scene.cycles.samples = original_samples

    def execute(self, context):
        self.batch_bake(context)
        self.report({'INFO'}, "Batch baking completed successfully")
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

"""
TEXTURE ANIMATIONS -------------------------------------------------------
"""

class ButtonCopyUvToFrame(bpy.types.Operator):
    bl_idname = "texanim.copy_uv_to_frame"
    bl_label = "UV to Frame"
    bl_description = "Copies the UV coordinates of the currently selected face to the texture animation frame"

    def execute(self, context):
        copy_uv_to_frame(context)
        context.area.tag_redraw()
        return{"FINISHED"}

class ButtonCopyFrameToUv(bpy.types.Operator):
    bl_idname = "texanim.copy_frame_to_uv"
    bl_label = "Frame to UV"
    bl_description = "Copies the UV coordinates of the frame to the currently selected face"

    def execute(self, context):
        scene = context.scene

        if scene.ta_max_frames == 0:
            msg_box("Slot is empty. No animation frame to copy.", "INFO")
            return {"CANCELLED"}

        copy_frame_to_uv(context)
        context.area.tag_redraw()
        return {"FINISHED"}
    
class PreviewNextFrame(bpy.types.Operator):
    bl_idname = "texanim.prev_next"
    bl_label = "Preview Next"
    bl_description = "Loads the next frame and previews it on the selected face"

    def execute(self, context):
        scene = context.scene

        # ❌ No animation assigned
        if scene.ta_max_frames == 0:
            msg_box("Slot is empty. No animation to preview.", "INFO")
            return {"CANCELLED"}

        # Ensure we don't go beyond the maximum number of frames
        if scene.ta_current_frame < scene.ta_max_frames - 1:
            scene.ta_current_frame += 1
        else:
            scene.ta_current_frame = 0  # Loop

        copy_frame_to_uv(context)

        if context.area:
            context.area.tag_redraw()

        return {"FINISHED"}

class PreviewPrevFrame(bpy.types.Operator):
    bl_idname = "texanim.prev_prev"
    bl_label = "Preview Previous"
    bl_description = "Loads the previous frame and previews it on the selected face"

    def execute(self, context):
        scene = context.scene

        # ❌ No animation assigned
        if scene.ta_max_frames == 0:
            msg_box("Slot is empty. No animation to preview.", "INFO")
            return {"CANCELLED"}

        # Ensure we don't go below the first frame
        if scene.ta_current_frame > 0:
            scene.ta_current_frame -= 1
        else:
            scene.ta_current_frame = scene.ta_max_frames - 1  # Loop

        copy_frame_to_uv(context)

        if context.area:
            context.area.tag_redraw()

        return {"FINISHED"}

class TexAnimTransform(bpy.types.Operator):
    bl_idname = "texanim.transform"
    bl_label = "Transform Animation"
    bl_description = "Creates a linear animation from one frame to another"

    def execute(self, context):
        scene = context.scene
        
        # Check if the slot limit is 0
        if scene.ta_max_slots == 0:
            msg_box("Slot limit is 0. Please increase the slot limit before creating an animation.", "ERROR")
            return {'FINISHED'}

        ta = eval(scene.texture_animations)
        slot = scene.ta_current_slot

        if slot >= len(ta):
            msg_box("Slot index out of range.", "ERROR")
            return {'FINISHED'}

        max_frames = scene.ta_max_frames
        frame_start = scene.ta_frame_start
        frame_end = scene.ta_frame_end

        # Bounds check against current slot's max_frames
        if frame_start >= max_frames or frame_end >= max_frames:
            msg_box("Frame index out of range. Please increase Frames Limit if needed.", "ERROR")
            return {'FINISHED'}

        # Remember original values for the message
        orig_start = frame_start
        orig_end = frame_end

        # Ensure start <= end for interpolation math
        if frame_end < frame_start:
            frame_start, frame_end = frame_end, frame_start

        # Shortcut: if start == end, nothing to interpolate – just ensure delay/texture are set
        if frame_start == frame_end:
            idx = frame_start
            ta[slot]["frames"][idx]["delay"] = scene.ta_delay
            ta[slot]["frames"][idx]["texture"] = scene.ta_texture
            # No UV change needed, but we could also copy current frame UVs here if desired

            scene.texture_animations = str(ta)
            update_ta_current_frame(self, context)

            msg_box(f"Single-frame transform applied at frame {idx}.", icon="FILE_TICK")
            return {'FINISHED'}

        # Read UVs from the start frame
        uv_start = (
            (ta[slot]["frames"][frame_start]["uv"][0]["u"],
             ta[slot]["frames"][frame_start]["uv"][0]["v"]),
            (ta[slot]["frames"][frame_start]["uv"][1]["u"],
             ta[slot]["frames"][frame_start]["uv"][1]["v"]),
            (ta[slot]["frames"][frame_start]["uv"][2]["u"],
             ta[slot]["frames"][frame_start]["uv"][2]["v"]),
            (ta[slot]["frames"][frame_start]["uv"][3]["u"],
             ta[slot]["frames"][frame_start]["uv"][3]["v"])
        )

        # And from the end frame
        uv_end = (
            (ta[slot]["frames"][frame_end]["uv"][0]["u"],
             ta[slot]["frames"][frame_end]["uv"][0]["v"]),
            (ta[slot]["frames"][frame_end]["uv"][1]["u"],
             ta[slot]["frames"][frame_end]["uv"][1]["v"]),
            (ta[slot]["frames"][frame_end]["uv"][2]["u"],
             ta[slot]["frames"][frame_end]["uv"][2]["v"]),
            (ta[slot]["frames"][frame_end]["uv"][3]["u"],
             ta[slot]["frames"][frame_end]["uv"][3]["v"])
        )

        nframes = (frame_end - frame_start) + 1
        denom = (frame_end - frame_start)

        for i in range(nframes):
            current_frame = frame_start + i
            prog = i / denom  # safe because frame_end != frame_start here

            ta[slot]["frames"][current_frame]["delay"] = scene.ta_delay
            ta[slot]["frames"][current_frame]["texture"] = scene.ta_texture

            for j in range(4):
                new_u = uv_start[j][0] * (1 - prog) + uv_end[j][0] * prog
                new_v = uv_start[j][1] * (1 - prog) + uv_end[j][1] * prog

                ta[slot]["frames"][current_frame]["uv"][j]["u"] = new_u
                ta[slot]["frames"][current_frame]["uv"][j]["v"] = new_v

        # 🔸 IMPORTANT: do NOT touch frame_count here.
        # Transform only reshapes existing frames inside [frame_start, frame_end].
        # Frame count / allocation is handled when user sets Frames Limit (ta_max_frames)
        # and by Grid (which already updates frame_count safely).

        scene.texture_animations = str(ta)
        update_ta_current_frame(self, context)

        msg_box("Animation from frame {} to {} completed.".format(
            orig_start, orig_end),
            icon="FILE_TICK"
        )

        return {'FINISHED'}

class TexAnimGrid(bpy.types.Operator):
    bl_idname = "texanim.grid"
    bl_label = "Grid Animation"
    bl_description = "Creates an animation based on a grid texture."

    def execute(self, context):
        scene = context.scene

        # Check if the slot limit is 0
        if scene.ta_max_slots == 0:
            msg_box("Slot limit is 0. Please increase the slot limit before creating a grid animation.", "ERROR")
            return {'FINISHED'}

        ta = eval(scene.texture_animations)
        slot = scene.ta_current_slot

        if slot >= len(ta):
            msg_box("Slot index out of range.", "ERROR")
            return {'FINISHED'}

        # Current info for this slot
        max_frames = scene.ta_max_frames
        frame_start = scene.ta_frame_start
        grid_x = scene.grid_x
        grid_y = scene.grid_y
        nframes = grid_x * grid_y

        # We need at least frame_start + nframes frames available
        needed_frames = frame_start + nframes

        # If the UI limit is too small, warn the user (keeps existing behaviour)
        if needed_frames > max_frames:
            msg_box(
                "Frame out of range.\n"
                "Please set the amount of frames to at least {}.".format(needed_frames),
                "ERROR"
            )
            return {'FINISHED'}

        # Ensure the internal frames list is large enough for this slot
        # (in case something got out of sync)
        frames_list = ta[slot]["frames"]
        while len(frames_list) < needed_frames:
            new_frame = rvstruct.Frame().as_dict()
            frames_list.append(new_frame)

        i = 0
        for y in range(grid_x):
            for x in range(grid_y):
                uv0 = (x / grid_x,     y / grid_y)
                uv1 = ((x + 1) / grid_x, y / grid_y)
                uv2 = ((x + 1) / grid_x, (y + 1) / grid_y)
                uv3 = (x / grid_x,     (y + 1) / grid_y)

                idx = frame_start + i

                frames_list[idx]["delay"] = scene.ta_delay
                frames_list[idx]["texture"] = scene.ta_texture

                frames_list[idx]["uv"][0]["u"] = uv0[0]
                frames_list[idx]["uv"][0]["v"] = uv0[1]
                frames_list[idx]["uv"][1]["u"] = uv1[0]
                frames_list[idx]["uv"][1]["v"] = uv1[1]
                frames_list[idx]["uv"][2]["u"] = uv2[0]
                frames_list[idx]["uv"][2]["v"] = uv2[1]
                frames_list[idx]["uv"][3]["u"] = uv3[0]
                frames_list[idx]["uv"][3]["v"] = uv3[1]

                i += 1

        # 🔹 Update frame_count so export writes ALL generated frames
        ta[slot]["frame_count"] = max(ta[slot].get("frame_count", 0), needed_frames)

        # Keep UI in sync with actual data
        scene.ta_max_frames = ta[slot]["frame_count"]

        # Store back once with the updated frame_count
        scene.texture_animations = str(ta)

        # Refresh current frame UI
        update_ta_current_frame(self, context)

        msg_box("Animation of {} frames completed.".format(nframes), icon="FILE_TICK")

        return {'FINISHED'}

class TexAnimAssignSlot(bpy.types.Operator):
    bl_idname = "texanim.assign_anim_slot"
    bl_label = "Assign Animation"
    bl_description = "Enable texture animation on selected faces (sets FACE_TEXANIM in Type)"

    def execute(self, context):
        scene = context.scene
        obj = context.object

        if not obj or obj.type != 'MESH' or not obj.data:
            msg_box("Please select a valid mesh object in Edit Mode.", "ERROR")
            return {'CANCELLED'}

        if obj.mode != 'EDIT':
            bpy.ops.object.mode_set(mode='EDIT')

        import bmesh
        bm = bmesh.from_edit_mesh(obj.data)

        type_layer = bm.faces.layers.int.get("Type")
        if type_layer is None:
            type_layer = bm.faces.layers.int.new("Type")

        selected_faces = [f for f in bm.faces if f.select]
        if not selected_faces:
            msg_box("Please select at least one face.", "ERROR")
            return {'CANCELLED'}

        for f in selected_faces:
            f[type_layer] |= FACE_TEXANIM

        bmesh.update_edit_mesh(obj.data)
        if context.area:
            context.area.tag_redraw()

        # Success message
        msg_box(f"Animation assigned to {len(selected_faces)} face(s).", "INFO")

        return {'FINISHED'}

class TexAnimClearSelectedFaces(bpy.types.Operator):
    bl_idname = "texanim.clear_selected_faces"
    bl_label = "Remove Assign (Selected Faces)"
    bl_description = "Disable texture animation on selected faces (clears FACE_TEXANIM from Type)"

    def execute(self, context):
        obj = context.object
        if not obj or obj.type != 'MESH' or not obj.data:
            msg_box("Please select a valid mesh object in Edit Mode.", "ERROR")
            return {'CANCELLED'}

        if obj.mode != 'EDIT':
            bpy.ops.object.mode_set(mode='EDIT')

        import bmesh
        bm = bmesh.from_edit_mesh(obj.data)

        type_layer = bm.faces.layers.int.get("Type")
        if type_layer is None:
            msg_box("No 'Type' layer found on this mesh.", "ERROR")
            return {'CANCELLED'}

        selected_faces = [f for f in bm.faces if f.select]
        if not selected_faces:
            msg_box("Please select at least one face.", "ERROR")
            return {'CANCELLED'}

        for f in selected_faces:
            f[type_layer] &= ~FACE_TEXANIM

        bmesh.update_edit_mesh(obj.data)
        if context.area:
            context.area.tag_redraw()

        # Success message
        msg_box(f"Animation removed from {len(selected_faces)} face(s).", "INFO")

        return {'FINISHED'}

class TexAnimClearCurrentSlot(bpy.types.Operator):
    bl_idname = "texanim.clear_current_slot"
    bl_label = "Clear Current Slot"
    bl_description = "Reset current texture animation slot data (frames + frame_count) to defaults"

    def execute(self, context):
        scene = context.scene

        if scene.ta_max_slots == 0:
            msg_box("No slots exist (Slots Limit is 0).", "ERROR")
            return {'CANCELLED'}

        ta = eval(scene.texture_animations)
        slot = scene.ta_current_slot

        if slot < 0 or slot >= len(ta):
            msg_box("Slot index out of range.", "ERROR")
            return {'CANCELLED'}

        # Reset slot dict completely, keep list length
        ta[slot] = rvstruct.TexAnimation().as_dict()

        # Keep UI in sync
        scene.texture_animations = str(ta)
        scene.ta_max_frames = ta[slot]["frame_count"]
        scene.ta_current_frame = 0
        update_ta_current_frame(self, context)

        msg_box(f"Slot {slot} cleared.", icon="TRASH")
        return {'FINISHED'}
    

"""
VERTEX COLORS -----------------------------------------------------------------
"""

class VertexAndAlphaLayer(bpy.types.Operator):
    """Setup Vertex Color and Alpha Layers and create generic named materials if they do not exist."""
    bl_idname = "mesh.vertex_color_and_alpha_setup"
    bl_label = "Setup Vertex Color and Alpha Layers"
    bl_description = "Creates necessary vertex color layers and materials if they do not exist."

    @classmethod
    def poll(cls, context):
        obj = context.object
        return obj and obj.type == 'MESH' and obj.mode == 'EDIT'

    def execute(self, context):
        for obj in context.selected_objects:
            if obj.type == 'MESH':
                mesh = obj.data
                bm = bmesh.from_edit_mesh(mesh)

                # Define the layers to be checked or created
                layers = ['Col', 'Alpha']

                for layer_name in layers:
                    # Check if the specific layer already exists
                    created_layer = bm.loops.layers.color.get(layer_name)
                    if not created_layer:
                        created_layer = bm.loops.layers.color.new(layer_name)
                        # Default alpha layer should start fully transparent (black)
                        default_color = (0.0, 0.0, 0.0, 1.0) if layer_name == 'Alpha' else (1.0, 1.0, 1.0, 1.0)
                        for face in bm.faces:
                            if face.select:  # Apply to selected faces only
                                for loop in face.loops:
                                    loop[created_layer] = default_color
                        self.report({'INFO'}, f"{layer_name} vertex color layer created for {obj.name}.")
                    else:
                        for face in bm.faces:
                            if face.select:  # Ensure selected faces have the correct layer data
                                for loop in face.loops:
                                    loop[created_layer] = (0.0, 0.0, 0.0, 1.0 if layer_name == 'Alpha' else 1.0)
                        self.report({'INFO'}, f"{layer_name} vertex color layer already exists for {obj.name}.")

                bmesh.update_edit_mesh(mesh, destructive=True)

                # Ensure materials are set up for the layers and assigned to selected faces
                self.setup_materials(obj, layers)
                self.reassign_materials_to_selected_faces(bm, obj, layers)

                # Recreate the vertex color and alpha layers if they were removed
                self.reapply_vertex_colors_to_selected_faces(bm, layers, mesh)

                # Trigger the MaterialAssignment operator to assign materials automatically
                bpy.ops.object.assign_materials()

        return {'FINISHED'}

    def setup_materials(self, obj, attributes):
        obj_name = obj.name.split('.')[0]  # Get the base name of the object
        
        # Define the potential shared material names based on the "worldname"
        worldname_materials = {attr_name: f"{obj_name}.w_{attr_name}" for attr_name in attributes}
        
        for attr_name in attributes:
            # First, try to find an existing material with the specific worldname
            material = bpy.data.materials.get(worldname_materials[attr_name])

            if not material:
                # If the specific worldname material doesn't exist, check for a generic one
                mat_name_generic = f"_{attr_name}"
                material = bpy.data.materials.get(mat_name_generic)

                if not material:
                    # If no generic material exists, create one
                    material = bpy.data.materials.new(name=mat_name_generic)
                    material.use_nodes = True
                    nodes = material.node_tree.nodes
                    nodes.clear()
                    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
                    output = nodes.new('ShaderNodeOutputMaterial')
                    vcol = nodes.new('ShaderNodeVertexColor')
                    vcol.layer_name = attr_name
                    bsdf.inputs['Base Color'].default_value = (0.5, 0.5, 0.5, 1.0) if attr_name == 'Alpha' else (1.0, 1.0, 1.0, 1.0)
                    material.node_tree.links.new(vcol.outputs['Color'], bsdf.inputs['Base Color'])
                    material.node_tree.links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
                    self.report({'INFO'}, f"Col/Alpha material created.")
            
            # Ensure the material is assigned to the object
            if material.name not in obj.data.materials:
                obj.data.materials.append(material)

    def reassign_materials_to_selected_faces(self, bm, obj, attributes):
        for face in bm.faces:
            if face.select:
                for attr_name in attributes:
                    material_index = obj.data.materials.find(f"_{attr_name}")
                    if material_index != -1:
                        face.material_index = material_index

        bmesh.update_edit_mesh(obj.data, destructive=True)

    def reapply_vertex_colors_to_selected_faces(self, bm, layers, mesh):
        for layer_name in layers:
            created_layer = bm.loops.layers.color.get(layer_name)
            if created_layer:
                for face in bm.faces:
                    if face.select:
                        for loop in face.loops:
                            loop[created_layer] = (0.0, 0.0, 0.0, 1.0) if layer_name == 'Alpha' else (1.0, 1.0, 1.0, 1.0)
        bmesh.update_edit_mesh(mesh, destructive=True)

class VertexColorRemove(bpy.types.Operator):
    bl_idname = "vertexcolor.remove_layer"
    bl_label = "Remove Vertex Color and Alpha Layers"
    bl_description = "Clears the active vertex color and alpha data from selected faces in the selected meshes"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.object
        return obj and obj.type == 'MESH' and obj.mode == 'EDIT'

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=420)

    def draw(self, context):
        layout = self.layout
        layout.label(text="Are you sure you want to remove the Vertex Colour + Alpha Layer?", icon='QUESTION')
        layout.label(text="This clears color/alpha on selected faces and unassigns _Col/_Alpha materials.")

    def execute(self, context):
        for obj in context.selected_objects:
            if obj.type == 'MESH':
                mesh = obj.data
                bm = bmesh.from_edit_mesh(mesh)

                vc_layer = bm.loops.layers.color.get("Col")
                va_layer = bm.loops.layers.color.get("Alpha")

                for face in bm.faces:
                    if face.select:
                        for loop in face.loops:
                            if vc_layer is not None:
                                loop[vc_layer] = (0.0, 0.0, 0.0, 1.0)
                            if va_layer is not None:
                                loop[va_layer] = (0.0, 0.0, 0.0, 1.0)

                bmesh.update_edit_mesh(mesh, destructive=True)

                materials_to_clear = [mat for mat in obj.data.materials
                                      if mat and (mat.name.endswith('_Col') or mat.name.endswith('_Alpha'))]

                for face in bm.faces:
                    if face.select:
                        for mat in materials_to_clear:
                            if face.material_index == obj.data.materials.find(mat.name):
                                face.material_index = 0

                bmesh.update_edit_mesh(mesh, destructive=True)

        self.report({'INFO'}, "Vertex color and alpha data cleared from selected faces, and materials cleared.")
        return {'FINISHED'}

class SetVertexColor(bpy.types.Operator):
    bl_idname = "vertexcolor.set_color"
    bl_label = "Set Vertex Color"
    bl_description = "Sets the vertex colors on the active vertex color layer using a scene-wide color picker"

    @classmethod
    def poll(cls, context):
        obj = context.object
        return obj and obj.type == 'MESH' and obj.mode == 'EDIT'

    def execute(self, context):
        for eo in context.selected_objects:
            if eo.type == 'MESH':
                bm = bmesh.from_edit_mesh(eo.data)

                vc_layer = bm.loops.layers.color.get("Col")
                if not vc_layer:
                    self.report({'WARNING'}, f"No active vertex color layer found for {eo.name}.")
                    continue

                selmode = context.tool_settings.mesh_select_mode
                color = context.scene.vertex_color_picker

                for face in bm.faces:
                    for loop in face.loops:
                        if (selmode[0] and loop.vert.select) or (selmode[1] and loop.edge.select) or (selmode[2] and face.select):
                            loop[vc_layer] = (color[0], color[1], color[2], 1.0)  # Set the alpha to 1.0

                bmesh.update_edit_mesh(eo.data, destructive=False)
                self.report({'INFO'}, f"Vertex color set for {eo.name}.")
        return {'FINISHED'}

class SetVertexAlpha(bpy.types.Operator):
    bl_idname = "vertexcolor.set_alpha"
    bl_label = "Set Vertex Alpha"
    bl_description = "Adjusts alpha on a specified vertex color layer for selected faces"

    @classmethod
    def poll(cls, context):
        return any(obj.type == 'MESH' for obj in context.selected_objects)

    def execute(self, context):
        for eo in context.selected_objects:
            if eo.type == 'MESH':
                bm = bmesh.from_edit_mesh(eo.data)

                va_layer = bm.loops.layers.color.get("Alpha")
                if not va_layer:
                    self.report({'WARNING'}, f"No vertex color layer with 'Alpha' in its name found for {eo.name}.")
                    continue

                # Retrieve the alpha percentage from the scene property and update the vertex_alpha
                alpha_percent = int(context.scene.vertex_alpha_percentage)
                alpha_value = alpha_percent / 100.0  # Normalize to 0-1
                context.scene.vertex_alpha = alpha_value  # Update the scene's vertex_alpha property

                grayscale_value = 1.0 - alpha_value  # Set color based on the inverse of alpha value

                for face in bm.faces:
                    if face.select:
                        for loop in face.loops:
                            loop[va_layer] = (grayscale_value, grayscale_value, grayscale_value, alpha_value)

                bmesh.update_edit_mesh(eo.data, destructive=False)
                self.report({'INFO'}, f"Alpha adjusted to {alpha_percent}% for selected faces on the chosen layer for {eo.name}.")
        return {'FINISHED'}

class CarAutoShader(bpy.types.Operator):
    bl_idname = "object.car_auto_shader"
    bl_label = "CAR AUTO SHADER"
    bl_description = "Bake lighting into vertex colors with base color"

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        scene = context.scene
        base_color = scene.car_shader_color
        selected_meshes = [obj for obj in context.selected_objects if obj.type == 'MESH']

        if not selected_meshes:
            self.report({'WARNING'}, "Select at least one mesh object to use Car Auto Shader.")
            return {'CANCELLED'}

        # Preserve the active color attribute so we don't end up previewing Alpha
        # after the bake adds / updates layers.
        active_color_by_object = {}

        for obj in selected_meshes:
            color_attrs = getattr(obj.data, "color_attributes", None)
            if color_attrs:
                active_attr = getattr(color_attrs, "active", None)
                active_color_by_object[obj.name] = active_attr.name if active_attr else None

        # --- Create temp lights in a safe way (scene collection, object mode) ---
        prev_active = context.view_layer.objects.active
        prev_mode = prev_active.mode if prev_active else 'OBJECT'

        if context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        def create_temp_light(name, location):
            light_data = bpy.data.lights.new(name=name, type='POINT')
            light_data.energy = 3500.0
            light_obj = bpy.data.objects.new(name, light_data)
            light_obj.location = BlenderVector(location)
            context.scene.collection.objects.link(light_obj)
            return light_obj

        temp_lights = [
            create_temp_light("TempLight1", (4, 1.5, 7)),
            create_temp_light("TempLight2", (-4, -1.5, 7)),
        ]

        # Cache light info (avoid property lookups in the hot loop)
        light_positions = [l.location.copy() for l in temp_lights]
        light_energies = [float(l.data.energy) for l in temp_lights]
        light_count = len(temp_lights)

        try:
            # Process each selected mesh
            for obj in selected_meshes:
                if not obj.visible_get():
                    continue

                me = obj.data
                bm = bmesh.new()
                bm.from_mesh(me)
                bm.verts.ensure_lookup_table()
                bm.faces.ensure_lookup_table()

                # Ensure layers exist (BMesh loop color layers)
                col_layer = bm.loops.layers.color.get("Col") or bm.loops.layers.color.new("Col")
                alpha_layer = bm.loops.layers.color.get("Alpha") or bm.loops.layers.color.new("Alpha")

                mw = obj.matrix_world
                nmat = mw.to_3x3()

                # Optional speedup: compute lighting per-vertex once, then reuse for loops
                v_light = [0.0] * len(bm.verts)
                for i, v in enumerate(bm.verts):
                    world_pos = mw @ v.co
                    world_n = (nmat @ v.normal).normalized()

                    lv = 0.0
                    for lp, e in zip(light_positions, light_energies):
                        to_light = (lp - world_pos)
                        to_light.normalize()
                        b = world_n.dot(to_light)
                        if b > 0.0:
                            lv += b * e

                    lv = lv / (light_count * 1000.0)
                    if lv < 0.1:
                        lv = 0.1
                    elif lv > 1.0:
                        lv = 1.0
                    v_light[i] = lv

                # Write loop colors
                for face in bm.faces:
                    for loop in face.loops:
                        li = v_light[loop.vert.index]
                        loop[col_layer] = (
                            base_color[0] * li,
                            base_color[1] * li,
                            base_color[2] * li,
                            1.0
                        )
                        loop[alpha_layer] = (0.0, 0.0, 0.0, 1.0)

                bm.to_mesh(me)
                bm.free()
                me.update()

                # Restore the active color layer so the viewport preview stays consistent
                color_attrs = getattr(me, "color_attributes", None)
                if color_attrs:
                    target_name = active_color_by_object.get(obj.name)

                    def _set_active_by_name(name: str) -> bool:
                        if not name or not color_attrs:
                            return False

                        for attr in color_attrs:
                            if attr.name == name:
                                # Blender 4/5 safe way:
                                try:
                                    color_attrs.active = attr
                                except Exception:
                                    pass

                                # Some builds have active_render, some don't
                                if hasattr(color_attrs, "active_render"):
                                    try:
                                        color_attrs.active_render = attr
                                    except Exception:
                                        pass

                                # If these exist in your build, set them too (optional)
                                if hasattr(color_attrs, "active_color_index"):
                                    try:
                                        color_attrs.active_color_index = color_attrs.find(attr.name)
                                    except Exception:
                                        pass
                                if hasattr(color_attrs, "active_index"):
                                    try:
                                        color_attrs.active_index = color_attrs.find(attr.name)
                                    except Exception:
                                        pass

                                return True

                        return False

                # If you really need it, do it once per object, but it's expensive:
                # context.view_layer.objects.active = obj
                # bpy.ops.object.assign_materials()

        finally:
            # cleanup lights even if something fails
            for l in temp_lights:
                if l and l.name in bpy.data.objects:
                    bpy.data.objects.remove(l, do_unlink=True)

            # restore previous mode
            if prev_active:
                context.view_layer.objects.active = prev_active
                try:
                    bpy.ops.object.mode_set(mode=prev_mode)
                except Exception:
                    pass

        self.report({'INFO'}, "Vertex colors and alpha baked based on lighting.")
        return {'FINISHED'}
