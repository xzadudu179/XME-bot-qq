from enum import Enum

class Celestial:
    """天体地点 可被雷达显示
    """
    # 天体会有 id 名称 介绍 位置坐标
    def __init__(self, id, name: str, desc: str, location: tuple[int, int]) -> None:
        self.id = id
        self.name = name
        self.desc = desc
        self.location = location
        self.type = type

class PlaentType(Enum):
    DESOLATE = "荒凉星球"
    DRY = "干旱星球"
    FUNGI = "菌类星球"
    CITY = "城市星球"
    GAS = "气态巨行星"
    SEA = "海洋星球"
    LAVA = "熔岩星球"
    VOLCANIC = "火山星球"
    ROCK = "岩石星球"
    TOXIC = "有毒星球"
    UNNATURAL = "非自然星球"
    ICE = "冰封星球"
    ICE_GIANT = "冰巨星"
    STRUCTURE = "构造体星球"