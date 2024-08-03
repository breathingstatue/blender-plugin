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

def import_file(filepath, scene):
    """
    Imports a parameters.txt file and loads car body and wheels.
    """
    PARAMETERS[filepath] = carinfo.read_parameters(filepath)
    import_car(PARAMETERS[filepath], filepath, scene)
    PARAMETERS.pop(filepath)

def import_car(params, filepath, scene):
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
    
    def get_single_file_with_keyword(keyword):
        files = [f for f in os.listdir(folder) if keyword in f.lower() and f.lower().endswith('.prm')]
        return files[0] if len(files) == 1 else None

    def get_path(model_num, keyword):
        model_path = get_single_file_with_keyword(keyword)
        if model_path:
            return os.path.join(folder, model_path)
        if model_num >= 0:
            model_file = params['model'][model_num]
            model_path = os.path.join(folder, model_file.split(os.sep)[-1])
            if os.path.exists(model_path):
                return model_path
        return None

    def import_or_placeholder(path, name, obj_location):
        if path:
            obj = prm_in.import_file(path, bpy.context.scene)
        else:
            obj = create_placeholder(name)
    
        obj.location = obj_location
        bpy.context.collection.objects.link(obj)
        obj.name = name
        return obj

    body_path = get_path(params['body']['modelnum'], 'body')
    body_obj = import_or_placeholder(body_path, "body", to_blender_coord(params["body"]["offset"]))
    body_obj.name = "body"
    
    wheel_names = ['wheelfl', 'wheelfr', 'wheelbl', 'wheelbr']
    spring_names = ['spring0', 'spring1', 'spring2', 'spring3']
    axle_names = ['axle0', 'axle1', 'axle2', 'axle3']

    wheel_locations = [wheel0loc, wheel1loc, wheel2loc, wheel3loc]
    spring_lengths = [spring0length, spring1length, spring2length, spring3length]
    axle_lengths = [axle0length, axle1length, axle2length, axle3length]
    
    for i in range(4):
        wheel_path = get_path(params['wheel'][i]['modelnum'], 'wheel')
        wheel = import_or_placeholder(wheel_path, wheel_names[i], to_blender_coord(params['wheel'][i]['offset1']))
        wheel.parent = body_obj
        
    springs = []
    for i in range(4):
        spring_path = get_path(params['spring'][i]['modelnum'], 'spring')
        if spring_path:
            spring = import_or_placeholder(spring_path, spring_names[i], to_blender_coord(params['spring'][i]['offset']))
            spring.parent = body_obj
            spring.location = to_blender_coord(params['spring'][i]['offset'])
            springs.append(spring)
            align_to_axis(spring, 'Z')
            adjust_object_length(spring, spring_lengths[i], 'Z')
            if is_aligned(spring):
                set_spring_orientation(spring, wheel_locations[i])
            print(f"Imported and aligned {spring.name}")

    axles = []
    for i in range(4):
        axle_path = get_path(params['axle'][i]['modelnum'], 'axle')
        if axle_path:
            axle = import_or_placeholder(axle_path, axle_names[i], to_blender_coord(params['axle'][i]['offset']))
            axle.parent = body_obj
            axle.location = to_blender_coord(params['axle'][i]['offset'])
            axles.append(axle)
            align_to_axis(axle, 'Y')
            adjust_object_length(axle, axle_lengths[i], 'Y')
            set_orientation(axle, wheel_locations[i])
            print(f"Adjusted length and set orientation for {axle.name}")
    
    aerial = bpy.data.objects.new("aerial", None)
    scene.collection.objects.link(aerial)
    aerial.location = aerial_loc
    aerial.empty_display_type = 'PLAIN_AXES'
    aerial.empty_display_size = 0.1
    aerial.parent = body_obj

def create_placeholder(name):
    obj = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(obj)
    obj.empty_display_type = 'PLAIN_AXES'
    obj.empty_display_size = 0.1
    return obj

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
