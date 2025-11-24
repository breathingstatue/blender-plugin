"""
Name:    parameters_in
Purpose: Import cars directly via parameters.txt.

Description:
Imports all car parts from files described in parameters.txt.

"""

import os
import bpy
import bmesh
import importlib
import math
from math import radians
from mathutils import Vector, Quaternion, Matrix, Euler
from . import common
from . import carinfo
from . import prm_in
from .common import to_blender_axis, to_blender_coord, to_blender_scale, PARAMETERS, to_blender_angle
from .prm_in import import_file

# Check if 'bpy' is already in locals to determine if this is a reload scenario
if "bpy" in locals():
    importlib.reload(common)
    importlib.reload(carinfo)
    importlib.reload(prm_in)

def import_file(filepath, scene):
    """
    Imports a parameters.txt file and loads car body and wheels.
    """
    PARAMETERS[filepath] = carinfo.read_parameters(filepath)

    # Import the car and its parts
    import_car(PARAMETERS[filepath], filepath, scene)

    PARAMETERS.pop(filepath)

def import_car(params, filepath, scene):
    folder = os.sep.join(filepath.split(os.sep)[:-1])
    imported_objects = []

    if 'wheel' in params:
        wheel0loc = to_blender_coord(params["wheel"][0]["offset1"])
        wheel1loc = to_blender_coord(params["wheel"][1]["offset1"])
        wheel2loc = to_blender_coord(params["wheel"][2]["offset1"])
        wheel3loc = to_blender_coord(params["wheel"][3]["offset1"])
    else:
        wheel0loc = wheel1loc = wheel2loc = wheel3loc = (0, 0, 0)
        print("Warning: 'wheel' data missing in parameters.txt. Skipping wheel imports.")

    spring_lengths = []
    if 'spring' in params:
        spring0loc = to_blender_coord(params["spring"][0]["offset"])
        spring1loc = to_blender_coord(params["spring"][1]["offset"])
        spring2loc = to_blender_coord(params["spring"][2]["offset"])
        spring3loc = to_blender_coord(params["spring"][3]["offset"])
        spring_lengths = [
            to_blender_scale(params["spring"][0]["length"]),
            to_blender_scale(params["spring"][1]["length"]),
            to_blender_scale(params["spring"][2]["length"]),
            to_blender_scale(params["spring"][3]["length"])
        ]
    else:
        spring0loc = spring1loc = spring2loc = spring3loc = (0, 0, 0)
        spring_lengths = [0, 0, 0, 0]
        print("Warning: 'spring' data missing in parameters.txt. Skipping all springs.")

    axle_lengths = []
    if 'axle' in params:
        axle0loc = to_blender_coord(params["axle"][0]["offset"])
        axle1loc = to_blender_coord(params["axle"][1]["offset"])
        axle2loc = to_blender_coord(params["axle"][2]["offset"])
        axle3loc = to_blender_coord(params["axle"][3]["offset"])
        axle_lengths = [
            to_blender_scale(params["axle"][0]["length"]),
            to_blender_scale(params["axle"][1]["length"]),
            to_blender_scale(params["axle"][2]["length"]),
            to_blender_scale(params["axle"][3]["length"])
        ]
    else:
        axle0loc = axle1loc = axle2loc = axle3loc = (0, 0, 0)
        axle_lengths = [0, 0, 0, 0]
        print("Warning: 'axle' data missing in parameters.txt. Skipping axle imports.")

    pin_lengths = []
    if 'pin' in params:
        pin0loc = to_blender_coord(params["pin"][0]["offset"]) if params["pin"][0]["offset"] != (0.0, 0.0, 0.0) else spring0loc
        pin1loc = to_blender_coord(params["pin"][1]["offset"]) if params["pin"][1]["offset"] != (0.0, 0.0, 0.0) else spring1loc
        pin2loc = to_blender_coord(params["pin"][2]["offset"]) if params["pin"][2]["offset"] != (0.0, 0.0, 0.0) else spring2loc
        pin3loc = to_blender_coord(params["pin"][3]["offset"]) if params["pin"][3]["offset"] != (0.0, 0.0, 0.0) else spring3loc
        pin_lengths = [
            (params["pin"][0]["length"]),
            (params["pin"][1]["length"]),
            (params["pin"][2]["length"]),
            (params["pin"][3]["length"])
        ]
    else:
        pin0loc = pin1loc = pin2loc = pin3loc = (0, 0, 0)
        pin_lengths = [0, 0, 0, 0]
        print("Warning: 'pin' data missing in parameters.txt. Skipping pin imports.")

    cambers = [
        to_blender_angle(params['wheel'][0].get("camber", 0.0)),
        to_blender_angle(params['wheel'][1].get("camber", 0.0)),
        to_blender_angle(params['wheel'][2].get("camber", 0.0)),
        to_blender_angle(params['wheel'][3].get("camber", 0.0))
    ]

    wheel_locations = [wheel0loc, wheel1loc, wheel2loc, wheel3loc]
    spring_locations = [spring0loc, spring1loc, spring2loc, spring3loc]
    pin_locations = [pin0loc, pin1loc, pin2loc, pin3loc]

    def get_single_file_with_keyword(keyword):
        files = [f for f in os.listdir(folder) if keyword in f.lower() and f.lower().endswith('.prm')]
        return files[0] if len(files) == 1 else None

    def get_path(model_num, keyword):
        model_path = get_single_file_with_keyword(keyword)
        if model_path:
            print(f"Found model path with keyword '{keyword}': {model_path}")
            return os.path.join(folder, model_path)

        if model_num >= 0:
            model_file = params['model'][model_num]
            if model_file is None:
                print(f"Error: 'model_file' is None for model_num {model_num}")
                return None
            print(f"Model file before split: {model_file}")

            model_path = os.path.join(folder, model_file.split(os.sep)[-1])
            if os.path.exists(model_path):
                print(f"Found model path: {model_path}")
                return model_path
            else:
                print(f"Model path does not exist: {model_path}")
        else:
            print(f"Invalid model_num: {model_num}")

        return None

    def import_or_placeholder(path, name, obj_location, mark_as_car_part=False):
        obj = None
        if path:
            obj = prm_in.import_file(path, bpy.context.scene)
            if obj is None:
                print(f"Error: Failed to import file from path '{path}' for {name}.")
        else:
            print(f"Path is None for {name}.")

        if obj is None:
            obj = bpy.data.objects.new(name, None)
            bpy.context.scene.collection.objects.link(obj)

        obj.is_car_part = mark_as_car_part
        obj.location = obj_location
        # Check if the object is already in the scene collection
        if obj.name not in bpy.context.scene.collection.objects:
            bpy.context.scene.collection.objects.link(obj)
        else:
            print(f"Object '{obj.name}' is already in the scene collection.")
        obj.name = name
        return obj

    # Body
    try:
        body_path = get_path(params['body']['modelnum'], 'body')
        if body_path:
            body_obj = import_or_placeholder(
                body_path,
                "body",
                to_blender_coord(params["body"]["offset"]),
                mark_as_car_part=True,
            )
            body_obj.name = "body"
            imported_objects.append(body_obj)
            print(f"Imported body at {params['body']['offset']}")

        else:
            print("Warning: Missing data or path for the car body. Skipping body import.")
    except KeyError:
        print("Warning: 'body' data missing in parameters.txt. Skipping body import.")

    # Wheels
    wheel_names = ['wheelfl', 'wheelfr', 'wheelbl', 'wheelbr']
    for i in range(4):
        try:
            wheel_path = get_path(params['wheel'][i]['modelnum'], 'wheel')
            if wheel_path:
                wheel = import_or_placeholder(
                    wheel_path,
                    wheel_names[i],
                    to_blender_coord(params['wheel'][i]['offset1']),
                    mark_as_car_part=True,
                )
                wheel.parent = body_obj
                is_right_wheel = i in [1, 3]
                apply_camber_to_wheel(wheel, cambers[i], is_right_wheel)
                imported_objects.append(wheel)
                print(f"Imported wheel {wheel_names[i]}")
            else:
                print(f"Warning: Missing data or path for wheel {i}. Skipping wheel import.")
        except KeyError:
            print(f"Warning: Wheel data missing for wheel {i}. Skipping wheel import.")

    # Springs
    if 'spring' in params:
        spring_names = ['spring0', 'spring1', 'spring2', 'spring3']
        springs = []
        for i in range(4):
            try:
                spring_path = get_path(params['spring'][i]['modelnum'], 'spring')
                if spring_path:
                    spring = import_or_placeholder(
                        spring_path,
                        spring_names[i],
                        to_blender_coord(params['spring'][i]['offset']),
                        mark_as_car_part=True,
                    )
                    spring.parent = body_obj
                    springs.append(spring)
                    align_to_axis(spring, 'Z')
                    adjust_object_length(spring, spring_lengths[i], 'Z')
                    if is_aligned(spring):
                        set_spring_orientation(spring, wheel_locations[i])
                    print(f"Imported and aligned {spring.name}")
                else:
                    print(f"Warning: Missing data or path for spring {i}. Skipping spring import.")
            except KeyError:
                print(f"Warning: Spring data missing for spring {i}. Skipping spring import.")
    else:
        print("Warning: 'spring' data missing in parameters.txt. Skipping all springs.")

    # Axles
    if 'axle' in params:
        axle_names = ['axle0', 'axle1', 'axle2', 'axle3']
        axles = []
        axle_locations = [axle0loc, axle1loc, axle2loc, axle3loc]
        for i in range(4):
            try:
                axle_path = get_path(params['axle'][i]['modelnum'], 'axle')
                if axle_path:
                    axle = import_or_placeholder(
                        axle_path,
                        axle_names[i],
                        axle_locations[i],
                        mark_as_car_part=True,
                    )
                    axle.parent = body_obj
                    axles.append(axle)
                    align_to_axis(axle, 'Y')
                    adjust_object_length(axle, axle_lengths[i], 'Y')
                    set_orientation(axle, wheel_locations[i])
                    print(f"Adjusted length and set orientation for {axle.name}")
                else:
                    print(f"Warning: Missing data or path for axle {i}. Skipping axle import.")
            except KeyError:
                print(f"Warning: Axle data missing for axle {i}. Skipping axle import.")
    else:
        print("Warning: 'axle' data missing in parameters.txt. Skipping all axles.")

    # Pins
    if 'pin' in params:
        pin_names = ['pin0', 'pin1', 'pin2', 'pin3']
        pins = []
        for i in range(4):
            try:
                if params['pin'][i]['modelnum'] == -1:
                    print(f"Skipping pin {i} due to ModelNum being -1.")
                    continue  # Skip this pin if ModelNum is -1
                pin_path = get_path(params['pin'][i]['modelnum'], 'pin')
                if pin_path:
                    pin = import_or_placeholder(
                        pin_path,
                        pin_names[i],
                        pin_locations[i],
                        mark_as_car_part=True,
                    )
                    pin.parent = body_obj
                    pins.append(pin)

                    # Use the predefined wheel location
                    wheel_location = Vector(wheel_locations[i])
                    print(f"Wheel location for pin {pin_names[i]}: {wheel_location}")

                    # Align the pin's Z-axis to point towards the wheel location
                    align_to_direction(pin, wheel_location)

                    # Move the pin to the wheel location
                    pin.location = wheel_location

                    # Update the object's transformation matrix to apply the changes
                    pin.matrix_world = pin.matrix_basis

                    # Get the length parameter and interpret the scale factor
                    length_param = params['pin'][i]['length']
                    print(f"Length parameter for pin {pin_names[i]}: {length_param}")

                    if length_param == 0.0:
                        scale_factor = 1.0  # No scaling or movement
                    elif 0 < length_param < 1:
                        scale_factor = 1.0 + length_param  # Increase scale
                    elif length_param < -1.0:
                        scale_factor = abs(length_param)
                    elif length_param > 1.0:
                        scale_factor = length_param

                        # Calculate the original bounding box after positioning and aligning
                        original_min_x, original_max_x, original_max_z = calculate_bounding_box(pin)
                        print(f"Original bounding box for pin {pin_names[i]}: X({original_min_x}, {original_max_x}), Z({original_max_z})")

                        # Scale the pin in the Z direction
                        pin.scale.z = scale_factor  # Directly set the scale factor
                        print(f"Scaled pin {pin_names[i]} by factor {scale_factor}")

                        # Update the object's transformation matrix to apply the scaling
                        pin.matrix_world = pin.matrix_basis

                        # Calculate the scaled bounding box
                        scaled_min_x, scaled_max_x, scaled_max_z = calculate_bounding_box(pin)
                        print(f"Scaled bounding box for pin {pin_names[i]}: X({scaled_min_x}, {scaled_max_x}), Z({scaled_max_z})")
                        # Calculate the adjustments needed to even out the edges
                        if i % 2 == 0:
                            # For pins 0 and 2, move towards -x based on max_x difference
                            adjustment_x = original_max_x - scaled_max_x
                        else:
                            # For pins 1 and 3, move towards +x based on min_x difference
                            adjustment_x = original_min_x - scaled_min_x

                        # Adjust the pin's X position
                        pin.location.x += adjustment_x

                        # Adjust the pin's Z position to maintain the top edge
                        adjustment_z = original_max_z - scaled_max_z
                        pin.location.z += adjustment_z

                        # Store the original Y coordinate
                        original_y = pin.location.y

                        # Duplicate the pin
                        duplicate = duplicate_object(pin)

                        # Set the duplicate's origin to its geometry
                        set_geometry_to_origin(duplicate)

                        # Align the original pin with the duplicate in the Y direction
                        pin.location.y = duplicate.location.y

                        # Remove the duplicate from the scene
                        bpy.data.objects.remove(duplicate, do_unlink=True)

                        # Restore the original Y coordinate
                        pin.location.y = original_y

                        print(f"Adjusted location for pin {pin_names[i]}: {pin.location}")
                    else:
                        scale_factor = 1.0 - length_param  # Reduce scale

                    # Ensure the final scale factor is applied correctly
                    pin.scale.z = scale_factor
                    print(f"Final scale factor for pin {pin_names[i]}: {scale_factor}")
                    print(f"Final location for pin {pin_names[i]}: {pin.location}")

                    print(f"Imported, oriented, and scaled pin {pin_names[i]} towards wheel {wheel_location}")
                else:
                    print(f"Warning: Missing data or path for pin {i}. Skipping pin import.")
            except KeyError:
                print(f"Warning: Pin data missing for pin {i}. Skipping pin import.")
    else:
        print("Warning: 'pin' data missing in parameters.txt. Skipping all pins.")

    # Spinner
    if "spinner" in params:
        try:
            spinner_params = params["spinner"]
            spinner_path = get_path(spinner_params["modelnum"], 'spinner')
            if spinner_path:
                spinner_loc = to_blender_coord(spinner_params["offset"])
                spinner_obj = import_or_placeholder(
                    spinner_path,
                    "spinner",
                    spinner_loc,
                    mark_as_car_part=True,
                )
                spinner_obj.parent = body_obj
                imported_objects.append(spinner_obj)
                print(f"Imported spinner at {spinner_loc}")
            else:
                print("Warning: Missing data or path for spinner. Skipping spinner import.")
        except KeyError:
            print("Warning: Spinner data missing in parameters.txt. Skipping spinner import.")
    else:
        print("Warning: 'spinner' data missing in parameters.txt. Skipping spinner import.")

    # Aerial
    aerial_params = params.get("aerial")
    if aerial_params:
        try:
            aerial_loc = to_blender_coord(aerial_params.get("offset", (0.0, 0.0, 0.0)))
            aerial = bpy.data.objects.new("aerial", None)
            scene.collection.objects.link(aerial)
            aerial.location = aerial_loc
            aerial.empty_display_type = 'PLAIN_AXES'
            aerial.empty_display_size = 0.1
            aerial.parent = body_obj
            imported_objects.append(aerial)
            print(f"Imported aerial at {aerial_loc}")
        except KeyError:
            print("Warning: Aerial data missing in parameters.txt. Skipping aerial import.")
    else:
        print("Warning: No aerial parameters found. Skipping aerial import.")

    # Load texture images
    load_texture_images(folder)

    return imported_objects

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

def is_close(v1, v2, tolerance):
    return (v1 - v2).length <= tolerance

def check_vertex_xy_match(vertices1, vertices2, tolerance=0.05):
    if not vertices1 or not vertices2:
        return False

    matches = [any(is_close(v1.xy, v2.xy, tolerance) for v2 in vertices2) for v1 in vertices1]
    percentage_matched = sum(matches) / len(vertices1) * 100
    return percentage_matched >= 55

def is_aligned(obj, tolerance=0.05):
    bottom_vertices, top_vertices = get_extreme_face_vertices(obj)
    return check_vertex_xy_match(bottom_vertices, top_vertices, tolerance)

def align_to_axis(obj, target_axis='Z'):
    bpy.context.view_layer.update()
    bbox = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    dimensions = {
        'x': max(v.x for v in bbox) - min(v.x for v in bbox),
        'y': max(v.y for v in bbox) - min(v.y for v in bbox),
        'z': max(v.z for v in bbox) - min(v.z for v in bbox)
    }
    principal_axis = max(dimensions, key=dimensions.get)

    if principal_axis.lower() == target_axis.lower():
        print(f"{obj.name} is already aligned to the {target_axis} axis.")
        return

    axis_map = {
        ('x', 'y'): ('z', 90),
        ('y', 'x'): ('z', -90),
        ('x', 'z'): ('y', -90),
        ('z', 'x'): ('y', 90),
        ('y', 'z'): ('x', 90),
        ('z', 'y'): ('x', -90)
    }
    rotation_axis, angle = axis_map.get((principal_axis, target_axis.lower()), (None, 0))
    if rotation_axis:
        obj.rotation_euler.rotate_axis(rotation_axis.upper(), radians(angle))
        bpy.context.view_layer.update()
        print(f"Rotated {obj.name} around {rotation_axis.upper()} by {angle} degrees to align {principal_axis.upper()} with {target_axis.upper()}")

def adjust_object_length(obj, target_length_blender, length_axis='Z'):
    bpy.context.view_layer.update()
    bbox = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]

    if length_axis == 'Y':
        original_length_blender = max(v.y for v in bbox) - min(v.y for v in bbox)
    elif length_axis == 'Z':
        original_length_blender = max(v.z for v in bbox) - min(v.z for v in bbox)
    elif length_axis == 'X':
        original_length_blender = max(v.x for v in bbox) - min(v.x for v in bbox)

    print(f"Original length of {obj.name} along {length_axis}: {original_length_blender} Blender units")

    # For other objects, use the percentage logic
    base_value = 20.0
    percentage = (base_value / target_length_blender)
    new_length = original_length_blender * percentage
    new_length /= 100  # Reduce the dimension by 100 times

    # Calculate the new scale factor
    new_scale_factor = new_length / original_length_blender

    # Apply the new scale factor to the object's scale along the specified axis
    if length_axis == 'Y':
        obj.scale.y *= new_scale_factor
    elif length_axis == 'Z':
        obj.scale.z *= new_scale_factor
    elif length_axis == 'X':
        obj.scale.x *= new_scale_factor

    bpy.context.view_layer.update()
    print(f"Adjusted {obj.name} along {length_axis} to target length {new_length} Blender units.")

    bpy.context.view_layer.update()
    bbox = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    new_length_blender = max(getattr(v, length_axis.lower()) for v in bbox) - min(getattr(v, length_axis.lower()) for v in bbox)
    print(f"After adjustment, {obj.name} length along {length_axis}: {new_length_blender} Blender units")

def check_alignment_and_orient(obj, wheel_loc):
    if is_aligned(obj):
        set_spring_orientation(obj, wheel_loc, True)
    else:
        pass

def set_spring_orientation(spring, wheel_loc, outward=True):
    direction = Vector(wheel_loc) - spring.location
    if outward:
        direction = -direction
    direction.normalize()

    up = Vector((0, 0, 1))
    rot_quat = direction.to_track_quat('Z', 'Y')
    spring.rotation_euler = rot_quat.to_euler()
    print(f"Applied rotation to {spring.name}")

def align_to_direction(pin, target_location):
    # Calculate the direction vector from the pin to the target location
    direction = target_location - pin.location
    direction.normalize()

    # Create a quaternion rotation to align the pin's Z-axis with the direction vector
    up = Vector((0, 1, 0))  # Assuming the pin's local Y-axis is the up direction
    rot_quat = direction.to_track_quat('Z', 'Y')

    # Apply an additional 180-degree rotation around the X-axis to flip the pin
    flip_quat = Quaternion((1, 0, 0), math.radians(180))

    # Combine the rotations
    final_quat = rot_quat @ flip_quat

    # Apply the rotation to the pin
    pin.rotation_mode = 'QUATERNION'
    pin.rotation_quaternion = final_quat

def calculate_bounding_box(obj):
    # Get the object's vertices in world space
    vertices = [obj.matrix_world @ Vector(v.co) for v in obj.data.vertices]

    # Calculate the bounding box
    min_x = min(v.x for v in vertices)
    max_x = max(v.x for v in vertices)
    max_z = max(v.z for v in vertices)

    return min_x, max_x, max_z

def duplicate_object(obj):
    # Create a duplicate of the object
    duplicate = obj.copy()
    duplicate.data = obj.data.copy()
    duplicate.animation_data_clear()
    bpy.context.collection.objects.link(duplicate)
    return duplicate

def set_geometry_to_origin(obj):
    # Store the current active object
    original_active = bpy.context.view_layer.objects.active

    # Set the duplicate as the active object
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')

    # Restore the original active object
    bpy.context.view_layer.objects.active = original_active

def set_orientation(obj, target_pos, flip=False):
    if obj is None:
        print("Attempted to set orientation on a None object.")
        return

    obj_location = Vector(obj.location)
    target_vector = Vector(target_pos)

    direction = (target_vector - obj_location).normalized()
    up_axis = 'Z'
    quat = direction.to_track_quat('Y', up_axis)

    if flip:
        flip_quat = Quaternion((0, 0, 1), radians(180))
        quat = quat @ flip_quat

    obj.rotation_euler = quat.to_euler()

def apply_camber_to_wheel(wheel, camber_angle, is_right_wheel=False):
    # Only apply camber if the angle is non-zero
    if camber_angle != 0.0:
        # Invert the camber angle for right-side wheels to tilt them outward
        if is_right_wheel:
            camber_angle = camber_angle
        else:
            camber_angle = -camber_angle

        # Apply the camber as a rotation around the Y-axis to tilt the wheels
        wheel.rotation_euler.rotate_axis('Y', camber_angle)
        print(f"Applied camber of {math.degrees(camber_angle)} degrees to {wheel.name}")
    else:
        pass

def load_texture_images(folder):
    """
    Load all texture images in the folder to the scene, excluding default textures and specific files.
    """
    excluded_files = {'carbox.bmp', 'carbox.png', 'shadow.bmp', 'shadow.png', 'car.bmp', 'car.png'}
    folder_name = os.path.basename(folder)
    excluded_files.update({f"{folder_name}.bmp", f"{folder_name}.png"})

    image_files = [f for f in os.listdir(folder) if f.lower().endswith(('.bmp', '.png')) and f not in excluded_files]

    for image_file in image_files:
        image_path = os.path.join(folder, image_file)
        image = bpy.data.images.load(image_path)
        texture = bpy.data.textures.new(image_file, type='IMAGE')
        texture.image = image
        print(f"Loaded texture image: {image_file}")