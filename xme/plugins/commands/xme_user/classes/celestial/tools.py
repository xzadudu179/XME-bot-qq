# from . import *
from .planet import Planet
from .star import Star

def load_celestial(celestial_dict: dict):
    match celestial_dict["type"]:
        case "Planet":
            result = Planet.load(celestial_dict)
        case "Star":
            result = Star.load(celestial_dict)
        case _:
            raise ValueError("错误的天体类型")
    return result