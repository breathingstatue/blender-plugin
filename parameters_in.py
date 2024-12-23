import os
from re import S
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
    car_name = extract_car_name(filepath)
    
    # Import the car and its parts
    import_car(PARAMETERS[filepath], filepath, scene, car_name)
    
    # After import, ensure material is named car.bmp
    ensure_car_bmp_material(filepath, car_name)

    PARAMETERS.pop(filepath)

def import_car(params, filepath, scene, car_name):
    folder = os.sep.join(filepath.split(os.sep)[:-1])
    imported_objects = []

    # Pass car_name and params to import_all_textures
    import_all_textures(folder, car_name, params)

    if 'body' in params and "model" in params:
        body = params["model"][params["body"]["modelnum"]]
        body_loc = to_blender_coord(params["body"]["offset"])
    else:
        body = None
        body_loc = (0, 0, 0)
        print("Warning: 'body' data missing in parameters.txt. Skipping body import.")
    if 'wheel' in params:
        wheel0loc = to_blender_coord(params["wheel"][0]["offset1"])
        wheel1loc = to_blender_coord(params["wheel"][1]["offset1"])
        wheel2loc = to_blender_coord(params["wheel"][2]["offset1"])
        wheel3loc = to_blender_coord(params["wheel"][3]["offset1"])
    else:
        wheel0loc = wheel1loc = wheel2loc = wheel3loc = (0, 0, 0)
        print("Warning: 'wheel' data missing in parameters.txt. Skipping wheel imports.")
    if 'spring' in params:
        spring0loc = to_blender_coord(params["spring"][0]["offset"])
        spring1loc = to_blender_coord(params["spring"][1]["offset"])
        spring2loc = to_blender_coord(params["spring"][2]["offset"])
        spring3loc = to_blender_coord(params["spring"][3]["offset"])
        spring0length = to_blender_scale(params["spring"][0]["length"])
        spring1length = to_blender_scale(params["spring"][1]["length"])
        spring2length = to_blender_scale(params["spring"][2]["length"])
        spring3length = to_blender_scale(params["spring"][3]["length"])
    else:
        spring0loc = spring1loc = spring2loc = spring3loc = (0, 0, 0)
        spring0length = spring1length = spring2length = spring3length = 0
        print("Warning: 'spring' data missing in parameters.txt. Skipping all springs.")
    if 'axle' in params:
        axle0loc = to_blender_coord(params["axle"][0]["offset"])
        axle1loc = to_blender_coord(params["axle"][1]["offset"])
        axle2loc = to_blender_coord(params["axle"][2]["offset"])
        axle3loc = to_blender_coord(params["axle"][3]["offset"])
        axle0length = to_blender_scale(params["axle"][0]["length"])
        axle1length = to_blender_scale(params["axle"][1]["length"])
        axle2length = to_blender_scale(params["axle"][2]["length"])
        axle3length = to_blender_scale(params["axle"][3]["length"])
    else:
        axle0loc = axle1loc = axle2loc = axle3loc = (0, 0, 0)
        axle0length = axle1length = axle2length = axle3length = 0
        print("Warning: 'axle' data missing in parameters.txt. Skipping axle imports.")
    if 'pin' in params:
        pin0loc = to_blender_coord(params["pin"][0]["offset"]) if params["pin"][0]["offset"] != (0.0, 0.0, 0.0) else spring0loc
        pin1loc = to_blender_coord(params["pin"][1]["offset"]) if params["pin"][1]["offset"] != (0.0, 0.0, 0.0) else spring1loc
        pin2loc = to_blender_coord(params["pin"][2]["offset"]) if params["pin"][2]["offset"] != (0.0, 0.0, 0.0) else spring2loc
        pin3loc = to_blender_coord(params["pin"][3]["offset"]) if params["pin"][3]["offset"] != (0.0, 0.0, 0.0) else spring3loc
        pin0length = to_blender_scale(params["pin"][0]["length"])
        pin1length = to_blender_scale(params["pin"][1]["length"])
        pin2length = to_blender_scale(params["pin"][2]["length"])
        pin3length = to_blender_scale(params["pin"][3]["length"])
    else:
        pin0loc = pin1loc = pin2loc = pin3loc = (0, 0, 0)
        pin0length = pin1length = pin2length = pin3length = 0
        print("Warning: 'pin' data missing in parameters.txt. Skipping pin imports.")
    if 'aerial' in params:
        aerial_loc = to_blender_coord(params["aerial"]["offset"])
    else:
        aerial_loc = (0, 0, 0)
        print("Warning: 'aerial' data missing in parameters.txt. Skipping aerial import.")
    if "camber" in params['wheel'][0]:
        camber_0 = to_blender_angle(params['wheel'][0]["camber"])
    else:
        camber_0 = 0.0  # Explicitly set camber to 0.0 if not present

    if "camber" in params['wheel'][1]:
        camber_1 = to_blender_angle(params['wheel'][1]["camber"])
    else:
        camber_1 = 0.0  # Explicitly set camber to 0.0 if not present

    if "camber" in params['wheel'][2]:
        camber_2 = to_blender_angle(params['wheel'][2]["camber"])
    else:
        camber_2 = 0.0  # Explicitly set camber to 0.0 if not present

    if "camber" in params['wheel'][3]:
        camber_3 = to_blender_angle(params['wheel'][3]["camber"])
    else:
        camber_3 = 0.0  # Explicitly set camber to 0.0 if not present

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

    def import_or_placeholder(path, name, obj_location):
        if path:
            obj = prm_in.import_file(path, bpy.context.scene)
            if obj is None:
                print(f"Error: Failed to import file from path '{path}' for {name}.")
                pass
        else:
            print(f"Path is None for {name}.")
            pass
    
        obj.location = obj_location
        bpy.context.collection.objects.link(obj)
        obj.name = name
        return obj

    wheel_locations = [wheel0loc, wheel1loc, wheel2loc, wheel3loc]
    spring_lengths = [spring0length, spring1length, spring2length, spring3length]
    axle_lengths = [axle0length, axle1length, axle2length, axle3length]
    if 'pin' in params:
        # Set pin locations and lengths only if pin data exists
        pin_locations = [pin0loc, pin1loc, pin2loc, pin3loc]
        pin_lengths = [spring_lengths[i] + to_blender_scale(params["pin"][i]["length"]) for i in range(4)]
    else:
        # Default values if pin data is missing
        pin_locations = [(0, 0, 0)] * 4
        pin_lengths = [0] * 4
        print("Warning: 'pin' data missing in parameters.txt. Skipping pin imports.")
    cambers = [camber_0, camber_1, camber_2, camber_3]
    
    # Body
    try:
        body_path = get_path(params['body']['modelnum'], 'body')
        if body_path:
            body_obj = import_or_placeholder(body_path, "body", to_blender_coord(params["body"]["offset"]))
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
                wheel = import_or_placeholder(wheel_path, wheel_names[i], to_blender_coord(params['wheel'][i]['offset1']))
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
                    spring = import_or_placeholder(spring_path, spring_names[i], to_blender_coord(params['spring'][i]['offset']))
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
        for i in range(4):
            try:
                axle_path = get_path(params['axle'][i]['modelnum'], 'axle')
                if axle_path:
                    axle = import_or_placeholder(axle_path, axle_names[i], to_blender_coord(params['axle'][i]['offset']))
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
                    continue  # Skip this pin if ModelNum is -1
                pin_path = get_path(params['pin'][i]['modelnum'], 'pin')
                if pin_path:
                    pin = import_or_placeholder(pin_path, pin_names[i], pin_locations[i])
                    pin.parent = body_obj
                    pins.append(pin)
                    align_to_axis(pin, 'Z')
                    adjust_object_length(pin, pin_lengths[i], 'Z')
                    direction_to_wheel = Vector(wheel_locations[i]) - Vector(pin_locations[i])
                    direction_to_wheel.normalize()
                    opposite_direction = -direction_to_wheel
                    rot_quat = opposite_direction.to_track_quat('Z', 'Y')
                    pin.rotation_euler = rot_quat.to_euler()
                    move_distance = pin_lengths[i]
                    move_vector = direction_to_wheel * move_distance
                    pin.location += move_vector
                    print(f"Imported and oriented pin {pin_names[i]} away from wheel {wheel_names[i]}")
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
                spinner_obj = import_or_placeholder(spinner_path, "spinner", spinner_loc)
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
    
    # Apply UV maps to textures for all imported objects
    for obj in imported_objects:
        apply_uv_maps_to_textures(obj)

    return imported_objects

def extract_car_name(filepath):
    """
    Reads the car name from the parameters.txt file.
    """
    with open(filepath, 'r') as file:
        for line in file:
            if line.startswith("Name"):
                # Extract the car name by stripping 'Name', spaces, and quotes
                return line.split('\"')[1].strip()  # Get the text between the quotes
    return "Unknown Car"  # Default if not found
    
def import_all_textures(folder, car_name, params):
    """
    Import all .bmp files in the given folder as textures.
    If car.bmp is missing, try to load the car-specific texture (e.g., carname.bmp).
    If that fails, check for a TPAGE entry in parameters.txt.
    """
    car_texture_found = False

    for image_file in os.listdir(folder):
        if image_file.lower().endswith('.bmp'):
            img_path = os.path.join(folder, image_file)
            img_name = os.path.splitext(image_file)[0]

            # Import texture without appending car name
            if img_name not in bpy.data.images:
                img = bpy.data.images.load(img_path)
                img.name = img_name  # Use the original name (without .bmp suffix)
                print(f"Imported texture: {img_name}")

            if img_name.lower() == "car" or img_name.lower() == car_name.lower():
                car_texture_found = True

    # Fallback to load car-specific texture if car.bmp is not found
    if not car_texture_found:
        fallback_texture = f"{car_name.lower()}.bmp"
        fallback_path = os.path.join(folder, fallback_texture)
        if os.path.exists(fallback_path):
            fallback_name = os.path.splitext(fallback_texture)[0]  # Remove .bmp for naming
            if fallback_name not in bpy.data.images:
                img = bpy.data.images.load(fallback_path)
                img.name = fallback_name
                print(f"Fallback imported texture: {fallback_name}")
                car_texture_found = True
        else:
            print(f"Warning: Neither car.bmp nor {fallback_texture} found in {folder}")

    # Fallback to TPAGE if other methods fail
    if not car_texture_found and 'TPAGE' in params:
        tpage_texture = params['TPAGE'].split('\\')[-1]
        tpage_name = os.path.splitext(tpage_texture)[0]  # Remove .bmp suffix
        tpage_path = os.path.join(folder, tpage_texture)
        if os.path.exists(tpage_path):
            if tpage_name not in bpy.data.images:
                img = bpy.data.images.load(tpage_path)
                img.name = tpage_name
                print(f"Imported TPAGE texture: {tpage_name}")
        else:
            print(f"Warning: TPAGE texture {tpage_texture} not found in {folder}")
                
def apply_uv_maps_to_textures(obj):
    """
    Apply UV maps to the object similar to how car.bmp is mapped.
    """
    # Ensure the object has valid mesh data
    if obj is None or not isinstance(obj.data, bpy.types.Mesh):
        print(f"Skipping UV map application: {obj.name} is not a mesh.")
        return

    # Check if the object has UV layers
    if not obj.data.uv_layers:
        print(f"No UV maps found for {obj.name}, skipping UV assignment.")
        return

    uv_map = obj.data.uv_layers.active.name if obj.data.uv_layers else None
    if not uv_map:
        print(f"No active UV map found for {obj.name}.")
        return

    for material_slot in obj.material_slots:
        mat = material_slot.material
        if not mat or not mat.use_nodes or not mat.node_tree:
            continue
        
        for node in mat.node_tree.nodes:
            if node.type == 'TEX_IMAGE':
                # Check if the node has an ImageUser (only necessary if the node supports multiple images)
                if hasattr(node, 'image_user'):
                    # Ensure that the image_user attribute exists before accessing uv_map
                    node.image_user.use_auto_refresh = True  # Just an example of a valid attribute
                    print(f"Assigned UV map {uv_map} to {node.image.name} in {obj.name}")
                else:
                    print(f"ImageUser object has no attribute 'uv_map'. Skipping for {node.image.name}.")

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

def adjust_object_length(obj, target_length, length_axis='Z'):
    bpy.context.view_layer.update()
    bbox = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    if length_axis == 'Y':
        current_length = max(v.y for v in bbox) - min(v.y for v in bbox)
    elif length_axis == 'Z':
        current_length = max(v.z for v in bbox) - min(v.z for v in bbox)
    elif length_axis == 'X':
        current_length = max(v.x for v in bbox) - min(v.x for v in bbox)

    print(f"Before scaling, {obj.name} length along {length_axis}: {current_length}")

    if current_length > 0:
        scale_factor = target_length / current_length
        if length_axis == 'Y':
            obj.scale.y *= scale_factor
        elif length_axis == 'Z':
            obj.scale.z *= scale_factor
        elif length_axis == 'X':
            obj.scale.x *= scale_factor

        bpy.context.view_layer.update()
        print(f"Scaled {obj.name} along {length_axis} to target length {target_length}. Scale factor applied: {scale_factor}")

        bpy.context.view_layer.update()
        bbox = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
        new_length = max(getattr(v, length_axis.lower()) for v in bbox) - min(getattr(v, length_axis.lower()) for v in bbox)
        print(f"After scaling, {obj.name} length along {length_axis}: {new_length}")

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
    
def ensure_car_bmp_material(filepath, car_name):
    """
    Ensures the material for the car body is named 'car.bmp'.
    If 'car.bmp' is not found but 'carname.bmp' exists, rename the material to 'car.bmp'.
    """
    folder = os.path.dirname(filepath)
    car_texture_path = os.path.join(folder, "car.bmp")
    fallback_texture_path = os.path.join(folder, f"{car_name.lower()}.bmp")
    
    # Check if car.bmp exists
    if not os.path.exists(car_texture_path):
        if os.path.exists(fallback_texture_path):
            # Check if the material with the fallback name exists (including .bmp suffix)
            fallback_name = os.path.basename(fallback_texture_path)
            fallback_material = bpy.data.materials.get(fallback_name)
            
            if fallback_material:
                # Rename the material to car.bmp (with .bmp suffix)
                fallback_material.name = "car.bmp"
                print(f"Renamed material '{fallback_name}' to 'car.bmp'")
            else:
                print(f"Fallback material '{fallback_name}' not found in Blender materials.")
        else:
            print("Neither car.bmp nor fallback texture found after import.")
    else:
        print("car.bmp already exists, no renaming necessary.")