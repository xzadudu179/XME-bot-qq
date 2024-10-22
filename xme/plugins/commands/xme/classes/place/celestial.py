from enum import Enum

class CelestialType(Enum):
    """天体类型"""
    UNKNOWN = '未知'
    STATION = '空间站'
    PLANET = '星球'
    SHIP = '舰船'

class Celestial:
    """天体地点 可被雷达显示
    """
    # 天体会有 名称 介绍 位置坐标
    def __init__(self, name: str, desc: str, location: tuple[int, int], type: CelestialType = CelestialType.UNKNOWN) -> None:
        self.name = name
        self.desc = desc
        self.location = location
        self.type = type

