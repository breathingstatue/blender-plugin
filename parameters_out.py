"""
Name:    parameters_out
Purpose: Exporting cars parameters useful for the parameters.txt files

Description:
Prints most valuable car parameters into clipboard.

"""

from http.client import NON_AUTHORITATIVE_INFORMATION
from pickle import NONE
import bpy
import importlib
from . import common

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
    params += f"Class\\tt0\t; Engine type (0 = Elec, 1 = Glow, 2 = Other)\n"
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

def append_static_placeholders(params):
    # Append static placeholders for SPRING details
    for i in range(4):
        params += f"\nSPRING {i} {{\t; Start Spring\n"
        params += f"ModelNum\t-1\n"
        params += f"Offset\t\t0.000000 0.000000 0.000000\n"
        params += f"Length\t\t0.000000\n"
        params += f"Stiffness\t1000.000000\n"
        params += f"Damping\t\t10.000000\n"
        params += f"Restitution\t-0.500000\n"
        params += "}\t\t; End Spring\n\n"

    # Append static placeholders for PIN details
    for i in range(4):
        params += f"\nPIN {i} {{\t; Start Pin\n"
        params += f"ModelNum\t-1\n"
        params += f"Offset\t\t0.000000 0.000000 0.000000\n"
        params += f"Length\t\t0.000000\n"
        params += "}\t\t; End Pin\n\n"

    # Append static placeholders for AXLE details
    for i in range(4):
        params += f"\nAXLE {i} {{\t; Start Axle\n"
        params += f"ModelNum\t-1\n"
        params += f"Offset\t\t0.000000 0.000000 0.000000\n"
        params += f"Length\t\t0.000000\n"
        params += "}\t\t; End Axle\n\n"

    # Append static placeholder for SPINNER details
    params += f"SPINNER {{\t; Start spinner\n"
    params += f"ModelNum\t-1\n"
    params += f"Offset\t\t0.000000 0.000000 0.000000\n"
    params += f"Axis\t\t0.000000 1.000000 0.000000\n"
    params += f"AngVel\t\t0.000000\n"
    params += "}\t\t; End Spinner\n"
    
    return params

def append_aerial_info(params, body, processed):
    # Append aerial info, fetching dynamic offset
    for child in body.children:
        if "aerial" in child.name.lower() and child.name not in processed:
            location = to_revolt_coord(child.location)
            params += f"\nAERIAL {{\t; Start Aerial\n"
            params += f"SecModelNum\t17\nTopModelNum\t18\n"
            params += f"Offset\t\t{location[0]:.6f} {location[1]:.6f} {location[2]:.6f}\n"
            params += f"Direction\t0.000000 -1.000000 0.000000\n"
            params += f"Length\t\t17.000000\n"
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
    params = append_static_placeholders(params)
    params = append_aerial_info(params, body, processed)

    bpy.context.window_manager.clipboard = params