"""
Name:    parameters_in
Purpose: Importing cars using the parameters.txt file

Description:
Imports entire cars using the carinfo module.

"""

import os
from re import S
import bpy
import bmesh
import importlib
from math import radians
from mathutils import Vector, Quaternion, Matrix, Euler
from . import common
from . import carinfo
from . import prm_in
from .common import to_blender_axis, to_blender_coord, to_blender_scale, PARAMETERS
from .prm_in import import_file

# Check if 'bpy' is already in locals to determine if this is a reload scenario
if "bpy" in locals():
    importlib.reload(common)
    importlib.reload(carinfo)
    importlib.reload(prm_in)

def import_file(filepath, context, scene):
    """
    Imports a parameters.txt file and loads car body and wheels.
    """

    PARAMETERS[filepath] = carinfo.read_parameters(filepath)

    # Imports the car with all supported files
    import_car(context, scene, PARAMETERS[filepath], filepath)
    
    # Removes parameters from dict so they can be reloaded next time
    PARAMETERS.pop(filepath)


def import_car(context, scene, params, filepath):
    body = params["model"][params["body"]["modelnum"]]
    body_loc = to_blender_coord(params["body"]["offset"])
    wheel0loc = to_blender_coord(params["wheel"][0]["offset1"])
    wheel1loc = to_blender_coord(params["wheel"][1]["offset1"])
    wheel2loc = to_blender_coord(params["wheel"][2]["offset1"])
    wheel3loc = to_blender_coord(params["wheel"][3]["offset1"])
    spring0loc = to_blender_coord(params["spring"][0]["offset"])
    spring1loc = to_blender_coord(params["spring"][1]["offset"])
    spring2loc = to_blender_coord(params["spring"][2]["offset"])
    spring3loc = to_blender_coord(params["spring"][3]["offset"])
    spring0length = to_blender_scale(params["spring"][0]["length"])
    spring1length = to_blender_scale(params["spring"][1]["length"])
    spring2length = to_blender_scale(params["spring"][2]["length"])
    spring3length = to_blender_scale(params["spring"][3]["length"])
    axle0length = to_blender_scale(params["axle"][0]["length"])
    axle1length = to_blender_scale(params["axle"][1]["length"])
    axle2length = to_blender_scale(params["axle"][2]["length"])
    axle3length = to_blender_scale(params["axle"][3]["length"])
    axle0loc = to_blender_coord(params["axle"][0]["offset"])
    axle1loc = to_blender_coord(params["axle"][1]["offset"])
    axle2loc = to_blender_coord(params["axle"][2]["offset"])
    axle3loc = to_blender_coord(params["axle"][3]["offset"])
    aerial_loc = to_blender_coord(params["aerial"]["offset"])

    folder = os.sep.join(filepath.split(os.sep)[:-1])
    
    # Helper function to safely fetch model paths
    def get_path(model_num):
        if model_num >= 0:
            model_file = params['model'][model_num]
            model_path = os.path.join(folder, model_file.split(os.sep)[-1])
            if os.path.exists(model_path):
                return model_path
        return None

    # Helper function to import or create a placeholder object
    def import_or_placeholder(path, name, obj_location):
        """Local helper to import an object or create a placeholder."""
        if path:
            obj = prm_in.import_file(path, bpy.context, bpy.context.scene)
        else:
            obj = create_placeholder(name)
    
        # Set location after import to ensure it overrides any imported transformation
        obj.location = obj_location
        bpy.context.collection.objects.link(obj)
        return obj

    # Body
    body_path = get_path(params['body']['modelnum'])
    body_obj = import_or_placeholder(body_path, "body", to_blender_coord(params["body"]["offset"]))
    
    # Wheels
    wheel_locations = [wheel0loc, wheel1loc, wheel2loc, wheel3loc]
    for i in range(4):
        wheel_path = get_path(params['wheel'][i]['modelnum'])
        wheel = import_or_placeholder(wheel_path, f"wheel {i}", to_blender_coord(params['wheel'][i]['offset1']))
        wheel.parent = body_obj
        
    # Springs
    springs = []
    spring_lengths = [spring0length, spring1length, spring2length, spring3length]
    for i in range(4):
        spring_path = get_path(params['spring'][i]['modelnum'])
        if spring_path:
            spring = import_or_placeholder(spring_path, f"spring{i}", to_blender_coord(params['spring'][i]['offset']))
            if spring:
                spring.parent = body_obj
                spring.location = to_blender_coord(params['spring'][i]['offset'])
                springs.append(spring)
                # Set properties and adjust lengths
                set_spring_properties(spring, spring_lengths[i])
                adjust_spring_length(spring)
                if is_aligned(spring):
                    set_spring_orientation(spring, wheel_locations[i])
            else:
                print(f"Failed to import spring {i} at path: {spring_path}")

    # Import axles and set properties
    axles = []
    axle_lengths = [axle0length, axle1length, axle2length, axle3length]
    for i in range(4):
        axle_path = get_path(params['axle'][i]['modelnum'])
        if axle_path:
            axle = import_or_placeholder(axle_path, f"axle{i}", to_blender_coord(params['axle'][i]['offset']))
            if axle:
                axle.parent = body_obj
                axle.location = to_blender_coord(params['axle'][i]['offset'])
                axles.append(axle)
                # set_axle_properties(axle, axle_lengths[i])
                print(f"Imported and set properties for axle {i}: Length target = {axle_lengths[i]}")
                # adjust_axle_length(axle)
                set_orientation(axle, wheel_locations[i])
                print(f"Adjusted length and set orientation for axle {i}")
            else:
                print(f"Failed to import axle {i} at path: {axle_path}")
        else:
            print(f"No path found for axle {i}")
    
    # Aerial
    aerial = bpy.data.objects.new("aerial", None)
    scene.collection.objects.link(aerial)
    aerial.location = aerial_loc
    aerial.empty_display_type = 'PLAIN_AXES'
    aerial.empty_display_size = 0.1  # This should be the correct attribute
    aerial.parent = body_obj

def create_placeholder(name, context, scene):
    """Create a placeholder object for missing model files."""
    obj = bpy.data.objects.new(name, None)
    scene.collection.objects.link(obj)
    obj.empty_display_type = 'PLAIN_AXES'
    obj.empty_display_size = 0.1
    return obj

def set_spring_orientation(spring, wheel_loc, outward=True):
    """
    Set the orientation of the spring relative to its corresponding wheel.
    Only adjust if the spring's rotation is neutral.
    """
    direction = Vector(wheel_loc) - spring.location
    if outward:
        direction = -direction  # Invert direction to point outward
    direction.normalize()

    # Assuming Z is up in Blender
    up = Vector((0, 0, 1))
    rot_quat = direction.to_track_quat('Z', 'Y')

    # Apply the calculated rotation
    spring.rotation_euler = rot_quat.to_euler()
    print(f"Applied rotation to {spring.name}")

def set_orientation(obj, target_pos, flip=False):
    """ Orient an object so its local Y-axis points towards target_pos, optionally flipped 180 degrees. """
    if obj is None:
        print("Attempted to set orientation on a None object.")
        return

    # Ensure the target position and object location are both vectors
    obj_location = Vector(obj.location)
    target_vector = Vector(target_pos)

    # Calculate the directional vector from the object to the target position
    direction = target_vector - obj_location
    if direction.length == 0:
        print("Target position is the same as object location; no orientation needed.")
        return  # Avoid division by zero in normalization

    # Normalize the directional vector
    direction.normalize()

    # Determine the correct axis for the forward direction; 'Y' axis should point towards the target
    forward_axis = 'Y'
    up_axis = 'Z'

    # Calculate the quaternion to align the object's Y-axis to the direction vector
    quat = direction.to_track_quat(forward_axis, up_axis)

    # If flipping is needed, apply a 180-degree rotation around the up_axis (Z-axis)
    if flip:
        flip_quat = Quaternion((0, 0, 1), radians(180))
        quat = quat @ flip_quat

    # Convert quaternion to Euler angles and apply to the object's rotation
    obj.rotation_euler = quat.to_euler()
    
def get_extreme_face_vertices(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.transform(obj.matrix_world)

    z_coords = [v.co.z for v in bm.verts]
    min_z = min(z_coords)
    max_z = max(z_coords)

    bottom_faces = [f for f in bm.faces if any(abs(v.co.z - min_z) < 0.0001 for v in f.verts)]
    top_faces = [f for f in bm.faces if any(abs(v.co.z - max_z) < 0.0001 for v in f.verts)]

    bottom_vertices = [v.co for f in bottom_faces for v in f.verts]
    top_vertices = [v.co for f in top_faces for v in f.verts]
    bm.free()
    return bottom_vertices, top_vertices

def check_vertex_xy_match(vertices1, vertices2):
    if not vertices1 or not vertices2:
        return False

    def is_close(v1, v2):
        return v1.x == v2.x and v1.y == v2.y

    matched = all(any(is_close(v1, v2) for v2 in vertices2) for v1 in vertices1)
    return matched

def is_aligned(obj):
    bottom_vertices, top_vertices = get_extreme_face_vertices(obj)
    match = check_vertex_xy_match(bottom_vertices, top_vertices)
    return match

def check_alignment_and_orient(obj, wheel_loc):
    if is_aligned(obj):
        set_spring_orientation(obj, wheel_loc, True)
    else:
        pass
    
def set_spring_properties(spring, spring_target_length):
    """Set the target length as a custom property on the spring object."""
    spring["spring_target_length"] = spring_target_length
    
def set_axle_properties(axle, axle_target_length):
    """Set the target length as a custom property on the spring object."""
    axle["axle_target_length"] = axle_target_length

def adjust_spring_length(spring):
    """Adjust the spring's length to match the target length specified in the parameters."""
    
    # Retrieve target length from custom property
    spring_target_length = spring.get("spring_target_length", None)
    if spring_target_length is None:
        print(f"No target length defined for {spring.name}.")
        return

    # Ensure spring's scale is reset to unity before measuring
    spring.scale = (1, 1, 1)
    bpy.context.view_layer.update()  # Ensure the scale reset is applied

    # Get the bounding box diagonal length
    bbox = spring.bound_box
    bbox_min = spring.matrix_world @ Vector(bbox[0])
    bbox_max = spring.matrix_world @ Vector(bbox[6])
    diagonal_length = (bbox_max - bbox_min).length

    # Compute the difference
    difference = spring_target_length - diagonal_length
    allowed_error = 0.025 * spring_target_length  # 2.5% margin

    # Apply scaling if the difference is significant
    if abs(difference) > allowed_error:  # Adjusted threshold
        scale_factor = spring_target_length / diagonal_length
        # Scale only along the Z axis
        spring.scale.z *= scale_factor
        bpy.context.view_layer.update()  # Refresh the scene to apply the transformation
        
def adjust_axle_length(axle):
    axle_target_length = axle.get("axle_target_length", None)
    if axle_target_length is None:
        print(f"No target length defined for {axle.name}.")
        return
    
    # Assuming axle is already aligned such that the y-axis is the length axis
    verts = [axle.matrix_world @ vert.co for vert in axle.data.vertices]
    
    # Compute the x-mid point
    x_mid = (min(vert.x for vert in verts) + max(vert.x for vert in verts)) / 2

    # Find vertices that are closest to this x-mid point
    relevant_verts = [vert for vert in verts if abs(vert.x - x_mid) < 0.10]  # 0.10 as a tolerance for x-mid

    if relevant_verts:
        y_min = min(vert.y for vert in relevant_verts)
        y_max = max(vert.y for vert in relevant_verts)
        current_length = y_max - y_min
        
        print(f"Current length of axle {axle.name}: {current_length} Blender units")

        # Proceed with any scaling or adjustments if needed
        # (this part would need more details based on your exact requirements)

def align_axle_to_principal_axis(axle_obj):
    # Reset rotation to original or neutral
    axle_obj.rotation_euler = Euler((0, 0, 0), 'XYZ')
    bpy.context.view_layer.update()

    # Calculate the principal axis (longest side of the bounding box)
    bbox = [axle_obj.matrix_world @ Vector(corner) for corner in axle_obj.bound_box]
    lengths = {
        'x': (max(bbox, key=lambda v: v.x).x - min(bbox, key=lambda v: v.x).x),
        'y': (max(bbox, key=lambda v: v.y).y - min(bbox, key=lambda v: v.y).y),
        'z': (max(bbox, key=lambda v: v.z).z - min(bbox, key=lambda v: v.z).z)
    }
    principal_axis = max(lengths, key=lengths.get)
    
    # Align this axis with the global Y-axis
    axis_vectors = {'x': Vector((1, 0, 0)), 'y': Vector((0, 1, 0)), 'z': Vector((0, 0, 1))}
    target_axis = Vector((0, 1, 0))  # Y-axis
    rotation_axis = axis_vectors[principal_axis].cross(target_axis)
    angle = axis_vectors[principal_axis].angle(target_axis)

    if rotation_axis.length != 0:
        rotation_matrix = Matrix.Rotation(angle, 4, rotation_axis)
        axle_obj.matrix_world = axle_obj.matrix_world @ rotation_matrix
    
    bpy.context.view_layer.update()