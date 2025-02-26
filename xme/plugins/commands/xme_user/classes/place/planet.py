from .celestial import *

class Planet(Celestial):
    """行星类型"""
    def __init__(self, id: int, name: str, desc: str, location: tuple[int, int], planet_type: PlaentType, star, is_known=False) -> None:
        super().__init__(id, name, desc, location)
        # 是否被开发
        # 未知的行星不可被雷达 / 星图发现
        self.is_known = is_known
        # 行星需要有恒星
        self.star = star
        self.planet_type = planet_type