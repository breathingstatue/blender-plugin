"""
Name:    parameters_out
Purpose: Exporting cars parameters useful for the parameters.txt files

Description:
Prints most valuable car parameters into clipboard.

"""

import bpy
import bmesh
import importlib
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
    params += f"SteerRate\t3.000000\t\t; Rate at which steer angle approaches value from input\n"
    params += f"SteerMod\t0.400000\t\t; Additional steering modulation\n"
    params += f"EngineRate\t4.500000\t\t; Rate at which Engine voltage approaches set value\n"
    params += f"TopSpeed\t32.000000\t\t; Car's theoretical top speed (not including friction...)\n"
    params += f"DownForceMod\t2.000000\t\t; Downforce modifier when car on floor\n"
    params += f"CoM\t\t0.000000 2.000000 -4.000000\t\t; Centre of mass relative to model centre\n"
    params += f"Weapon\t\t0.000000 -32.000000 64.000000\t\t; Weapon generation offset\n\n"

    return params
    
def append_body_info(params):
    # Append static placeholders for BODY details
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
    params += "}\t\t; End Body\n\n"
    
    return params

def append_front_left_wheel(params, body, processed):
    wheel_names = [
        ("wheelfl", "wheelfl.prm", "wheell.prm")
    ]
    wheels = get_objects_by_exact_names(wheel_names, parent_object=body)

    # Check for any of the matching keys
    child = wheels.get("wheelfl") or wheels.get("wheelfl.prm") or wheels.get("wheell.prm")
    if child and child.name not in processed:
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
        params += "}\t\t; End Wheel\n\n"
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
        params += "}\t\t; End Wheel\n\n"
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
        params += "}\t\t; End Wheel\n\n"
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
        params += "}\t\t; End Wheel\n\n"
        processed.add(child.name)
    else:
        print(f"Warning: wheelbr not found in the scene.")
    
    return params

def append_spring_info(params, body, processed):
    spring_names = [
        ("spring0", "spring.prm", "springl.prm"),
        ("spring1", "spring.prm.001", "springr.prm"),
        ("spring2", "spring.prm.002", "springl.prm.001"),
        ("spring3", "spring.prm.003", "springr.prm.001")
    ]
    springs = get_objects_by_exact_names(spring_names, parent_object=body)

    wheel_names = [
        ("wheelfl", "wheelfl.prm", "wheell.prm"),
        ("wheelfr", "wheelfr.prm", "wheelr.prm"),
        ("wheelbl", "wheelbl.prm", "wheelfl.prm.001", "wheell.prm.001"),
        ("wheelbr", "wheelbr.prm", "wheelfr.prm.001", "wheelr.prm.001")
    ]
    wheels = get_objects_by_exact_names(wheel_names, parent_object=body)

    for i, (spring_group, wheel_group) in enumerate(zip(spring_names, wheel_names)):
        spring_key = spring_group[0]
        wheel_key = wheel_group[0]

        spring_obj = springs.get(spring_key)
        wheel_obj = wheels.get(wheel_key)

        if not spring_obj or not wheel_obj:
            print(f"Warning: Spring or wheel not found for index {i} ({spring_key}, {wheel_key}).")
            continue

        # Store original rotation
        original_rotation = spring_obj.rotation_euler.copy()

        # Align spring to face upwards for parameter calculation
        align_spring_to_upwards(spring_obj)

        # Recalculate bounding box after alignment
        bpy.context.view_layer.update()
        bbox_corners = [spring_obj.matrix_world @ Vector(corner) for corner in spring_obj.bound_box]

        # Calculate the highest Z and midpoint X
        z_max = max(corner.z for corner in bbox_corners)
        x_min = min(corner.x for corner in bbox_corners)
        x_max = max(corner.x for corner in bbox_corners)
        x_mid = (x_min + x_max) / 2

        # Convert to Re-Volt coordinates
        spring_position_revolt = to_revolt_coord(Vector((x_mid, spring_obj.location.y, z_max)))
        x, y, z = spring_position_revolt

        # Calculate spring length
        diagonal_distances = [Vector(bbox_corners[j]) - Vector(bbox_corners[i]) for i in range(len(bbox_corners)) for j in range(i+1, len(bbox_corners))]
        spring_length_blender = max(v.length for v in diagonal_distances)
        spring_length_revolt = to_revolt_scale(spring_length_blender)

        params += f"\nSPRING {i} {{\t; Start Spring\n"
        params += f"ModelNum\t5\n"
        params += f"Offset\t\t{x:.6f} {y:.6f} {z:.6f}\n"
        params += f"Length\t\t{spring_length_revolt:.6f}\n"
        params += f"Stiffness\t400.000000\n"
        params += f"Damping\t\t9.000000\n"
        params += f"Restitution\t-0.950000\n"
        params += f"}}\t\t; End Spring\n\n"
        processed.add(spring_obj.name)

        # Restore original rotation
        spring_obj.rotation_euler = original_rotation

    return params

def append_axle_info(params, body, processed):
    axle_names = [
        ("axle0", "axle.prm", "axlel.prm"),
        ("axle1", "axle.prm.001", "axler.prm"),
        ("axle2", "axle.prm.002", "axlel.prm.001"),
        ("axle3", "axle.prm.003", "axler.prm.001")
    ]
    axles = get_objects_by_exact_names(axle_names, parent_object=body)
    correction_factor = 0.82979745  # Corrective scaling to apply to measured

    for i, axle_group in enumerate(axle_names):
        axle_key = axle_group[0]
        axle_obj = axles.get(axle_key)

        if not axle_obj:
            print(f"Warning: Axle not found for index {i} ({axle_key}).")
            continue
        
        original_rotation = axle_obj.rotation_euler.copy()

        # First align to the principal axis
        align_axle_to_principal_axis(axle_obj)
        bpy.context.view_layer.update()  # Ensure the update is applied

        # Assuming axle is already aligned such that the y-axis is the length axis
        verts = [axle_obj.matrix_world @ vert.co for vert in axle_obj.data.vertices]
    
        # Direct calculation of y-axis distance
        y_min = min(vert.y for vert in verts)
        y_max = max(vert.y for vert in verts)
        axle_length_blender = (y_max - y_min) * correction_factor
        axle_length_revolt = to_revolt_scale(axle_length_blender)

        # Using the axle's current position for x and z
        axle_position_revolt = to_revolt_coord(Vector((axle_obj.location.x, axle_obj.location.y, axle_obj.location.z)))
        x, y, z = axle_position_revolt
        
        params += f"\nAXLE {i} {{\t; Start Axle\n"
        params += f"ModelNum\t9\n"
        params += f"Offset\t\t{x:.6f} {y:.6f} {z:.6f}\n"
        params += f"Length\t\t{axle_length_revolt:.6f}\n"
        params += "}\t\t; End Axle\n\n"
        processed.add(axle_obj.name)
        
        axle_obj.rotation_euler = original_rotation
    
    return params

def append_aerial_info(params, body_obj, processed):
    # Find the aerial object, checking both name and parent
    aerial = next((obj for obj in bpy.data.objects if "aerial" in obj.name.lower() and obj.name not in processed and obj.parent == body_obj), None)

    if aerial:
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
        print("No aerial found in the scene or not parented to body.")
        if params is None:  # Ensure params is not None
            params = ""

    return params

def align_spring_to_wheel(spring, wheel):
    direction = (wheel.location.xy - spring.location.xy).normalized()
    up_vector = Vector((0, 0, 1))  # Assuming Z is up
    angle = direction.angle_signed(Vector((1, 0)))  # Angle with respect to the global X-axis

    # Set the spring's rotation to align with the calculated angle
    spring.rotation_euler = (0, 0, angle)

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

def get_wheels_by_prefixes(prefix_tuples, parent_object=None):
    """
    Retrieves objects matching any of the given prefixes provided in tuples.
    If a parent object is specified, it also checks if they are children of that parent object.
    Assumes objects follow a naming convention that includes a base name followed by an optional numerical suffix.
    """
    found_objects = {}

    for obj in bpy.data.objects:
        for prefixes in prefix_tuples:
            for prefix in prefixes:
                if obj.name.startswith(prefix):
                    if parent_object is None or obj.parent == parent_object:
                        found_objects[obj.name] = obj
                        print(f"Found {obj.name} with prefix {prefix}, parent: {obj.parent.name if obj.parent else 'None'}")
                        break  # Once matched, no need to check further prefixes for this object
    return found_objects

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
    params = f"Name\t{car_name}\n\n"
    body = bpy.data.objects.get("body.prm", None)
    processed = set()

    params = append_model_info(params, car_name)
    params = append_additional_params(params)
    params = append_body_info(params)
    params = append_front_left_wheel(params, body, processed)
    params = append_front_right_wheel(params, body, processed)
    params = append_back_left_wheel(params, body, processed)
    params = append_back_right_wheel(params, body, processed)
    params = append_spring_info(params, body, processed)
    params = append_axle_info(params, body, processed)
    params = append_aerial_info(params, processed)

    bpy.context.window_manager.clipboard = params