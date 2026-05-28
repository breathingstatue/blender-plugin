"""
Name:    fob_subtypes
Purpose: Providing variables for FOB Objects.

Description:
Contains values that are specific to Re-Volt, functions for converting units
and helper functions for Blender. 
"""


def _range_token(value):
    return f"m{abs(value)}" if value < 0 else str(value)


def fob_subtype_range_property_name(index, min_value, max_value):
    return f"fob_subtype_{index}_range_{_range_token(min_value)}_{_range_token(max_value)}"

OBJECT_TYPE_NAMES = {
    0: "Spinning Barrel",
    1: "Beachball",
    2: "Planet",
    3: "Plane",
    4: "Copter",
    5: "Dragon",
    6: "Water",
    7: "Trolley",
    8: "Boat",
    9: "Speedup",
    10: "Radar",
    11: "Balloon",
    12: "Horse",
    13: "Train",
    14: "Strobe",
    15: "Football",
    16: "Spark Generator",
    17: "Space Man",
    30: "Pickup",
    32: "Flappage",
    33: "Laser",
    36: "Wobbly Cone",
    37: "Probe Logo",
    38: "Clouds",
    39: "Name Entry",
    40: "Sprinkler",
    41: "Sprinkler Hose",
    42: "Object Thrower",
    43: "BasketBall",
    44: "TrackScreen",
    45: "Clock",
    46: "CarBox",
    47: "Stream",
    48: "Cup",
    49: "3D Sound",
    50: "Star",
    52: "Tumbleweed",
    53: "Small Screen",
    54: "Lantern",
    55: "Skybox",
    56: "Slider",
    57: "Bottle",
    58: "Bucket",
    59: "Cone",
    60: "Can",
    61: "Lilo",
    63: "Rain",
    64: "Lightning",
    65: "Ship light",
    66: "Packet",
    67: "ABC Block",
    68: "Water Box",
    69: "Water Ripples",
    70: "Gari flag",
    71: "Dolphin",
    72: "Garden Fox",
    73: "Fog Box",
    74: "Chopper",
    75: "Disco",
    76: "Custom Animation"
}

OBJECT_SUBTYPE_DESCRIPTIONS = {
    0: ["Speed"],
    2: ["Name", "Orbit", "Orbit Speed", "Spin Speed"],
    3: ["Speed", "Radius", "Bank"],
    4: ["X range", "Y range", "Z range", "Y offset"],
    8: ["Type"],
    9: ["Width", "LoSpeed", "HiSpeed", "Time"],
    14: ["Type", "Sequence Num", "Sequence Count"],
    16: ["Type", "Av. Speed", "Var. Speed", "Frequency"],
    33: ["Width", "Rand", "Object"],
    40: ["id"],
    41: ["id"],
    42: ["id", "Object", "Speed", "ReUse"],
    46: ["id"],
    47: ["Model"],
    48: ["Type"],
    49: ["Name", "Range", "Mode", "Start Time"],
    50: ["Type"],
    55: ["Level"],
    56: ["id"],
    57: ["Stop"],
    68: ["X range", "Y range", "Z range"],
    69: ["Model"],
    70: ["Garyness"],
    76: ["Type", "Start offset", "Hide in Time Trial", "Trigger ID"]
}

OBJECT_SUBTYPE_VALUES = {
    0: {  # Spinning Barrel
        0: list(range(-255, 256))
    },
    2: {  # Planet
        0: ["Mercury", "Venus", "Earth", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto", "Moon", "Rings", "Sun"],
        1: ["Mercury", "Venus", "Earth", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto", "Moon", "Rings", "Sun"],
        2: list(range(-255, 256)),
        3: list(range(-255, 256))
    },
    3: {  # Plane
        0: list(range(-255, 256)),
        1: list(range(1025)),
        2: list(range(-256, 257))
    },
    4: {  # Copter
        0: list(range(257)),
        1: list(range(257)),
        2: list(range(257)),
        3: list(range(-256, 257))
    },
    8: {  # Boat
        0: ["Sail", "Tug"]
    },
    9: {  # Speedup
        0: list(range(10, 101)),
        1: list(range(101)),
        2: list(range(101)),
        3: list(range(51))
    },
    14: {  # Strobe
        0: ["Muse Post", "Muse Wall", "Hood Tunnel"],
        1: list(range(501)),
        2: list(range(1, 501))
    },
    16: {  # Spark Generator
        0: ["SPARK", "SPARK2", "SNOW", "POPCORN", "GRAVEL", "SAND", "GRASS", "ELECTRIC", "WATER", "DIRT",
            "SMOKE1", "SMOKE2", "SMOKE3", "BLUE", "BIGBLUE", "SMALLORANGE", "SMALLRED", "EXPLOSION1", "EXPLOSION2",
            "STAR", "PROBE_SMOKE", "SPRINKLER", "SPRINKLER_BIG", "DOLPHIN", "DOLPHIN_BIG", "SPARK3", "ROADDUST",
            "GRASSDUST", "SOILDUST", "GRAVELDUST", "SANDDUST"] + [f"Type {i}" for i in range(31, 64)],
        1: list(range(201)),
        2: list(range(201)),
        3: list(range(1, 201))
    },
    33: {  # Laser
        0: list(range(1, 11)),
        1: list(range(1, 11)),
        2: ["No", "Yes"]
    },
    40: {  # Sprinkler
        0: list(range(256))
    },
    41: {  # Sprinkler Hose
        0: list(range(256))
    },
    42: {  # Object Thrower
        0: list(range(256)),
        1: [
            "BARREL", "BEACHBALL", "PLANET", "PLANE", "COPTER", "DRAGON", "WATER", "TROLLEY", "BOAT", "SPEEDUP",
            "RADAR", "BALLOON", "HORSE", "TRAIN", "STROBE", "FOOTBALL", "SPARKGEN", "SPACEMAN", "SHOCKWAVE",
            "FIREWORK", "PUTTYBOMB", "WATERBOMB", "ELECTROPULSE", "OILSLICK", "OILSLICK_DROPPER", "CHROMEBALL",
            "CLONE", "TURBO", "ELECTROZAPPER", "SPRING", "PICKUP", "DISSOLVEMODEL", "FLAP", "LASER", "SPLASH",
            "BOMBGLOW", "WEEBEL", "PROBELOGO", "CLOUDS", "NAMEWHEEL", "SPRINKLER", "SPRINKLER_HOSE",
            "OBJECT_THROWER", "BASKETBALL", "TRACKSCREEN", "CLOCK", "CARBOX", "STREAM", "CUP", "3DSOUND", "STAR",
            "FOX", "TUMBLEWEED", "SMALLSCREEN", "LANTERN", "SKYBOX", "SLIDER", "BOTTLE", "BUCKET", "CONE", "CAN",
            "LILO", "GLOBAL", "RAIN", "LIGHTNING", "SHIPLIGHT", "PACKET", "ABC", "WATERBOX", "RIPPLE", "FLAG",
            "DOLPHIN", "GARDEN_FOG", "FOGBOX", "CHOPPER", "DISCO", "CUSTOM_ANIMATION"
        ],
        2: list(range(-1, 101)),
        3: ["No", "Yes"]
    },
    46: {  # CarBox
        0: list(range(-1, 49))
    },
    47: {  # Stream
        0: list(range(6))
    },
    48: {  # Cup
        0: ["BRONZE", "SILVER", "GOLD", "PLATINUM"]
    },
    49: {  # 3D Sound
        0: [
            "Hood Dog Bark", "Hood Kids", "Hood TV", "Hood Lawnmower", "Hood Digger", "Hood Birds 2",
            "Hood Birds 3", "Toy Arcade", "Hood Stream", "Garden tropics2", "Garden tropics3", "Garden tropics4",
            "Muse ambience", "Market air cond", "Market cabinet hum", "Market car park", "Market freezer",
            "Market icy", "Muse escalator", "Muse barrel", "Muse door", "Garden stream", "Ghost coyote",
            "Ghost bats", "Ghost eagle", "Ghost drip", "Ghost rattle", "Ship internal ambience", "Ship seagulls",
            "Ship foghorn", "Ship thunder", "Ship storm", "Ship calm", "Garden animal wierd", "Garden animal bird1",
            "Garden animal bird2", "Garden animal frog", "Hood ambience", "Ghost bell", "Roof traffic ambience",
            "Roof chopper", "Roof siren", "Roof wind", "Roof steam hiss", "Roof electric hum", "Roof telemetry",
            "Roof air conditioner", "Hood Birds 1"
        ],
        1: list(range(101)),
        2: ["Continuous", "Random", "Play Once"],
        3: list(range(1001))
    },
    50: {  # Star
        0: ["Global Weapon", "Practice Star"]
    },
    55: {  # Skybox
        0: ["Toytanic day", "Toytanic night", "Wild West", "Neighborhood", "Rooftops"]
    },
    56: {  # Slider
        0: [0, 1]
    },
    57: {  # Bottle
        0: ["No", "Yes"]
    },
    68: {  # Water Box
        0: list(range(20001)),
        1: list(range(20001)),
        2: list(range(20001))
    },
    69: {  # Water Ripples
        0: ["Hood Stream", "Toytanic Pool", "Garden 1", "Garden 2", "Garden 3", "Garden 4"]
    },
    70: {  # Gari flag
        0: list(range(11))
    },
    76: {  # Custom Animation
        0: list(range(256)),
        1: list(range(10001)),
        2: ["No", "Yes"],
        3: list(range(256))
    }
}
