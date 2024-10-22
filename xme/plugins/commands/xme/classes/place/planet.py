from xme.plugins.commands.xme.classes.place.celestial import CelestialType
from .celestial import *
from enum import Enum

class PlanetType(Enum):
    """行星类型"""
    DESOLATE = '荒凉星球'


class Planet(Celestial):
    """行星类型"""
    def __init__(self, name: str, desc: str, location: tuple[int, int], planet_type, is_known=False, type: CelestialType=CelestialType.PLANET) -> None:
        super().__init__(name, desc, location, type)
        # 是否被开发
        # 未知的行星不可被雷达 / 星图发现
        self.is_known = is_known
        self.planet_type = planet_type