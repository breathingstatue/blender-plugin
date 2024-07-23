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
from mathutils import Vector, Quaternion, Matrix
from . import common
from . import carinfo
from . import prm_in
from .common import to_blender_axis, to_blender_coord, to_blender_scale, PARAMETERS

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
	axle0loc = to_blender_coord(params["axle"][0]["offset"])
	axle1loc = to_blender_coord(params["axle"][1]["offset"])
	axle2loc = to_blender_coord(params["axle"][2]["offset"])
	axle3loc = to_blender_coord(params["axle"][3]["offset"])

	folder = os.sep.join(filepath.split(os.sep)[:-1])

	# Checks if the wheel models exist
	wheel0_modelnum = int(params["wheel"][0]["modelnum"])
	if wheel0_modelnum >= 0:
		wheel0 = params["model"][wheel0_modelnum]
		if wheel0.split(os.sep)[-1] in os.listdir(folder):
				wheel0path = os.sep.join([folder, wheel0.split(os.sep)[-1]])
	else:
		wheel0 = None

	wheel1_modelnum = int(params["wheel"][1]["modelnum"])
	if wheel1_modelnum >= 0:
		wheel1 = params["model"][wheel1_modelnum]
		if wheel1.split(os.sep)[-1] in os.listdir(folder):
				wheel1path = os.sep.join([folder, wheel1.split(os.sep)[-1]])
	else:
		wheel1 = None

	wheel2_modelnum = int(params["wheel"][2]["modelnum"])
	if wheel2_modelnum >= 0:
		wheel2 = params["model"][wheel2_modelnum]
		if wheel2.split(os.sep)[-1] in os.listdir(folder):
				wheel2path = os.sep.join([folder, wheel2.split(os.sep)[-1]])
	else:
		wheel2 = None

	wheel3_modelnum = int(params["wheel"][3]["modelnum"])
	if wheel3_modelnum >= 0:
		wheel3 = params["model"][wheel3_modelnum]
		if wheel3.split(os.sep)[-1] in os.listdir(folder):
				wheel3path = os.sep.join([folder, wheel3.split(os.sep)[-1]])
	else:
		wheel3 = None
   
	# Define the model number for springs
	spring_modelnum = 5

	# Checks if the spring model exists
	spring0 = params["model"][spring_modelnum]
	if spring0 and spring0.split(os.sep)[-1] in os.listdir(folder):
		spring0path = os.sep.join([folder, spring0.split(os.sep)[-1]])
	else:
		spring0 = None

	spring1 = params["model"][spring_modelnum]
	if spring1 and spring1.split(os.sep)[-1] in os.listdir(folder):
		spring1path = os.sep.join([folder, spring1.split(os.sep)[-1]])
	else:
		spring1 = None

	spring2 = params["model"][spring_modelnum]
	if spring2 and spring2.split(os.sep)[-1] in os.listdir(folder):
		spring2path = os.sep.join([folder, spring2.split(os.sep)[-1]])
	else:
		spring2 = None

	spring3 = params["model"][spring_modelnum]
	if spring3 and spring3.split(os.sep)[-1] in os.listdir(folder):
		spring3path = os.sep.join([folder, spring3.split(os.sep)[-1]])
	else:
		spring3 = None

  # Checks if the axle model exists
	axle_modelnum = 9
	
	axle0 = params["model"][axle_modelnum]
	if axle0 and axle0.split(os.sep)[-1] in os.listdir(folder):
		axle0path = os.sep.join([folder, axle0.split(os.sep)[-1]])
	else:
		axle0 = None

	axle1 = params["model"][axle_modelnum]
	if axle1 and axle1.split(os.sep)[-1] in os.listdir(folder):
		axle1path = os.sep.join([folder, axle1.split(os.sep)[-1]])
	else:
		axle1 = None

	axle2 = params["model"][axle_modelnum]
	if axle2 and axle2.split(os.sep)[-1] in os.listdir(folder):
		axle2path = os.sep.join([folder, axle2.split(os.sep)[-1]])
	else:
		axle2 = None

	axle3 = params["model"][axle_modelnum]
	if axle3 and axle3.split(os.sep)[-1] in os.listdir(folder):
		axle3path = os.sep.join([folder, axle3.split(os.sep)[-1]])
	else:
		axle3 = None
		
	# Checks if the body is in the same folder
	if body.split(os.sep)[-1] in os.listdir(folder):
		bodypath = os.sep.join([folder, body.split(os.sep)[-1]])

	# Creates the car body and sets the offset
	body_obj = prm_in.import_file(bodypath, context, scene)
	body_obj.location = body_loc

	# Creates the wheel objects or an empty if the wheel file is not present
	if wheel0:
		wheel = prm_in.import_file(wheel0path, context, scene)
	else:
		wheel = bpy.data.objects.new("wheel 0", None)
		scene.objects.link(wheel)
		wheel.empty_display_type = 'SPHERE'
		wheel.display_size = 0.1
	wheel.location = wheel0loc
	wheel.parent = body_obj

	if wheel1:
		wheel = prm_in.import_file(wheel1path, context, scene)
	else:
		wheel = bpy.data.objects.new("wheel 1", None)
		scene.objects.link(wheel)
		wheel.empty_display_type = 'SPHERE'
		wheel.display_size = 0.1
	wheel.location = wheel1loc
	wheel.parent = body_obj

	if wheel2:
		wheel = prm_in.import_file(wheel2path, context, scene)
	else:
		wheel = bpy.data.objects.new("wheel 2", None)
		scene.objects.link(wheel)
		wheel.empty_display_type = 'SPHERE'
		wheel.display_size = 0.1
	wheel.location = wheel2loc
	wheel.parent = body_obj

	if wheel3:
		wheel = prm_in.import_file(wheel3path, context, scene)
	else:
		wheel = bpy.data.objects.new("wheel 3", None)
		scene.objects.link(wheel)
		wheel.empty_display_type = 'SPHERE'
		wheel.display_size = 0.1
	wheel.location = wheel3loc
	wheel.parent = body_obj

	# Use adjusted indices for wheel locations
	spring_names = ["spring0", "spring1", "spring2", "spring3"]
	spring_paths = [spring0path, spring1path, spring2path, spring3path]
	spring_locs = [
		to_blender_coord(params["spring"][0]["offset"]),
		to_blender_coord(params["spring"][1]["offset"]),
		to_blender_coord(params["spring"][2]["offset"]),
		to_blender_coord(params["spring"][3]["offset"])
	]
	wheel_locs = [
		to_blender_coord(params["wheel"][0]["offset1"]),  # Front left
		to_blender_coord(params["wheel"][1]["offset1"]),  # Front right
		to_blender_coord(params["wheel"][2]["offset1"]),  # Back left
		to_blender_coord(params["wheel"][3]["offset1"])   # Back right
	]

	# Create and position springs
	for i in range(4):
		wheel_loc = wheel_locs[i]
		spring_path = spring_paths[i]
		if spring_path and os.path.basename(spring_path) in os.listdir(os.path.dirname(spring_path)):
			spring = prm_in.import_file(spring_path, context, scene)
		else:
			spring = create_placeholder(spring_names[i], context, scene)

		spring.location = Vector(spring_locs[i])  # Set location directly from parameters
		spring.parent = body_obj
		set_spring_orientation(spring, wheel_loc, outward=True)  # Align spring outward from wheel

	# Creates the axle objects or an empty if the axle file is not present
	if axle0:
		axle = prm_in.import_file(axle0path, context, scene)
	else:
		axle = bpy.data.objects.new("axle0", None)
		scene.collection.objects.link(axle)
		axle.empty_display_type = 'SPHERE'
		axle.display_size = 0.1
	axle.location = axle0loc
	axle.parent = body_obj
	# Setting orientation towards wheel 1, flipping corrected
	set_orientation(axle, wheel1loc)

	if axle1:
		axle = prm_in.import_file(axle1path, context, scene)
	else:
		axle = bpy.data.objects.new("axle1", None)
		scene.collection.objects.link(axle)
		axle.empty_display_type = 'SPHERE'
		axle.display_size = 0.1
	axle.location = axle1loc
	axle.parent = body_obj
	# Setting orientation towards wheel 0
	set_orientation(axle, wheel0loc)

	if axle2:
		axle = prm_in.import_file(axle2path, context, scene)
	else:
		axle = bpy.data.objects.new("axle2", None)
		scene.collection.objects.link(axle)
		axle.empty_display_type = 'SPHERE'
		axle.display_size = 0.1
	axle.location = axle2loc
	axle.parent = body_obj
	# Setting orientation towards wheel 3, flipping corrected
	set_orientation(axle, wheel3loc)

	if axle3:
		axle = prm_in.import_file(axle3path, context, scene)
	else:
		axle = bpy.data.objects.new("axle3", None)
		scene.collection.objects.link(axle)
		axle.empty_display_type = 'SPHERE'
		axle.display_size = 0.1
	axle.location = axle3loc
	axle.parent = body_obj
	# Setting orientation towards wheel 2
	set_orientation(axle, wheel2loc)

	# Aerial representation
	aerial_loc = to_blender_coord(params["aerial"]["offset"])
	aerial = bpy.data.objects.new("aerial", None)
	scene.collection.objects.link(aerial)
	aerial.location = aerial_loc
	aerial.empty_display_type = 'PLAIN_AXES'
	aerial.empty_display_size = 0.1  # This should be the correct attribute
	aerial.parent = body_obj
	
def create_placeholder(name, context, scene):
    """ Creates a placeholder object if the model file is missing. """
    obj = bpy.data.objects.new(name, None)
    scene.collection.objects.link(obj)
    obj.empty_display_type = 'SPHERE'
    obj.display_size = 0.1
    return obj

def set_spring_orientation(spring, wheel_loc, outward=True):
    """ Set the orientation of the spring relative to its corresponding wheel.
        If 'outward' is True, the spring points away from the wheel.
    """
    direction = Vector(wheel_loc) - spring.location
    if outward:
        direction = -direction  # Invert direction to point outward
    direction.normalize()

    # Create a quaternion that represents the rotation needed to align the spring
    up = Vector((0, 0, 1))  # Assuming Z is up
    rot_quat = direction.to_track_quat('Z', 'Y')  # Adjust the axes as needed

    # Rotate the spring to face the correct direction
    spring.rotation_euler = rot_quat.to_euler()

def set_orientation(obj, target_pos, flip=False):
	""" Orient an object so its local Y-axis points towards target_pos, optionally flipped 180 degrees. """
	if obj is None:
		print("Attempted to set orientation on a None object.")
		return

	# Calculate the directional vector from the object to the target position
	direction = Vector(target_pos) - Vector(obj.location)
	if direction.length == 0:
		return  # Avoid division by zero in normalization

	# Calculate the quaternion to align Y-axis to the direction
	quat = direction.to_track_quat('Y', 'Z')

	# If flipping is needed, apply a 180-degree rotation around the Z-axis
	if flip:
		flip_quat = Quaternion((0, 0, 1), radians(180))
		quat = quat @ flip_quat

	# Apply the rotation
	obj.rotation_euler = quat.to_euler()