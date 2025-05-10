"""
Name:    parameters_out_redux
Purpose: Exporting cars parameters useful for the parameters.txt files

Description:
Prints most valuable car parameters into clipboard.

"""

from logging import INFO
import bpy
import bmesh
import importlib
from math import radians
from mathutils import Vector, Matrix, Euler
import numpy as np
from . import common
from .common import to_revolt_coord, to_revolt_scale, to_revolt_camber
from .layers import get_average_vcol2

# Check if 'bpy' is already in locals to determine if this is a reload scenario
if "bpy" in locals():
    importlib.reload(common)

from .common import to_revolt_coord  # Assuming to_revolt_coord exists in common and converts Blender to Re-Volt coordinates

"""
MODEL INFO -----------------------------------------------------------------------
"""

def append_model_info(params, car_name):
    params += f";====================\n"
    params += f" Model Filenames\n"
    params += f";====================\n\n"
    params += f"MODEL\t0\t\"cars\\{car_name}\\body.prm\"\n"
    params += f"MODEL\t1\t\"cars\\{car_name}\\wheelfl.prm\"\n"
    params += f"MODEL\t2\t\"cars\\{car_name}\\wheelfr.prm\"\n"
    params += f"MODEL\t3\t\"cars\\{car_name}\\wheelbl.prm\"\n"
    params += f"MODEL\t4\t\"cars\\{car_name}\\wheelbr.prm\"\n"

    # Check and add spring model
    if any(obj.name.startswith("spring") for obj in bpy.data.objects):
        params += f"MODEL\t5\t\"cars\\{car_name}\\spring.prm\"\n"
    else:
        params += f"MODEL\t5\t\"NONE\"\n"

    # Default to "NONE" for models 6 to 8 unless a pin or spinner is found
    for i in range(6, 8):
        params += f"MODEL\t{i}\t\"NONE\"\n"

    # Check and add axle model
    if any(obj.name.startswith("axle") for obj in bpy.data.objects):
        params += f"MODEL\t9\t\"cars\\{car_name}\\axle.prm\"\n"
    else:
        params += f"MODEL\t9\t\"NONE\"\n"

    # Default to "NONE" for models 10 to 12
    for i in range(10, 12):
        params += f"MODEL\t{i}\t\"NONE\"\n"

    # Check and add pin or spinner model
    pin_or_spinner_obj = next((obj for obj in bpy.data.objects if obj.name.startswith(("pin", "spinner"))), None)
    if pin_or_spinner_obj:
        model_name = "pin.prm" if pin_or_spinner_obj.name.startswith("pin") else "spinner.prm"
        params += f"MODEL\t13\t\"cars\\{car_name}\\{model_name}\"\n"
    else:
        params += f"MODEL\t13\t\"NONE\"\n"

    # Default to "NONE" for models 14 to 16
    for i in range(14, 16):
        params += f"MODEL\t{i}\t\"NONE\"\n"

    # Append models 17 and 18
    params += f"MODEL\t17\t\"cars\\misc\\Aerial.m\"\n"
    params += f"MODEL\t18\t\"cars\\misc\\AerialT.m\"\n"

    # Append TPAGE, COLL
    params += f"TPAGE\t\"cars\\{car_name}\\car.bmp\"\n"
    params += f"COLL\t\"cars\\{car_name}\\hull.hul\"\n"

    # Fetch the EnvRGB color
    env_rgb = get_body_env_rgb()

    params += f"EnvRGB\t{env_rgb}\n\n"

    return params
            
"""
WHEELS -----------------------------------------------------------------------
"""

def append_front_left_wheel(params, body, processed):
    wheel_names = [
        ("wheelfl", "wheelfl.prm", "wheell.prm")
    ]
    wheels = get_objects_by_exact_names(wheel_names, parent_object=body)

    child = wheels.get("wheelfl") or wheels.get("wheelfl.prm") or wheels.get("wheell.prm")
    if child and child.name not in processed and child.parent == body:
        params += f";====================\n"
        params += f"; Car Wheel details\n"
        params += f";====================\n\n"
        location = to_revolt_coord(child.location)
        params += f"\nWHEEL 0 {{\t; Start Wheel\n"
        params += f"ModelNum\t1\n"
        params += f"Offset1\t\t{location[0]:.6f} {location[1]:.6f} {location[2]:.6f}\n"
        params += f"Offset2\t\t-0.000000 0.000000 0.000000\n"
        camber_value = get_camber_for_wheel(child, 0)
        if camber_value is not None:
            params += f"Camber\t{camber_value:.6f}\n"
        params += "}\t\t; End Wheel\n"
        processed.add(child.name)
    else:
        print(f"Warning: wheelfl not found in the scene or not parented to body.")
    
    return params

def append_front_right_wheel(params, body, processed):
    wheel_names = [
        ("wheelfr", "wheelfr.prm", "wheelr.prm")
    ]
    wheels = get_objects_by_exact_names(wheel_names, parent_object=body)

    child = wheels.get("wheelfr") or wheels.get("wheelfr.prm") or wheels.get("wheelr.prm")
    if child and child.name not in processed and child.parent == body:
        location = to_revolt_coord(child.location)
        params += f"\nWHEEL 1 {{\t; Start Wheel\n"
        params += f"ModelNum\t2\n"
        params += f"Offset1\t\t{location[0]:.6f} {location[1]:.6f} {location[2]:.6f}\n"
        params += f"Offset2\t\t0.000000 0.000000 0.000000\n"
        camber_value = get_camber_for_wheel(child, 1)
        if camber_value is not None:
            params += f"Camber\t{camber_value:.6f}\n"
        params += "}\t\t; End Wheel\n"
        processed.add(child.name)
    else:
        print(f"Warning: wheelfr not found in the scene or not parented to body.")
    
    return params

def append_back_left_wheel(params, body, processed):
    wheel_names = [
        ("wheelbl", "wheelbl.prm", "wheelfl.prm.001", "wheell.prm.001")
    ]
    wheels = get_objects_by_exact_names(wheel_names, parent_object=body)

    child = wheels.get("wheelbl") or wheels.get("wheelbl.prm") or wheels.get("wheelfl.prm.001") or wheels.get("wheell.prm.001")
    if child and child.name not in processed and child.parent == body:
        location = to_revolt_coord(child.location)
        params += f"\nWHEEL 2 {{\t; Start Wheel\n"
        params += f"ModelNum\t3\n"
        params += f"Offset1\t\t{location[0]:.6f} {location[1]:.6f} {location[2]:.6f}\n"
        params += f"Offset2\t\t-0.000000 0.000000 0.000000\n"
        camber_value = get_camber_for_wheel(child, 2)
        if camber_value is not None:
            params += f"Camber\t{camber_value:.6f}\n"
        params += "}\t\t; End Wheel\n"
        processed.add(child.name)
    else:
        print(f"Warning: wheelbl not found in the scene or not parented to body.")
    
    return params

def append_back_right_wheel(params, body, processed):
    wheel_names = [
        ("wheelbr", "wheelbr.prm", "wheelfr.prm.001", "wheelr.prm.001")
    ]
    wheels = get_objects_by_exact_names(wheel_names, parent_object=body)

    child = wheels.get("wheelbr") or wheels.get("wheelbr.prm") or wheels.get("wheelfr.prm.001") or wheels.get("wheelr.prm.001")
    if child and child.name not in processed and child.parent == body:
        location = to_revolt_coord(child.location)
        params += f"\nWHEEL 3 {{\t; Start Wheel\n"
        params += f"ModelNum\t4\n"
        params += f"Offset1\t\t{location[0]:.6f} {location[1]:.6f} {location[2]:.6f}\n"
        params += f"Offset2\t\t0.000000 0.000000 0.000000\n"
        camber_value = get_camber_for_wheel(child, 3)
        if camber_value is not None:
            params += f"Camber\t{camber_value:.6f}\n"
        params += "}\t\t; End Wheel\n"
        processed.add(child.name)
    else:
        print(f"Warning: wheelbr not found in the scene or not parented to body.")
    
    return params

"""
SPRINGS -----------------------------------------------------------------------
"""

def compare_and_adjust_spring_lengths(imported_object):
    body = bpy.data.objects.get("body")
    if not body:
        print("Body object not found in the scene.")
        return

    spring_names = [
        ("spring0", "spring.prm", "springsl.prm", "springs.prm"),
        ("spring1", "spring.prm.001", "springsr.prm", "springs.prm.001"),
        ("spring2", "spring.prm.002", "springsr.prm.001", "springs.prm.002"),
        ("spring3", "spring.prm.003", "springsl.prm.001", "springs.prm.003")
    ]
    springs = get_objects_by_exact_names(spring_names, parent_object=body)

    for spring_name in spring_names:
        spring_key = spring_name[0]
        spring_obj = springs.get(spring_key)

        if not spring_obj or spring_obj.parent != body:
            print(f"Warning: Spring {spring_key} not found or not parented to body.")
            continue

        # Store the original rotation
        original_rotation = spring_obj.rotation_euler.copy()

        # Align the existing spring to face upwards
        align_spring_to_upwards(spring_obj)
        bpy.context.view_layer.update()

        # Use the single imported object for comparison
        if imported_object:
            print(f"Using imported object: {imported_object.name}")

            # Calculate the length of the imported spring
            imported_spring_length = calculate_spring_length(imported_object)

            # Calculate the length of the existing spring
            existing_spring_length = calculate_spring_length(spring_obj)

            # Compare lengths and adjust the measured length
            if existing_spring_length == 0:
                measured_length = 20.000000  # Default value if existing length is zero
            else:
                length_ratio = imported_spring_length / existing_spring_length
                measured_length = 20.000000 * length_ratio

            # Store the measured length for parameters export
            spring_obj["measured_length"] = measured_length
            print(f"Spring {spring_key}: Measured length = {measured_length:.6f}")
        else:
            print("Warning: No imported object found for comparison.")

        # Restore the original rotation
        spring_obj.rotation_euler = original_rotation

def append_spring_info(params, body, processed):
    spring_names = [
        ("spring0", "spring.prm", "springsl.prm", "springs.prm"),
        ("spring1", "spring.prm.001", "springsr.prm", "springs.prm.001"),
        ("spring2", "spring.prm.002", "springsr.prm.001", "springs.prm.002"),
        ("spring3", "spring.prm.003", "springsl.prm.001", "springs.prm.003")
    ]
    springs = get_objects_by_exact_names(spring_names, parent_object=body)

    for i, spring_name in enumerate(spring_names):
        spring_key = spring_name[0]
        spring_obj = springs.get(spring_key)

        if not spring_obj or spring_obj.parent != body:
            print(f"Warning: Spring {spring_key} not found or not parented to body.")
            continue

        # Use the stored measured length if available
        spring_length_revolt = spring_obj.get("measured_length", 20.000000)
        print(f"Using measured length for {spring_key}: {spring_length_revolt:.6f}")

        # Converting the location to Re-Volt coordinates
        spring_position_revolt = to_revolt_coord(spring_obj.location)
        x, y, z = spring_position_revolt

        # Build output string
        params += f"\nSPRING {i} {{\t; Start Spring\n"
        params += f"ModelNum\t5\n"
        params += f"Offset\t\t{x:.6f} {y:.6f} {z:.6f}\n"
        params += f"Length\t\t{spring_length_revolt:.6f}\n"
        params += f"}}\t\t; End Spring\n"
        processed.add(spring_obj.name)

    return params

def calculate_spring_length(spring_obj):
    bbox = [spring_obj.matrix_world @ Vector(corner) for corner in spring_obj.bound_box]
    z_min = min(corner.z for corner in bbox)
    z_max = max(corner.z for corner in bbox)
    return z_max - z_min

def align_spring_to_upwards(spring_obj):
    """
    Aligns the spring object so that its primary axis points directly upwards.
    Assumes the primary axis of the spring is its local Z-axis.
    """
    # Determine the direction vector for the spring's primary axis in world space
    # Assuming the primary axis is the Z-axis locally
    local_z = Vector((0, 0, 1))
    world_z = spring_obj.matrix_world.to_3x3() @ local_z

    # Calculate the rotation required to align this vector with the global Z-axis
    align_rotation = world_z.rotation_difference(Vector((0, 0, 1)))

    # Apply this rotation to the object's existing rotation
    spring_obj.rotation_euler = (Matrix.Rotation(align_rotation.angle, 3, align_rotation.axis) @ spring_obj.matrix_world.to_3x3()).to_euler()

    # Update the scene to apply changes
    bpy.context.view_layer.update()

def get_objects_by_exact_names(names, parent_object=None):
    """
    Retrieves objects by their exact names, optionally filtering by parent object.
    """
    objects = {}
    for name_tuple in names:
        for name in name_tuple:
            obj = bpy.data.objects.get(name)
            if obj and (parent_object is None or obj.parent == parent_object):
                objects[name_tuple[0]] = obj
                break
    return objects

def remove_imported_springs(objects):
    """
    Removes the imported spring objects from the scene.
    """
    for obj in objects:
        bpy.data.objects.remove(obj, do_unlink=True)

"""
PINS -----------------------------------------------------------------------
"""

def compare_and_adjust_pin_lengths(imported_object):
    body = bpy.data.objects.get("body")
    if not body:
        print("Body object not found in the scene.")
        return

    pin_names = [
        ("pin0", "pin.prm", "pinfl.prm"),
        ("pin1", "pin.prm.001", "pinfr.prm"),
        ("pin2", "pin.prm.002", "pinfr.prm.001"),
        ("pin3", "pin.prm.003", "pinfl.prm.001")
    ]
    pins = get_objects_by_exact_names(pin_names, parent_object=body)

    wheel_names = [
        ("wheelfl", "wheelfl.prm", "wheell.prm"),
        ("wheelfr", "wheelfr.prm", "wheelr.prm"),
        ("wheelbl", "wheelbl.prm", "wheelfl.prm.001", "wheell.prm.001"),
        ("wheelbr", "wheelbr.prm", "wheelfr.prm.001", "wheelr.prm.001")
    ]
    wheels = get_objects_by_exact_names(wheel_names, parent_object=body)

    wheel_locations = [
        wheels.get("wheelfl") or wheels.get("wheelfl.prm") or wheels.get("wheell.prm"),
        wheels.get("wheelfr") or wheels.get("wheelfr.prm") or wheels.get("wheelr.prm"),
        wheels.get("wheelbl") or wheels.get("wheelbl.prm") or wheels.get("wheelfl.prm.001") or wheels.get("wheell.prm.001"),
        wheels.get("wheelbr") or wheels.get("wheelbr.prm") or wheels.get("wheelfr.prm.001") or wheels.get("wheelr.prm.001")
    ]

    for i, pin_name in enumerate(pin_names):
        pin_key = pin_name[0]
        pin_obj = pins.get(pin_key)

        if not pin_obj or pin_obj.parent != body:
            print(f"Warning: Pin {pin_key} not found or not parented to body.")
            continue

        # Store the original rotation mode
        original_rotation_mode = pin_obj.rotation_mode

        # Store the original rotation based on the mode
        if original_rotation_mode == 'QUATERNION':
            original_rotation = pin_obj.rotation_quaternion.copy()
        elif original_rotation_mode == 'AXIS_ANGLE':
            original_rotation = (pin_obj.rotation_axis_angle[0], pin_obj.rotation_axis_angle[1])
        else:
            original_rotation = pin_obj.rotation_euler.copy()

        # Store the original location
        original_location = pin_obj.location.copy()

        # Align the existing pin to face upwards
        align_pin_to_upwards(pin_obj)
        bpy.context.view_layer.update()

        # Use the single imported object for comparison
        if imported_object:
            print(f"Using imported object: {imported_object.name}")

            # Calculate the length of the imported pin
            imported_pin_length = calculate_pin_length(imported_object)

            # Calculate the length of the existing pin
            existing_pin_length = calculate_pin_length(pin_obj)

            # Calculate the bounding box of the pin
            bbox = [pin_obj.matrix_world @ Vector(corner) for corner in pin_obj.bound_box]
            z_min = min(corner.z for corner in bbox)

            # Determine if the pin exceeds the wheel's coordinates
            wheel_location = wheel_locations[i].location if wheel_locations[i] else None
            if wheel_location:
                if z_min < wheel_location.z:
                    exceeding_part = wheel_location.z - z_min
                    if exceeding_part > 0.10 * existing_pin_length:
                        measured_length = existing_pin_length / imported_pin_length
                    else:
                        length_ratio = existing_pin_length / imported_pin_length
                        measured_length = -length_ratio  # Pin is longer from the top
                else:
                    length_ratio = existing_pin_length / imported_pin_length
                    measured_length = -length_ratio  # Pin is longer from the top
            else:
                measured_length = 1.000000  # Default value if no wheel location

            # Store the measured length for parameters export
            pin_obj["measured_length"] = measured_length
            print(f"Pin {pin_key}: Measured length = {measured_length:.6f}")
        else:
            print("Warning: No imported object found for comparison.")

        # Restore the original rotation mode and rotation
        pin_obj.rotation_mode = original_rotation_mode
        if original_rotation_mode == 'QUATERNION':
            pin_obj.rotation_quaternion = original_rotation
        elif original_rotation_mode == 'AXIS_ANGLE':
            pin_obj.rotation_axis_angle = original_rotation
        else:
            pin_obj.rotation_euler = original_rotation

        # Restore the original location
        pin_obj.location = original_location

def append_pin_info(params, body, processed):
    pin_names = [
        ("pin0", "pin.prm", "pinfl.prm"),
        ("pin1", "pin.prm.001", "pinfr.prm"),
        ("pin2", "pin.prm.002", "pinfr.prm.001"),
        ("pin3", "pin.prm.003", "pinfl.prm.001")
    ]
    pins = get_objects_by_exact_names(pin_names, parent_object=body)

    for i, pin_name in enumerate(pin_names):
        pin_key = pin_name[0]
        pin_obj = pins.get(pin_key)

        if not pin_obj or pin_obj.parent != body:
            print(f"Warning: Pin {pin_key} not found or not parented to body.")
            continue

        # Use the stored measured length if available
        pin_length_revolt = pin_obj.get("measured_length", -1.000000)
        print(f"Using measured length for {pin_key}: {pin_length_revolt:.6f}")

        # Build output string
        params += f"\nPIN {i} {{\t\t; Start Pin\n"
        params += f"ModelNum\t13\n"
        params += f"Offset\t\t0.000000 0.000000 0.000000\n"
        params += f"Length\t\t{pin_length_revolt:.6f}\n"
        params += f"}}\t\t; End Pin\n\n"
        processed.add(pin_obj.name)

    return params

def calculate_pin_length(pin_obj):
    bbox = [pin_obj.matrix_world @ Vector(corner) for corner in pin_obj.bound_box]
    z_min = min(corner.z for corner in bbox)
    z_max = max(corner.z for corner in bbox)
    return z_max - z_min

def align_pin_to_upwards(pin_obj):
    """
    Aligns the pin object so that its primary axis points directly upwards.
    Assumes the primary axis of the pin is its local Z-axis.
    """
    # Determine the direction vector for the pin's primary axis in world space
    local_z = Vector((0, 0, 1))
    world_z = pin_obj.matrix_world.to_3x3() @ local_z

    # Calculate the rotation required to align this vector with the global Z-axis
    align_rotation = world_z.rotation_difference(Vector((0, 0, 1)))

    # Apply this rotation to the object's existing rotation
    current_mode = pin_obj.rotation_mode
    pin_obj.rotation_mode = 'XYZ'  # Temporarily set to Euler XYZ for alignment
    pin_obj.rotation_euler.rotate(align_rotation)
    pin_obj.rotation_mode = current_mode  # Restore the original rotation mode

    # Update the scene to apply changes
    bpy.context.view_layer.update()

def get_objects_by_exact_names(names, parent_object=None):
    """
    Retrieves objects by their exact names, optionally filtering by parent object.
    """
    objects = {}
    for name_tuple in names:
        for name in name_tuple:
            obj = bpy.data.objects.get(name)
            if obj and (parent_object is None or obj.parent == parent_object):
                objects[name_tuple[0]] = obj
                break
    return objects

def remove_imported_pins(objects):
    """
    Removes the imported pin objects from the scene.
    """
    for obj in objects:
        bpy.data.objects.remove(obj, do_unlink=True)

"""
AXLES -----------------------------------------------------------------------
"""

def compare_and_adjust_axle_lengths(imported_object):
    body = bpy.data.objects.get("body")
    if not body:
        print("Body object not found in the scene.")
        return

    axle_names = [
        ("axle0", "axle.prm", "axlefl.prm"),
        ("axle1", "axle.prm.001", "axlefr.prm"),
        ("axle2", "axle.prm.002", "axlefr.prm.001"),
        ("axle3", "axle.prm.003", "axlefl.prm.001")
    ]
    axles = get_objects_by_exact_names(axle_names, parent_object=body)

    for axle_name in axle_names:
        axle_key = axle_name[0]
        axle_obj = axles.get(axle_key)

        if not axle_obj or axle_obj.parent != body:
            print(f"Warning: Axle {axle_key} not found or not parented to body.")
            continue

        # Store the original rotation
        original_rotation = axle_obj.rotation_euler.copy()

        # Align the existing axle to a consistent orientation
        align_axle_to_consistent_orientation(axle_obj, target_forward='Y', target_up='Z')
        bpy.context.view_layer.update()

        # Use the single imported object for comparison
        if imported_object:
            print(f"Using imported object: {imported_object.name}")

            # Calculate the length of the imported axle
            imported_axle_length = calculate_axle_length(imported_object)

            # Calculate the length of the existing axle
            existing_axle_length = calculate_axle_length(axle_obj)

            # Compare lengths and adjust the measured length
            if existing_axle_length == 0:
                measured_length = 20.000000  # Default value if existing length is zero
            else:
                length_ratio = imported_axle_length / existing_axle_length
                measured_length = 20.000000 * length_ratio

            # Store the measured length for parameters export
            axle_obj["measured_length"] = measured_length
            print(f"Axle {axle_key}: Measured length = {measured_length:.6f}")
        else:
            print("Warning: No imported object found for comparison.")

        # Restore the original rotation
        axle_obj.rotation_euler = original_rotation

def append_axle_info(params, body, processed):
    axle_names = [
        ("axle0", "axle.prm", "axlefl.prm"),
        ("axle1", "axle.prm.001", "axlefr.prm"),
        ("axle2", "axle.prm.002", "axlefr.prm.001"),
        ("axle3", "axle.prm.003", "axlefl.prm.001")
    ]
    axles = get_objects_by_exact_names(axle_names, parent_object=body)

    for i, axle_name in enumerate(axle_names):
        axle_key = axle_name[0]
        axle_obj = axles.get(axle_key)

        if not axle_obj or axle_obj.parent != body:
            print(f"Warning: Axle {axle_key} not found or not parented to body.")
            continue

        # Use the stored measured length if available
        axle_length_revolt = axle_obj.get("measured_length", 20.000000)
        print(f"Using measured length for {axle_key}: {axle_length_revolt:.6f}")

        # Build output string
        axle_position = to_revolt_coord(axle_obj.location)
        params += f"\nAXLE {i} {{\t; Start Axle\n"
        params += f"ModelNum\t9\n"
        params += f"Offset\t\t{axle_position[0]:.6f} {axle_position[1]:.6f} {axle_position[2]:.6f}\n"
        params += f"Length\t\t{axle_length_revolt:.6f}\n"
        params += "}\t\t; End Axle\n"
        processed.add(axle_obj.name)

    return params

def calculate_axle_length(axle_obj):
    bbox = [axle_obj.matrix_world @ Vector(corner) for corner in axle_obj.bound_box]
    y_min = min(corner.y for corner in bbox)
    y_max = max(corner.y for corner in bbox)
    return y_max - y_min

def align_axle_to_consistent_orientation(axle_obj, target_forward='Y', target_up='Z'):
    """Align the axle's primary forward axis and a secondary up axis to specified global axes."""
    bpy.context.view_layer.update()  # Refresh to get current state.

    # Calculate the current forward vector in world coordinates
    current_forward_local = Vector((0, 1, 0))  # Assuming local Y is the forward direction
    current_forward_world = axle_obj.matrix_world.to_3x3() @ current_forward_local

    # Calculate the desired world forward vector
    desired_forward_world = Vector((0, 1, 0)) if target_forward == 'Y' else Vector((1, 0, 0)) if target_forward == 'X' else Vector((0, 0, 1))

    # Calculate rotation to align current forward to desired forward
    rotation_to_align_forward = current_forward_world.rotation_difference(desired_forward_world)
    axle_obj.rotation_euler = (Matrix.Rotation(rotation_to_align_forward.angle, 3, rotation_to_align_forward.axis) @ axle_obj.matrix_world.to_3x3()).to_euler()

    # Update to apply the first alignment
    bpy.context.view_layer.update()

    # Align the up vector
    current_up_local = Vector((0, 0, 1))  # Assuming local Z is the up direction
    current_up_world = axle_obj.matrix_world.to_3x3() @ current_up_local
    desired_up_world = Vector((0, 0, 1)) if target_up == 'Z' else Vector((0, 1, 0)) if target_up == 'Y' else Vector((1, 0, 0))

    # Calculate rotation to align current up to desired up
    rotation_to_align_up = current_up_world.rotation_difference(desired_up_world)
    axle_obj.rotation_euler = (Matrix.Rotation(rotation_to_align_up.angle, 3, rotation_to_align_up.axis) @ axle_obj.matrix_world.to_3x3()).to_euler()

    # Final update to apply all transformations
    bpy.context.view_layer.update()
    print(f"{axle_obj.name} aligned to forward {target_forward} and up {target_up}.")

def remove_imported_axles(imported_objects):
    for obj in imported_objects:
        if isinstance(obj, str):
            # If obj is a string, assume it's an object name
            obj = bpy.data.objects.get(obj)

        if obj and obj.name in bpy.data.objects:
            bpy.data.objects.remove(obj, do_unlink=True)
        else:
            print(f"Warning: Object {obj.name if obj else obj} not found in the scene.")

    print("Imported axles removed from the scene.")
    
"""
SPINNER -----------------------------------------------------------------------
"""

def append_spinner_info(params, body, processed):
    spinner = bpy.data.objects.get("spinner")

    # New parenting check
    if spinner and spinner.parent == body and spinner.name not in processed:
        spinner_position = to_revolt_coord(spinner.location)
        x, y, z = spinner_position

        params += f"\nSPINNER {{\t; Start Spinner\n"
        params += f"ModelNum\t13\n"
        params += f"Offset\t\t{x:.6f} {y:.6f} {z:.6f}\n"
        params += f"}}\t\t; End Spinner\n"
        processed.add(spinner.name)
    else:
        print("Spinner not found or not parented to body, or already processed.")

    return params

"""
AERIAL -----------------------------------------------------------------------
"""

def append_aerial_info(params, body, processed):
    # Directly fetch the aerial object by name and check its parent
    aerial = bpy.data.objects.get("aerial")
    
    # New parenting check
    if aerial and aerial.parent == body and aerial.name not in processed:
        params += f";====================\n"
        params += f"; Car Aerial details\n"
        params += f";====================\n"
        location = to_revolt_coord(aerial.location)
        params += f"\nAERIAL {{\t; Start Aerial\n"
        params += f"SecModelNum\t17\n"
        params += f"TopModelNum\t18\n"
        params += f"Offset\t\t{location[0]:.6f} {location[1]:.6f} {location[2]:.6f}\n"
        params += "}\t\t; End Aerial\n"
        processed.add(aerial.name)
    else:
        if aerial is None:
            print("Aerial object not found.")
        elif aerial.parent != body:
            print("Aerial is not parented to body.")
        elif aerial.name in processed:
            print("Aerial has already been processed.")

    return params

"""
TOOLS -----------------------------------------------------------------------
"""

def get_objects_by_exact_names(name_tuples, parent_object=None):
    """
    Retrieves objects matching any of the given exact names provided in tuples.
    If a parent object is specified, it also checks if they are children of that parent object.
    """
    found_objects = {}
    object_set = set()  # This set will hold all exact names to be matched

    # Flatten the list of tuples and populate the set with exact names
    for names in name_tuples:
        object_set.update(names)

    for obj in bpy.data.objects:
        if obj.name in object_set:
            if parent_object is None or obj.parent == parent_object:
                # Assign the object to all possible keys it matches
                for names in name_tuples:
                    if obj.name in names:
                        base_key = names[0]  # Use the first item as the key
                        found_objects[base_key] = obj
                        print(f"Found {obj.name} as {base_key}, parent: {obj.parent.name if obj.parent else 'None'}")

    return found_objects

def get_body_env_rgb():
    body = bpy.data.objects.get("body")
    if not body or body.type != 'MESH':
        print("Body object not found or is not a mesh.")
        return "000 000 000"
    
    original_mode = bpy.context.object.mode if bpy.context.object else None

    # Ensure the body object is selected and switch to Edit mode
    bpy.context.view_layer.objects.active = body

    if original_mode != 'EDIT':
        bpy.ops.object.mode_set(mode='EDIT')

    bm = bmesh.from_edit_mesh(body.data)
    vc_layer = bm.loops.layers.color.get("Col")

    if not vc_layer:
        print("No active vertex color layer found on body.")
        bpy.ops.object.mode_set(mode='OBJECT')
        return "000 000 000"

    avg_color = get_average_vcol2(bm.faces, vc_layer)
    env_rgb = f"{int(avg_color[0] * 255):03d} {int(avg_color[1] * 255):03d} {int(avg_color[2] * 255):03d}"

    # Ensure the mesh is updated
    bmesh.update_edit_mesh(body.data)

    # Explicitly set the mode back to OBJECT mode
    bpy.ops.object.mode_set(mode='OBJECT')

    return env_rgb

def get_camber_for_wheel(wheel_obj, wheel_index):
    # Check if the camber should be exported
    if bpy.context.scene.export_camber:
        # Assuming the camber is applied as a rotation around the Y-axis
        camber_in_radians = wheel_obj.rotation_euler.y

        # Convert the camber to the Re-Volt format
        camber_in_revolt = to_revolt_camber(camber_in_radians)

        # Invert camber for left-side wheels (0 and 2)
        if wheel_index in [0, 2]:
            camber_in_revolt = -camber_in_revolt

        return camber_in_revolt
    else:
        return None  # If camber is not exported, return None
    
def check_and_get_child(name, body, required=True):
    """
    Check if an object exists and is parented to 'body'. 
    If required is True and the check fails, print a warning.
    """
    obj = bpy.data.objects.get(name)
    if not obj:
        if required:
            print(f"Warning: {name} is not found in the scene.")
        return None
    elif obj.parent != body:
        print(f"Warning: {name} is not parented to 'body'. Parent the object to proceed.")
        return None
    return obj

"""
EXPORT FUNCTION -----------------------------------------------------------------------
"""
    
def export_file(car_name="car", filepath=None, scene=None):
    params = f"{{\n\n;============================================================\n"
    params += f";============================================================\n"
    params += f" {car_name}\n"
    params += f";============================================================\n"
    params += f";============================================================\n"
    params += f"Name\t\t\"{car_name}\"\n\n"
    body = bpy.data.objects.get("body", None)
    processed = set()

    params = append_model_info(params, car_name)
    params += f"\n"
    params = append_front_left_wheel(params, body, processed)
    params = append_front_right_wheel(params, body, processed)
    params = append_back_left_wheel(params, body, processed)
    params = append_back_right_wheel(params, body, processed)
    params += f"\n"
    params += f";====================\n"
    params += f"; Car Spring details\n"
    params += f";====================\n"
    params = append_spring_info(params, body, processed)
    params += f"\n"
    params += f";====================\n"
    params += f"; Car Pin details\n"
    params += f";====================\n"
    params = append_pin_info(params, body, processed)
    params += f"\n"
    params += f";====================\n"
    params += f"; Car Axle details\n"
    params += f";====================\n"
    params = append_axle_info(params, body, processed)
    params += f"\n"
    params += f";====================\n"
    params += f"; Car Spinner details\n"
    params += f";====================\n"
    params = append_spinner_info(params, body, processed)
    params += f"\n"
    params = append_aerial_info(params, body, processed)
    
    bpy.context.window_manager.clipboard = params