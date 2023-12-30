"""
Name:    tools
Purpose: Provides functions for operators

Description:
Some functions that are called by operators 
(e.g. the light panel, helpers, etc.).

"""

import bpy
import bmesh
import mathutils
from math import pi
import time
from . import common
import importlib

from .props.props_scene import RVSceneProperties
from bpy.props import (
    FloatProperty,
    IntProperty,
    StringProperty,
)

# Reloading the 'common' module if it's already in locals
if "common" in locals():
    importlib.reload(common)

    # from common
BAKE_SHADOW_METHODS = [
    ("ADAPTIVE_QMC", "Default (fast)", "", "ALIASED", 0),
    ("CONSTANT_QMC", "Nicer (slow)", "", "ANTIALIASED", 1)
]
    # from props_scene
shadow_method = bpy.props.EnumProperty(
    name="Method",
    items=BAKE_SHADOW_METHODS,
    description="Default (Adaptive QMC):\nFaster option, recommended "
                "for testing the shadow settings.\n\n"
                "High Quality:\nSlower and less grainy option, "
                "recommended for creating the final shadow"
)

shadow_quality = IntProperty(
    name = "Quality",
    min = 0,
    max = 32,
    default = 15,
    description = "The amount of samples the shadow is rendered with "
                  "(number of samples taken extra)"
)
    
shadow_resolution = IntProperty(
    name = "Resolution",
    min = 32,
    max = 8192,
    default = 128,
    description = "Texture resolution of the shadow.\n"
                  "Default: 128x128 pixels"
)
    
shadow_softness = FloatProperty(
    name = "Softness",
    min = 0.0,
    max = 100.0,
    default = 1,
    description = "Softness of the shadow "
                  "(Light size for ray shadow sampling)"
)
    
shadow_table = StringProperty(
    name = "Shadowtable",
    default = "",
    description = "Shadow coordinates for use in parameters.txt of cars.\n"
                  "Click to select all, then CTRL C to copy"
)

def bake_shadow(self, context):
    # This will create a negative shadow (Re-Volt requires a neg. texture)
    rd = context.scene.render
    rd.use_bake_to_vertex_color = False
    rd.use_textures = False

    shade_obj = context.object
    scene = bpy.context.scene
    props = scene.revolt

    resolution = props.shadow_resolution
    quality = props.shadow_quality
    method = props.shadow_method
    softness = props.shadow_softness

    # Create a hemi light (positive)
    lamp_data_pos = bpy.data.lights.new(name="ShadePositive", type="HEMI")
    lamp_data_pos.energy = 1.0  # Adjust the light intensity if needed
    lamp_positive = bpy.data.objects.new(name="ShadePositive", object_data=lamp_data_pos)

    # Create a sun light (negative)
    lamp_data_neg = bpy.data.lights.new(name="ShadeNegative", type="SUN")
    lamp_data_neg.energy = 1.0  # Adjust the light intensity if needed
    lamp_data_neg.use_negative = True
    lamp_negative = bpy.data.objects.new(name="ShadeNegative", object_data=lamp_data_neg)

    # Link lights to the scene
    scene.collection.objects.link(lamp_positive)
    scene.collection.objects.link(lamp_negative)

    # Create a texture
    shadow_tex = bpy.data.images.new(name="Shadow", width=resolution, height=resolution)

    all_objs = [ob_child for ob_child in context.scene.objects if ob_child.parent == shade_obj] + [shade_obj]

    # Get the bounds taking in account all child objects (wheels, etc.)
    # Using the world matrix here to get positions from child objects
    far_left = min([min([(ob.matrix_world[0][3] + ob.bound_box[i][0] * shade_obj.scale[0]) for i in range(0, 8)]) for ob in all_objs])
    far_right = max([max([(ob.matrix_world[0][3] + ob.bound_box[i][0] * shade_obj.scale[0]) for i in range(0, 8)]) for ob in all_objs])
    far_front = max([max([(ob.matrix_world[1][3] + ob.bound_box[i][1] * shade_obj.scale[1]) for i in range(0, 8)]) for ob in all_objs])
    far_back = min([min([(ob.matrix_world[1][3] + ob.bound_box[i][1] * shade_obj.scale[1]) for i in range(0, 8)]) for ob in all_objs])
    far_top = max([max([(ob.matrix_world[2][3] + ob.bound_box[i][2] * shade_obj.scale[2]) for i in range(0, 8)]) for ob in all_objs])
    far_bottom = min([min([(ob.matrix_world[2][3] + ob.bound_box[i][2] * shade_obj.scale[2]) for i in range(0, 8)]) for ob in all_objs])

    # Get the dimensions to set the scale
    dim_x = abs(far_left - far_right)
    dim_y = abs(far_front - far_back)

    # Location for the shadow plane
    loc = ((far_right + far_left)/2,
           (far_front + far_back)/2,
            far_bottom)

    # Create the shadow plane and map it
    bpy.ops.mesh.primitive_plane_add(location=loc, enter_editmode=True)
    bpy.ops.uv.unwrap()
    bpy.ops.object.mode_set(mode='OBJECT')
    shadow_plane = context.object

    # Set the scale for the shadow plane
    scale = max(dim_x, dim_y)
    shadow_plane.scale.x = scale / 1.5
    shadow_plane.scale.y = scale / 1.5

    # Unwrap the shadow plane
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.uv.unwrap(method='ANGLE_BASED', margin=0.001)
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.bake(type='DIFFUSE')

    # Set the image for the shadow plane UV map
    uv_layer = shadow_plane.data.uv_layers.active
    for polygon in shadow_plane.data.polygons:
        for loop_index in polygon.loop_indices:
            loop = shadow_plane.data.loops[loop_index]
            uv_layer.data[loop.index].image = shadow_tex

    # And finally select it and delete it
    shade_obj.select = False
    shadow_plane.select = False
    lamp_positive.select = True
    lamp_negative.select = True
    bpy.ops.object.delete()

    # select the other object again
    shade_obj.select = True
    scene.objects.active = shade_obj

    # space between the car body center and the edge of the shadow plane
    sphor = (shadow_plane.location[0] - (shadow_plane.dimensions[0]/2))
    spver = ((shadow_plane.dimensions[1]/2) - shadow_plane.location[1])

    # Generates shadowtable
    sleft = (sphor - shade_obj.location[0]) * 100
    sright = (shade_obj.location[0] - sphor) * 100
    sfront = (spver - shade_obj.location[1]) * 100
    sback = (shade_obj.location[1] - spver) * 100
    sheight = (far_bottom - shade_obj.location[2]) * 100
    shtable = ";)SHADOWTABLE {:.4f} {:.4f} {:.4f} {:.4f} {:.4f}".format(
        sleft, sright, sfront, sback, sheight
    )
    props.shadow_table = shtable
    
class ButtonBakeShadow(bpy.types.Operator):
    bl_idname = "button.bake_shadow"
    bl_label = "Bake Shadow"
    bl_description = "Creates a shadow plane beneath the selected object"

    def execute(self, context):
        bake_shadow(context)
        return {"FINISHED"}


def rename_all_objects(self, context):
    props = context.scene.revolt

    for obj in context.selected_objects:
        obj.name = props.rename_all_name

    return len(context.selected_objects)


def select_by_name(self, context):
    props = context.scene.revolt
    sce = context.scene

    objs = [obj for obj in sce.objects if props.rename_all_name in obj.name]

    for obj in objs:
        obj.select = True

    return len(objs)

def select_by_data(self, context):
    sce = context.scene
    compare = context.object

    objs = [obj for obj in sce.objects if obj.data == compare.data]

    for obj in objs:
            obj.select = True

    return len(objs)


def set_property_to_selected(self, context, prop, value):
    for obj in context.selected_objects:
        setattr(obj.revolt, prop, value)
    return len(context.selected_objects)


def batch_bake(self, context):
    props = context.scene.revolt

    rd = context.scene.render

    # Saves old render settings
    old_bake_vcol = rd.use_bake_to_vertex_color
    old_bake_type = rd.bake_type

    # Sets render settings
    rd.use_bake_to_vertex_color = True
    rd.bake_type = "FULL"

    # Bakes all selected objects
    for obj in context.selected_objects:

        # Skips unsupported objects
        if not hasattr(obj.data, "vertex_colors"):
            continue

        dprint("Baking at {}...".format(obj.name))
        context.scene.objects.active = obj

        # Gets currently selected layers
        old_active_render_layer = None
        old_active = None
        for vclayer in obj.data.vertex_colors:
            if vclayer.active_render:
                old_active_render_layer = vclayer.name
            if vclayer.active:
                old_active = vclayer.name

        dprint("Currently active layer:", old_active)
        dprint("Currently active layer (render):", old_active_render_layer)
        
        # Creates a temporary layer for baking a full render to
        if not "temp" in obj.data.vertex_colors:
            obj.data.vertex_colors.new(name="temp")
        tmp_layer = obj.data.vertex_colors.get("temp")
        tmp_layer.active = True
        tmp_layer.active_render = True
        dprint("TMP layer:", tmp_layer.name)
        dprint("TMP is active render:", tmp_layer.active_render)
        
        # Bakes the image onto that layer
        dprint("Baking...")
        bpy.ops.object.bake_image()
        dprint("done.")

        dprint("Calculating mean color...")
        
        bm = bmesh.new()
        bm.from_mesh(obj.data)

        vcol_layer = bm.loops.layers.color.get("temp")
        
        avg_col = [0.0, 0.0, 0.0]
        
        count = 0

        for face in bm.faces:
            for loop in face.loops:
                for c in range(3):
                    avg_col[c] += loop[vcol_layer][c]
                count += 1

        #TODO: Figure out if brightness is right
        inf_col = [c / count for c in avg_col]
        bm.free()

        for c in range(3):
            if props.batch_bake_model_rgb:
                obj.revolt.fin_col[c] = inf_col[c]
            if props.batch_bake_model_env:
                obj.revolt.fin_envcol[c] = inf_col[c]
        obj.revolt.fin_model_rgb = True

        # Removes the temporary render layer
        obj.data.vertex_colors.remove(tmp_layer)

        dprint("Restoring selection...")
        # Restores active layers
        if old_active_render_layer is not None:
            obj.data.vertex_colors[old_active_render_layer].active_render = True
        if old_active is not None:
            obj.data.vertex_colors[old_active].active = True
        dprint("done.")


    # Restores baking settings
    rd.use_bake_to_vertex_color = old_bake_vcol
    rd.bake_type = old_bake_type
    return len(context.selected_objects)

def generate_chull(context):
    props = context.scene.revolt
    filename = "{}_hull".format(context.object.name)

    scene = context.scene
    obj = context.object

    bm = bmesh.new()
    bm.from_mesh(obj.data)

    # Adds a convex hull to the bmesh
    chull_out = bmesh.ops.convex_hull(bm, input=bm.verts)

    # Gets rid of interior geometry
    for face in bm.faces:
        if face not in chull_out["geom"]:
            bm.faces.remove(face)

    for edge in bm.edges:
        if edge not in chull_out["geom"]:
            bm.edges.remove(edge)

    for vert in bm.verts:
        if vert not in chull_out["geom"]:
            bm.verts.remove(vert)

    me = bpy.data.meshes.new(filename)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(filename, me)
    #TODO: Check for existing material or return existing one in create_material
    me.materials.append(create_material("RVHull", COL_HULL, 0.3))
    ob.show_transparent = True
    ob.show_wire = True
    ob.revolt.is_hull_convex = True
    ob.select = True
    ob.matrix_world = obj.matrix_world.copy()
    scene.objects.link(ob)
    scene.objects.active = ob