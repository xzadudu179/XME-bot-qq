from . import *
from ..faction import FACTIONS

class Moon(Celestial, CanDevelop):
    """卫星类型"""
    def __init__(self, name: str, desc: str, galaxy_location, location: tuple[int, int], planet_type: PlanetType, star, is_known=False, buildings=[], faction_id: int = 0) -> None:
        Celestial.__init__(self, galaxy_location=galaxy_location, location=location, name=name, desc=desc, faction_id=faction_id)
        CanDevelop.__init__(self, buildings)
        # 是否被开发
        # 未知的行星不可被雷达 / 星图发现
        self.is_known = is_known
        # 行星需要有恒星
        self.star = star
        self.planet_type = planet_type
        # 建筑物
        # self.buildings = buildings
        # 所属阵营
        # self.faction = factions.get(faction_id, factions[0])