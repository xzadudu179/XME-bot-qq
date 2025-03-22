from . import *
from ..faction import FACTIONS

class Ship(Celestial):
    """飞船类型"""
    def __init__(self, starfield_map, name: str, desc: str, galaxy_location, location: tuple[int, int], faction_id: int = 0, buildings=[]) -> None:
        Celestial.__init__(self, starfield_map=starfield_map, galaxy_location=galaxy_location, location=location, name=name, desc=desc, faction_id=faction_id)
        CanDevelop.__init__(self, buildings)
