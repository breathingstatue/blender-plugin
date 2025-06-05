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
from . import common
from .common import create_material, COL_HULL, int_to_texture, texture_to_int, TRIGGER_TYPES, LOW_FLAG_OPTIONS, HIGH_FLAG_OPTIONS
from .fob_subtypes import OBJECT_TYPE_NAMES
import importlib

if "common" in locals():
    importlib.reload(common)


def generate_chull(context):
    scene = context.scene
    obj = context.object
    hull_name = "Convex_Hull"

    # Duplicate the object
    duplicate_obj = obj.copy()
    duplicate_obj.data = obj.data.copy()

    # Temporarily link the duplicate for processing
    temp_collection = bpy.data.collections.new("Temp_Collection")
    bpy.context.scene.collection.children.link(temp_collection)
    temp_collection.objects.link(duplicate_obj)

    bpy.context.view_layer.objects.active = duplicate_obj
    duplicate_obj.select_set(True)

    # Convert the duplicate to a convex hull
    bm = bmesh.new()
    bm.from_mesh(duplicate_obj.data)

    try:
        chull_out = bmesh.ops.convex_hull(bm, input=bm.verts)

        # Validate convex hull geometry
        if not chull_out["geom"]:
            print("No valid convex hull geometry created.")
            bm.free()
            return None

        # Remove non-hull geometry
        for face in bm.faces[:]:
            if face not in chull_out["geom"]:
                bm.faces.remove(face)
        for edge in bm.edges[:]:
            if edge not in chull_out["geom"]:
                bm.edges.remove(edge)
        for vert in bm.verts[:]:
            if vert not in chull_out["geom"]:
                bm.verts.remove(vert)

        # Create a new mesh and object for the convex hull
        me = bpy.data.meshes.new(hull_name)
        bm.to_mesh(me)
        bm.free()

        hull_ob = bpy.data.objects.new(hull_name, me)
        hull_ob.is_hull_convex = True
        hull_ob["is_hull_convex"] = True
        hull_ob.matrix_world = obj.matrix_world.copy()
        hull_ob.show_transparent = True
        hull_ob.show_wire = True
        me.materials.append(create_material("RVHull", COL_HULL, 0.3))

        # Link to the same collections as the original object
        for collection in obj.users_collection:
            collection.objects.link(hull_ob)

        # Remove the temporary duplicate
        bpy.data.objects.remove(duplicate_obj, do_unlink=True)
        bpy.data.collections.remove(temp_collection)

        # Set the convex hull as the active object
        context.view_layer.objects.active = hull_ob
        hull_ob.select_set(True)
        context.view_layer.update()

        return hull_ob
    except Exception as e:
        print(f"Failed to generate convex hull: {e}")
        bm.free()
        bpy.data.objects.remove(duplicate_obj, do_unlink=True)
        bpy.data.collections.remove(temp_collection)
        return None
    
def get_trigger_type_items(self, context):
    """Generates a list of trigger type items for the EnumProperty."""
    return [(str(k), v, "") for k, v in TRIGGER_TYPES.items()]
    
def get_trigger_type(self):
    """Retrieve the trigger_type stored as an integer."""
    return self.get("trigger_type", 0)  # Return as an integer

def set_trigger_type(self, value):
    """Store the trigger_type as an integer."""
    self["trigger_type"] = int(value)  # Store as integer
    self["trigger_type_description"] = TRIGGER_TYPES.get(int(value), "UnknownType")

    # Reset high_flag_enum if not needed
    if int(value) not in HIGH_FLAG_OPTIONS:
        self["high_flag_enum"] = 0

def get_low_flag_items(self, context):
    """Generate a list of low flag items based on the trigger type."""
    obj = context.object
    trigger_type = int(obj.trigger_type_enum)
    low_flag_data = LOW_FLAG_OPTIONS.get(trigger_type)

    if not low_flag_data or "values" not in low_flag_data:
        return []

    return [(str(k), v, "") for k, v in low_flag_data["values"].items()]

def get_high_flag_items(self, context):
    """Generate a list of high flag items based on the trigger type."""
    obj = context.object
    trigger_type = int(obj.trigger_type_enum)  # Retrieve the current trigger type
    high_flag_data = HIGH_FLAG_OPTIONS.get(trigger_type)

    if not high_flag_data:
        return []

    return [(str(i), f"High Flag {i}", "") for i in range(high_flag_data["range"][0], high_flag_data["range"][1] + 1)]

def get_low_flag(self):
    """Retrieve the stored low flag value and return it as an integer."""
    return self.get("flag_low", 0)  # Return as an integer

def set_low_flag(self, value):
    """Store the low flag value as an integer."""
    self["flag_low"] = int(value)  # Store as integer

def get_high_flag(self):
    """Retrieve the stored high flag value as an integer."""
    return self.get("flag_high", 0)  # Return as an integer

def set_high_flag(self, value):
    """Set the high flag value."""
    self["flag_high"] = int(value)
    
def map_strength_to_threshold(strength: int) -> float:
    return round(0.90 - (strength - 1) * 0.05, 2)

def trigger_type_items(self, context):
    return [(str(k), v, "") for k, v in TRIGGER_TYPES.items()]

def fob_type_items(self, context):
    return [(str(k), v, "") for k, v in OBJECT_TYPE_NAMES.items()]

def visibox_type_items(self, context):
    return [
        ('1', "Camera", "Camera visibility box"),
        ('2', "Cubes", "Cubes visibility box")
    ]