"""
Name:    parameters_out
Purpose: Exporting cars parameters useful for the parameters.txt files

Description:
Prints most valuable car parameters into clipboard.

"""

import bpy
import bmesh
import importlib
from math import radians
from mathutils import Vector, Matrix, Euler
import numpy as np
from . import common
from .common import to_revolt_coord, to_revolt_scale
from .layers import get_average_vcol2

# Check if 'bpy' is already in locals to determine if this is a reload scenario
if "bpy" in locals():
    importlib.reload(common)

from .common import to_revolt_coord  # Assuming to_revolt_coord exists in common and converts Blender to Re-Volt coordinates

def append_model_info(params, car_name):
    params += f";====================\n"
    params += f" Model Filenames\n"
    params += f";====================\n\n"
    params += f"MODEL\t0\t\"cars\\{car_name}\\body.prm\"\n"
    params += f"MODEL\t1\t\"cars\\{car_name}\\wheelfl.prm\"\n"
    params += f"MODEL\t2\t\"cars\\{car_name}\\wheelfr.prm\"\n"
    params += f"MODEL\t3\t\"cars\\{car_name}\\wheelbl.prm\"\n"
    params += f"MODEL\t4\t\"cars\\{car_name}\\wheelbr.prm\"\n"

    spring_found = False
    for obj in bpy.data.objects:
        if obj.name.startswith(("spring")):
            params += f"MODEL\t5\t\"cars\\{car_name}\\spring.prm\"\n"
            spring_found = True
            break

    # Append "NONE" for models 6 to 8
    for i in range(6, 8):
        params += f"MODEL\t{i}\t\"NONE\"\n"
        
    axle_found = False
    for obj in bpy.data.objects:
        if obj.name.startswith(("axle")):
            params += f"MODEL\t9\t\"cars\\{car_name}\\axle.prm\"\n"
            axle_found = True
            break
        
    # Append "NONE" for models 10 to 16
    for i in range(10, 16):
        params += f"MODEL\t{i}\t\"NONE\"\n"

    # Append models 17 and 18
    params += f"MODEL\t17\t\"cars\\misc\\Aerial.m\"\n"
    params += f"MODEL\t18\t\"cars\\misc\\AerialT.m\"\n"

    # Append TPAGE, COLL
    params += f"TPAGE\t\"cars\\{car_name}\\car.bmp\"\n"
    params += f"COLL\t\"cars\\{car_name}\\hull.hul\"\n"
    
    # Fetch the EnvRGB color
    env_rgb = copy_average_vcol_to_clipboard()
    
    params += f"EnvRGB\t{env_rgb}\n\n"
            
    return params
            
def append_additional_params(params):
    params += f";====================\n"
    params += f"; Stuff mainly for frontend display and car selectability\n"
    params += f";====================\n\n"
    params += f"BestTime\tTRUE\n"
    params += f"Selectable\tTRUE\n"
    params += f"Class\t\t0\t\t; Engine type (0 = Elec, 1 = Glow, 2 = Other)\n"
    params += f"Obtain\t\t0\t\t; Obtain method\n"
    params += f"Rating\t\t0\t\t; Skill level (rookie, amateur, ...)\n"
    params += f"TopEnd\t\t3000.000000\t\t; Actual top speed (mph) for frontend bars\n"
    params += f"Acc\t\t5.000000\t\t; Acceleration rating (empirical)\n"
    params += f"Weight\t\t1.000000\t\t; Scaled weight (for frontend bars)\n"
    params += f"Handling\t50.000000\t\t; Handling ability (empirical and totally subjective)\n"
    params += f"Trans\t\t0\t\t; Transmission type (calculate in-game anyway...)\n"
    params += f"MaxRevs\t\t0.500000\t\t; Max Revs (for rev counter)\n\n"
    params += f";====================\n"
    params += f"; Handling related stuff\n"
    params += f";====================\n\n"
    params += f"SteerRate\t3.000000\t\t; Rate at which steer angle approaches value from input\n"
    params += f"SteerMod\t0.400000\t\t; Additional steering modulation\n"
    params += f"EngineRate\t4.500000\t\t; Rate at which Engine voltage approaches set value\n"
    params += f"TopSpeed\t32.000000\t\t; Theoretical top speed of car (not including friction...)\n"
    params += f"DownForceMod\t2.000000\t\t; Downforce modifier when car on floor\n"
    params += f"CoM\t\t0.000000 2.000000 -4.000000\t\t; Centre of mass relative to model centre\n"
    params += f"Weapon\t\t0.000000 -32.000000 64.000000\t\t; Weapon generation offset\n\n"

    return params
    
def append_body_info(params):
    # Append static placeholders for BODY details
    params += f";====================\n"
    params += f"; Car Body details\n"
    params += f";====================\n\n"
    params += f"BODY {{\t\t; Start Body\n"
    params += f"ModelNum\t0\n"
    params += f"Offset\t\t0, 0, 0\n"
    params += f"Mass\t\t1.000000\n"
    params += f"Inertia\t\t800.000000 0.000000 0.000000\n"
    params += f"\t\t0.000000 1000.000000 0.000000\n"
    params += f"\t\t0.000000 0.000000 500.000000\n"
    params += f"Gravity\t\t2200\n"
    params += f"Hardness\t0.000000\n"
    params += f"Resistance\t0.001000\t\t; Linear air resistance\n"
    params += f"AngRes\t\t0.001000\t\t; Angular air resistance\n"
    params += f"ResMod\t\t25.000000\t\t; Ang air resistance scale when in air\n"
    params += f"Grip\t\t0.010000\t\t; Converts downforce to friction value\n"
    params += f"StaticFriction\t0.800000\n"
    params += f"KineticFriction\t0.400000\n"
    params += "}\t\t; End Body\n"
    
    return params

def append_front_left_wheel(params, body, processed):
    wheel_names = [
        ("wheelfl", "wheelfl.prm", "wheell.prm")
    ]
    wheels = get_objects_by_exact_names(wheel_names, parent_object=body)

    # Check for any of the matching keys
    child = wheels.get("wheelfl") or wheels.get("wheelfl.prm") or wheels.get("wheell.prm")
    if child and child.name not in processed:
        params += f";====================\n"
        params += F"; Car Wheel details\n"
        params += f";====================\n\n"
        location = to_revolt_coord(child.location)
        params += f"\nWHEEL 0 {{\t; Start Wheel\n"
        params += f"ModelNum\t1\n"
        params += f"Offset1\t\t{location[0]:.6f} {location[1]:.6f} {location[2]:.6f}\n"
        params += f"Offset2\t\t-0.000000 0.000000 0.000000\n"
        params += f"IsPresent\tTRUE\nIsPowered\tTRUE\nIsTurnable\tTRUE\n"
        params += f"SteerRatio\t-0.500000\nEngineRatio\t12000.000000\n"
        params += f"Radius\t\t12.000000\n"
        params += f"Mass\t\t0.150000\n"
        params += f"Gravity\t\t2200.000000\n"
        params += f"MaxPos\t\t5.000000\n"
        params += f"SkidWidth\t10.000000\n"
        params += f"ToeIn\t\t0.000000\n"
        params += f"AxleFriction\t0.020000\n"
        params += f"Grip\t\t0.014000\n"
        params += f"StaticFriction\t1.500000\nKineticFriction\t1.500000\n"
        params += "}\t\t; End Wheel\n"
        processed.add(child.name)
    else:
        print(f"Warning: wheelfl  not found in the scene.")
    
    return params

def append_front_right_wheel(params, body, processed):
    wheel_names = [
        ("wheelfr", "wheelfr.prm", "wheelr.prm")
    ]
    wheels = get_objects_by_exact_names(wheel_names, parent_object=body)

    # Check for any of the matching keys
    child = wheels.get("wheelfr") or wheels.get("wheelfr.prm") or wheels.get("wheelr.prm")
    if child and child.name not in processed:
        location = to_revolt_coord(child.location)
        params += f"\nWHEEL 1 {{\t; Start Wheel\n"
        params += f"ModelNum\t2\n"
        params += f"Offset1\t\t{location[0]:.6f} {location[1]:.6f} {location[2]:.6f}\n"
        params += f"Offset2\t\t0.000000 0.000000 0.000000\n"
        params += f"IsPresent\tTRUE\nIsPowered\tTRUE\nIsTurnable\tTRUE\n"
        params += f"SteerRatio\t-0.500000\nEngineRatio\t12000.000000\n"
        params += f"Radius\t\t12.000000\n"
        params += f"Mass\t\t0.150000\n"
        params += f"Gravity\t\t2200.000000\n"
        params += f"MaxPos\t\t5.000000\n"
        params += f"SkidWidth\t10.000000\n"
        params += f"ToeIn\t\t0.000000\n"
        params += f"AxleFriction\t0.020000\n"
        params += f"Grip\t\t0.014000\n"
        params += f"StaticFriction\t1.500000\nKineticFriction\t1.500000\n"
        params += "}\t\t; End Wheel\n"
        processed.add(child.name)
    else:
        print(f"Warning: wheelfr not found in the scene.")
    
    return params

def append_back_left_wheel(params, body, processed):
    wheel_names = [
        ("wheelbl", "wheelbl.prm", "wheelfl.prm.001", "wheell.prm.001")
    ]
    wheels = get_objects_by_exact_names(wheel_names, parent_object=body)

    # Check for any of the matching keys
    child = wheels.get("wheelbl") or wheels.get("wheelbl.prm") or wheels.get("wheell.prm.001")
    if child and child.name not in processed:
        location = to_revolt_coord(child.location)
        params += f"\nWHEEL 2 {{\t; Start Wheel\n"
        params += f"ModelNum\t3\n"
        params += f"Offset1\t\t{location[0]:.6f} {location[1]:.6f} {location[2]:.6f}\n"
        params += f"Offset2\t\t-0.000000 0.000000 0.000000\n"
        params += f"IsPresent\tTRUE\nIsPowered\tTRUE\nIsTurnable\tFALSE\n"
        params += f"SteerRatio\t0.100000\nEngineRatio\t12000.000000\n"
        params += f"Radius\t\t13.000000\n"
        params += f"Mass\t\t0.150000\n"
        params += f"Gravity\t\t2200.000000\n"
        params += f"MaxPos\t\t5.000000\n"
        params += f"SkidWidth\t10.000000\n"
        params += f"ToeIn\t\t0.000000\n"
        params += f"AxleFriction\t0.050000\n"
        params += f"Grip\t\t0.014000\n"
        params += f"StaticFriction\t1.500000\nKineticFriction\t1.500000\n"
        params += "}\t\t; End Wheel\n"
        processed.add(child.name)
    else:
        print(f"Warning: wheelbl not found in the scene.")
    
    return params

def append_back_right_wheel(params, body, processed):
    wheel_names = [
        ("wheelbr", "wheelbr.prm", "wheelfr.prm.001", "wheelr.prm.001")
    ]
    wheels = get_objects_by_exact_names(wheel_names, parent_object=body)

    # Check for any of the matching keys
    child = wheels.get("wheelbr") or wheels.get("wheelbr.prm") or wheels.get("wheelr.prm.001")
    if child and child.name not in processed:
        location = to_revolt_coord(child.location)
        params += f"\nWHEEL 3 {{\t; Start Wheel\n"
        params += f"ModelNum\t4\n"
        params += f"Offset1\t\t{location[0]:.6f} {location[1]:.6f} {location[2]:.6f}\n"
        params += f"Offset2\t\t0.000000 0.000000 0.000000\n"
        params += f"IsPresent\tTRUE\nIsPowered\tTRUE\nIsTurnable\tFALSE\n"
        params += f"SteerRatio\t0.100000\nEngineRatio\t12000.000000\n"
        params += f"Radius\t\t13.000000\n"
        params += f"Mass\t\t0.150000\n"
        params += f"Gravity\t\t2200.000000\n"
        params += f"MaxPos\t\t5.000000\n"
        params += f"SkidWidth\t10.000000\n"
        params += f"ToeIn\t\t0.000000\n"
        params += f"AxleFriction\t0.050000\n"
        params += f"Grip\t\t0.014000\n"
        params += f"StaticFriction\t1.500000\nKineticFriction\t1.500000\n"
        params += "}\t\t; End Wheel\n"
        processed.add(child.name)
    else:
        print(f"Warning: wheelbr not found in the scene.")
    
    return params

def append_spring_info(params, body, processed):
    spring_names = [
        ("spring0", "spring.prm", "springsl.prm"),
        ("spring1", "spring.prm.001", "springsr.prm"),
        ("spring2", "spring.prm.002", "springsr.prm.001"),
        ("spring3", "spring.prm.003", "springsl.prm.001")
    ]
    springs = get_objects_by_exact_names(spring_names, parent_object=body)

    for i, spring_name in enumerate(spring_names):
        spring_key = spring_name[0]
        spring_obj = springs.get(spring_key)

        if not spring_obj:
            print(f"Warning: Spring not found for index {i} ({spring_key}).")
            continue

        # Store original rotation
        original_rotation = spring_obj.rotation_euler.copy()

        # Align spring to face upwards for parameter calculation
        align_spring_to_upwards(spring_obj)

        # Recalculate bounding box after alignment
        bpy.context.view_layer.update()
        
        # Calculate the lenght directly from the bounding box
        bbox = [spring_obj.matrix_world @ Vector(corner) for corner in spring_obj.bound_box]
        z_min = min(corner.z for corner in bbox)
        z_max = max(corner.z for corner in bbox)
        spring_length = z_max - z_min  # Spring length along the Z-axis
        spring_length_revolt = to_revolt_scale(spring_length)

        # Converting the location to Re-Volt coordinates
        spring_position_revolt = to_revolt_coord(spring_obj.location)
        x, y, z = spring_position_revolt

        params += f"\nSPRING {i} {{\t; Start Spring\n"
        params += f"ModelNum\t5\n"
        params += f"Offset\t\t{x:.6f} {y:.6f} {z:.6f}\n"
        params += f"Length\t\t{spring_length_revolt:.6f}\n"
        params += f"Stiffness\t400.000000\n"
        params += f"Damping\t\t9.000000\n"
        params += f"Restitution\t-0.950000\n"
        params += f"}}\t\t; End Spring\n"
        processed.add(spring_obj.name)

        # Restore original rotation
        spring_obj.rotation_euler = original_rotation

    return params

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

        if not axle_obj:
            print(f"Warning: Axle not found for index {i} ({axle_key}).")
            continue
        
        original_rotation = axle_obj.rotation_euler.copy()

        # Align the axle to consistent orientation (modify the axis as needed for your model)
        align_axle_to_consistent_orientation(axle_obj, target_forward='Y', target_up='Z')
        bpy.context.view_layer.update()  # Ensure the alignment is applied

        # Calculate the axle's length along the Y-axis (primary length axis)
        bbox = [axle_obj.matrix_world @ Vector(corner) for corner in axle_obj.bound_box]
        y_min = min(corner.y for corner in bbox)
        y_max = max(corner.y for corner in bbox)
        axle_length = y_max - y_min
        axle_length_revolt = to_revolt_scale(axle_length)

        # Build output string
        axle_position = to_revolt_coord(axle_obj.location)
        params += f"\nAXLE {i} {{\t; Start Axle\n"
        params += f"ModelNum\t9\n"
        params += f"Offset\t\t{axle_position[0]:.6f} {axle_position[1]:.6f} {axle_position[2]:.6f}\n"
        params += f"Length\t\t{axle_length_revolt:.6f}\n"
        params += "}\t\t; End Axle\n"
        processed.add(axle_obj.name)
        
        # Restore original rotation if needed
        axle_obj.rotation_euler = original_rotation
    
    return params

def append_aerial_info(params, body, processed):
    # Directly fetch the aerial object by name and check its parent
    aerial = bpy.data.objects.get("aerial")
    
    if aerial and aerial.parent == body and aerial.name not in processed:
        params += f";====================\n"
        params += f"; Car Aerial details\n"
        params += f";====================\n"
        location = to_revolt_coord(aerial.location)
        params += f"\nAERIAL {{\t; Start Aerial\n"
        params += f"SecModelNum\t17\n"
        params += f"TopModelNum\t18\n"
        params += f"Offset\t\t{location[0]:.6f} {location[1]:.6f} {location[2]:.6f}\n"
        params += f"Direction\t0.000000 -1.000000 0.000000\n"
        params += f"Length\t\t35.000000\n"
        params += f"Stiffness\t2000.000000\n"
        params += f"Damping\t\t5.500000\n"
        params += "}\t\t; End Aerial\n"
        processed.add(aerial.name)
    else:
        if aerial is None:
            print("Aerial object not found.")
        elif aerial.parent != body:
            print("Aerial is not parented correctly.")
        elif aerial.name in processed:
            print("Aerial has already been processed.")

    return params

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

def copy_average_vcol_to_clipboard():
    obj = bpy.context.active_object
    if obj and obj.type == 'MESH':
        bm = bmesh.new()
        bm.from_mesh(obj.data)

        vc_layer = bm.loops.layers.color.get("Col")
        if not vc_layer:
            print("No active vertex color layer found.")
            bm.free()
            return "000 000 000"

        avg_color = get_average_vcol2(bm.faces, vc_layer)
        env_rgb = f"{int(avg_color[0] * 255):03d} {int(avg_color[1] * 255):03d} {int(avg_color[2] * 255):03d}"
        
        bm.free()
        return env_rgb
    else:
        print("No active mesh object found.")
        return "000 000 000"
    
def export_file(car_name="car", filepath=None, scene=None):
    params = f"\t{{\n\n;============================================================\n"
    params += f";============================================================\n"
    params += f" {car_name}\n"
    params += f";============================================================\n"
    params += f";============================================================\n"
    params += f"Name\t\t\"{car_name}\"\n\n"
    body = bpy.data.objects.get("body", None)
    processed = set()

    params = append_model_info(params, car_name)
    params = append_additional_params(params)
    params = append_body_info(params)
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
    params += f";====================\n\n"
    params += f";====================\n"
    params += f"; Car Axle details\n"
    params += f";====================\n"
    params = append_axle_info(params, body, processed)
    params += f"\n"
    params += f";====================\n"
    params += f"; Car Spinner details\n"
    params += f";====================\n\n"
    params = append_aerial_info(params, body, processed)
    params += f"\n"
    params += f";====================\n"
    params += f"; Car AI details\n"
    params += f";====================\n\n"
    params += f"AI {{\t\t; Start AI\n"
    params += f"UnderThresh\t8.049010\n"
    params += f"UnderRange\t550.400561\n"
    params += f"UnderFront\t300.000000\n"
    params += f"UnderRear\t132.6500000\n"
    params += f"UnderMax\t0.999711\n"
    params += f"OverThresh\t200.600000\n"
    params += f"OverRange\t666.000000\n"
    params += f"OverMax\t\t0.400000\n"
    params += f"OverAccThresh\t31000.000000\n"
    params += f"OverAccRange\t601.000000\n"
    params += f"PickupBias\t16383\n"
    params += f"BlockBias\t16383\n"
    params += f"OvertakeBias\t19660\n"
    params += f"Suspension\t19660\n"
    params += f"Aggression\t16383\n"
    params += f"}}\t\t; End AI\n\n}}"

    bpy.context.window_manager.clipboard = params