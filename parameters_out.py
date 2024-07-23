"""
Name:    parameters_out
Purpose: Exporting cars parameters useful for the parameters.txt files

Description:
Prints most valuable car parameters into clipboard.

"""

import bpy
import importlib
from mathutils import Vector, Matrix
import numpy as np
from . import common
from .common import to_revolt_coord, to_revolt_scale

# Check if 'bpy' is already in locals to determine if this is a reload scenario
if "bpy" in locals():
    importlib.reload(common)

from .common import to_revolt_coord  # Assuming to_revolt_coord exists in common and converts Blender to Re-Volt coordinates

def append_model_info(params):
    params += f"MODEL\t0\t\"cars\\car\\body.prm\"\n"
    params += f"MODEL\t1\t\"cars\\car\\wheelfl.prm\"\n"
    params += f"MODEL\t2\t\"cars\\car\\wheelfr.prm\"\n"
    params += f"MODEL\t3\t\"cars\\car\\wheelbl.prm\"\n"
    params += f"MODEL\t4\t\"cars\\car\\wheelbr.prm\"\n"

    # Append "NONE" for models 5 to 16
    for i in range(5, 17):
        params += f"MODEL\t{i}\t\"NONE\"\n"

    # Append models 17 and 18
    params += f"MODEL\t17\t\"cars\\misc\\Aerial.m\"\n"
    params += f"MODEL\t18\t\"cars\\misc\\AerialT.m\"\n"

    # Append TPAGE, COLL, and EnvRGB
    params += f"TPAGE\t\"cars\\car\\car.bmp\"\n"
    params += f"COLL\t\"cars\\car\\hull.hul\"\n"
    params += f"EnvRGB\t000 000 000\n\n"
            
    return params
            
def append_additional_params(params):
    params += f"BestTime\tTRUE\n"
    params += f"Selectable\tTRUE\n"
    params += f"Class\t\t0\t; Engine type (0 = Elec, 1 = Glow, 2 = Other)\n"
    params += f"Obtain\t\t0\t; Obtain method\n"
    params += f"Rating\t\t0\t; Skill level (rookie, amateur, ...)\n"
    params += f"TopEnd\t\t1000.000000\t; Actual top speed (mph) for frontend bars\n"
    params += f"Acc\t\t1.000000\t; Acceleration rating (empirical)\n"
    params += f"Weight\t\t1.000000\t; Scaled weight (for frontend bars)\n"
    params += f"Handling\t50.000000\t; Handling ability (empirical and totally subjective)\n"
    params += f"Trans\t\t0\t; Transmission type (calculate in-game anyway...)\n"
    params += f"MaxRevs\t\t0.500000\t; Max Revs (for rev counter)\n\n"
    params += f"SteerRate\t3.000000\t; Rate at which steer angle approaches value from input\n"
    params += f"SteerMod\t0.400000\t; Additional steering modulation\n"
    params += f"EngineRate\t4.500000\t; Rate at which Engine voltage approaches set value\n"
    params += f"TopSpeed\t10.000000\t; Car's theoretical top speed (not including friction...)\n"
    params += f"DownForceMod\t2.000000\t; Downforce modifier when car on floor\n"
    params += f"CoM\t\t0.000000 0.000000 0.000000\t; Centre of mass relative to model centre\n"
    params += f"Weapon\t\t0.000000 -32.000000 64.000000\t; Weapon generation offset\n\n"

    return params
    
def append_body_info(params):
    # Append static placeholders for BODY details
    params += f"BODY {{\t\t; Start Body\n"
    params += f"ModelNum\t0\n"
    params += f"Offset\t\t0, 0, 0\n"
    params += f"Mass\t\t1.000000\n"
    params += f"Inertia\t\t1000.000000 0.000000 0.000000\n"
    params += f"\t\t0.000000 2000.000000 0.000000\n"
    params += f"\t\t0.000000 0.000000 500.000000\n"
    params += f"Gravity\t\t2000\n"
    params += f"Hardness\t0.000000\n"
    params += f"Resistance\t0.001000\n"
    params += f"AngRes\t\t0.001000\n"
    params += f"ResMod\t\t25.000000\n"
    params += f"Grip\t\t0.010000\n"
    params += f"StaticFriction\t0.800000\n"
    params += f"KineticFriction\t0.400000\n"
    params += "}\t\t; End Body\n\n"
    
    return params

def append_wheel_info(params, body, processed):
    # Mapping wheel suffixes to their model numbers
    wheel_mapping = {
        "fl": 1,  # Front Left
        "fr": 2,  # Front Right
        "bl": 3,  # Back Left
        "br": 4,  # Back Right
    }

    for suffix, model_num in wheel_mapping.items():
        wheel_name = f"wheel{suffix}"
        wheel_found = False
        for child in body.children:
            if wheel_name in child.name.lower() and child.name not in processed:
                location = to_revolt_coord(child.location)
                params += f"\nWHEEL {model_num - 1} {{\t; Start Wheel\n"
                params += f"ModelNum\t{model_num}\n"
                params += f"Offset1\t\t{location[0]:.6f} {location[1]:.6f} {location[2]:.6f}\n"
                params += f"Offset2\t\t-2.000000 0.000000 0.000000\n"
                params += f"IsPresent\tTRUE\nIsPowered\tTRUE\nIsTurnable\tTRUE\n"
                params += f"SteerRatio\t-0.500000\nEngineRatio\t10000.000000\n"
                params += f"Radius\t\t10.000000\n"
                params += f"Mass\t\t0.150000\n"
                params += f"Gravity\t\t2000.000000\n"
                params += f"MaxPos\t\t3.000000\n"
                params += f"SkidWidth\t10.000000\n"
                params += f"ToeIn\t\t0.000000\n"
                params += f"AxleFriction\t0.020000\n"
                params += f"Grip\t\t0.015000\n"
                params += f"StaticFriction\t1.800000\nKineticFriction\t1.650000\n"
                params += "}\t\t; End Wheel\n\n"
                processed.add(child.name)
                wheel_found = True
                break

        if not wheel_found:
            print(f"Warning: {wheel_name} not found in the scene.")
            
    return params

def append_spring_info(params, body, processed):
    # Define prefixes and fetch objects
    spring_prefixes = [("spring", "spring.prm", "spring.prm.001", "spring.prm.002", "spring.prm.003")]
    springs = get_objects_by_prefixes(spring_prefixes, parent_object=body)
    wheel_prefixes = [("wheelfl", "wheelfl.prm"), ("wheelfr", "wheelfr.prm"), ("wheelbl", "wheelbl.prm"), ("wheelbr", "wheelbr.prm")]
    wheels = get_objects_by_prefixes(wheel_prefixes, parent_object=body)

    # Processing each spring and its corresponding wheel
    for i in range(4):
        spring_key = f"spring{i}"  # Key as defined by get_objects_by_prefixes
        wheel_key = f"wheel{['fl', 'fr', 'bl', 'br'][i]}0"  # Wheel keys based on prefix indexing
        
        spring_obj = springs.get(spring_key)
        wheel_obj = wheels.get(wheel_key)
        if not spring_obj or not wheel_obj:
            print(f"Warning: Spring or wheel not found for index {i}.")
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
        params += f"Stiffness\t500.000000\n"
        params += f"Damping\t\t9.000000\n"
        params += f"Restitution\t-0.950000\n"
        params += f"}}\t\t; End Spring\n\n"
        processed.add(spring_obj.name)

        # Restore original rotation
        spring_obj.rotation_euler = original_rotation

    return params

def append_axle_info(params, body, processed):
    # Define axle prefixes and fetch objects
    axle_prefixes = [("axle", "axle.prm", "axle.prm.001", "axle.prm.002", "axle.prm.003")]
    axles = get_objects_by_prefixes(axle_prefixes, parent_object=body)

    # Processing each axle
    for i in range(4):
        axle_key = f"axle{i}"  # Assuming axle naming follows a consistent pattern
        axle_obj = axles.get(axle_key)
        if not axle_obj:
            print(f"Warning: Axle '{axle_key}' not found.")
            continue

def append_axle_info(params, body, processed):
    # Define axle prefixes and fetch objects
    axle_prefixes = [("axle", "axle.prm", "axle.prm.001", "axle.prm.002", "axle.prm.003")]
    axles = get_objects_by_prefixes(axle_prefixes, parent_object=body)

    # Processing each axle
    for i in range(4):
        axle_key = f"axle{i}"
        axle_obj = axles.get(axle_key)
        if not axle_obj:
            print(f"Warning: Axle '{axle_key}' not found.")
            continue

        # Update scene to ensure the bounding box is accurate
        bpy.context.view_layer.update()
        bbox_corners = [axle_obj.matrix_world @ Vector(corner) for corner in axle_obj.bound_box]

        # Calculate the axle length from the bounding box diagonals
        diagonal_distances = [Vector(bbox_corners[j]) - Vector(bbox_corners[i]) for i in range(len(bbox_corners)) for j in range(i + 1, len(bbox_corners))]
        axle_length_blender = max(v.length for v in diagonal_distances)
        axle_length_revolt = to_revolt_scale(axle_length_blender)

        # Calculate the median of the z coordinates of the bounding box
        z_median = np.median([corner.z for corner in bbox_corners])
        
        # Identify the highest face oriented mostly along the z-axis
        tolerance = 0.001
        vertical_edges = []
        for j in range(len(bbox_corners)):
            for k in range(j + 1, len(bbox_corners)):
                if abs(bbox_corners[j].z - bbox_corners[k].z) < tolerance:
                    vertical_edges.append((bbox_corners[j], bbox_corners[k]))

        if not vertical_edges:
            print(f"No vertical edges found for axle '{axle_key}'.")
            continue

        # Find the highest edge
        highest_edge = max(vertical_edges, key=lambda edge: max(edge[0].z, edge[1].z))
        highest_edge_mid_z = (highest_edge[0].z + highest_edge[1].z) / 2

        # Collect corners that are on the highest face
        upper_face_corners = [corner for corner in bbox_corners if abs(corner.z - highest_edge_mid_z) < tolerance]

        if not upper_face_corners:
            print(f"No upper face corners found for axle '{axle_key}'.")
            continue

        x_mid = sum(corner.x for corner in upper_face_corners) / len(upper_face_corners)
        y_mid = sum(corner.y for corner in upper_face_corners) / len(upper_face_corners)

        # Convert to Re-Volt coordinates
        axle_position_revolt = to_revolt_coord(Vector((x_mid, y_mid, z_median)))
        _, y, z = axle_position_revolt  # Ignore x_mid and use 0.0 instead

        x = 0.000000  # Explicitly set x to 0.000000

        params += f"\nAXLE {i} {{\t; Start Axle\n"
        params += f"ModelNum\t9\n"
        params += f"Offset\t\t{x:.6f} {y:.6f} {z:.6f}\n"
        params += f"Length\t\t{axle_length_revolt:.6f}\n"
        params += "}\t\t; End Axle\n\n"
        processed.add(axle_obj.name)

    return params

def append_aerial_info(params, body, processed):
    # Append aerial info, fetching dynamic offset
    for child in body.children:
        if "aerial" in child.name.lower() and child.name not in processed:
            location = to_revolt_coord(child.location)
            params += f"\nAERIAL {{\t; Start Aerial\n"
            params += f"SecModelNum\t17\n"
            params += f"TopModelNum\t18\n"
            params += f"Offset\t\t{location[0]:.6f} {location[1]:.6f} {location[2]:.6f}\n"
            params += f"Direction\t0.000000 -1.000000 0.000000\n"
            params += f"Length\t\t20.000000\n"
            params += f"Stiffness\t2000.000000\n"
            params += f"Damping\t\t5.500000\n"
            params += "}\t\t; End Aerial\n"
            processed.add(child.name)
            break
        
    return params

def export_file(filepath=None, scene=None):
    params = "Name\tcar\n\n"
    body = bpy.data.objects.get("body.prm", None)
    processed = set()

    params = append_model_info(params)
    params = append_additional_params(params)
    params = append_body_info(params)
    params = append_wheel_info(params, body, processed)
    params = append_spring_info(params, body, processed)
    params = append_axle_info(params, body, processed)
    params = append_aerial_info(params, body, processed)

    bpy.context.window_manager.clipboard = params

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

def get_objects_by_prefixes(prefix_tuples, parent_object=None):
    
    """
    Retrieves objects matching any of the given prefixes provided in tuples,
    and checks if they are children of a specified parent object.
    Assumes objects follow a naming convention that includes a base name followed by an optional numerical suffix.
    """
    found_objects = {}
    object_counter = {}  # To keep track of how many objects with the same base name have been found

    for obj in bpy.data.objects:
        if parent_object and obj.parent != parent_object:
            continue  # Skip objects that are not children of the specified parent
        for prefixes in prefix_tuples:
            for prefix in prefixes:
                if obj.name.startswith(prefix):
                    base_name = prefix.split('.')[0]  # Get the base name without any suffix
                    if base_name not in object_counter:
                        object_counter[base_name] = 0
                    else:
                        object_counter[base_name] += 1

                    key = f"{base_name}{object_counter[base_name]}"  # Create a unique key by appending a counter
                    found_objects[key] = obj
                    print(f"Found {obj.name} as {key}, parent: {obj.parent.name if obj.parent else 'None'}")
                    break  # Once matched, no need to check further prefixes for this object
    return found_objects