from enum import Enum
from ..faction import FACTIONS
import uuid
class Celestial:
    """天体地点 可被雷达显示
    """
    # 天体会有 uid 所属星域地图 所属银河系地图位置 所属星域地图位置 名称 介绍 位置坐标
    def __init__(self,  galaxy_location: tuple[int, int], location: tuple[int, int], name: str = "", desc: str = "", faction_id: int = 0) -> None:
        # from ..xme_map import get_starfield_map
        self.uid = uuid.uuid4()
        self.name = name
        self.desc = desc
        self.galaxy_location = galaxy_location
        self.location = location
        self.faction = FACTIONS.get(faction_id, FACTIONS[0])

    def __dict__(self):
        return {
            "type": "Celestial",
            "uid": self.uid,
            "name": self.name,
            "desc": self.desc,
            "galaxy_location": self.galaxy_location,
            "location": self.location,
            "faction": self.faction.id,
        }

    @staticmethod
    def load(celestial_dict):
        # from ..xme_map import get_starfield_map
        return Celestial(
            # starfield_map=get_starfield_map(celestial_dict["galaxy_location"]),
            name=celestial_dict["name"],
            desc=celestial_dict["desc"],
            galaxy_location=tuple(celestial_dict["galaxy_location"]),
            location=tuple([x for x in celestial_dict["location"].split(",")]),
            faction_id=celestial_dict["faction"],
        )

class CanDevelop:
    """可被开发
    """
    def __init__(self, buildings=[]):
        self.buildings = buildings

class PlanetType(Enum):
    DESOLATE = "荒凉星球"
    DRY = "干旱星球"
    FUNGI = "菌类星球"
    CITY = "城市星球"
    GAS = "气态巨行星"
    SEA = "海洋星球"
    LAVA = "熔岩星球"
    VOLCANIC = "火山星球"
    TERRESTRIAL = "陆地星球"
    ROCK = "岩石星球"
    TOXIC = "有毒星球"
    UNNATURAL = "非自然星球"
    ICE = "冰封星球"
    ICE_GIANT = "冰巨星"
    STRUCTURE = "构造体星球"

planet_probabilities = {
    PlanetType.DESOLATE: 20,
    PlanetType.DRY: 20,
    PlanetType.GAS: 15,
    PlanetType.SEA: 4,
    PlanetType.LAVA: 50,
    PlanetType.VOLCANIC: 10,
    PlanetType.TERRESTRIAL: 5,
    PlanetType.ROCK: 80,
    PlanetType.TOXIC: 50,
    PlanetType.ICE: 30,
    PlanetType.ICE_GIANT: 20,
}

class StarType(Enum):
    RED_SUPERGIANT = "红超巨星"
    YELLOW_SUPERGIANT = "黄超巨星"
    BLUE_SUPERGIANT = "蓝超巨星"
    RED_GIANT = "红巨星"
    BLUE_GIANT = "蓝巨星"
    YELLOW_GIANT = "黄巨星"
    YELLOW_DWARF = "黄矮星"
    ORANGE_DWARF = "橙矮星"
    WHITE_DWARF = "白矮星"
    RED_DWARF = "红矮星"
    NEUTRON_STAR = "中子星"
    BLACKHOLE = "黑洞"

star_probabilities = {
    StarType.RED_SUPERGIANT: 0.001,
    StarType.YELLOW_SUPERGIANT: 0.01,
    StarType.BLUE_SUPERGIANT: 0.01,
    StarType.RED_GIANT: 5,
    StarType.BLUE_GIANT: 0.5,
    StarType.YELLOW_GIANT: 1,
    StarType.YELLOW_DWARF: 7,
    StarType.ORANGE_DWARF: 12,
    StarType.WHITE_DWARF: 5,
    StarType.RED_DWARF: 73,
    StarType.NEUTRON_STAR: 0.001,
    StarType.BLACKHOLE: 0.0001,
}

star_thermal_luminosity_range: dict[StarType, tuple[float, float]] = {
    StarType.RED_SUPERGIANT: (10000.0, 300000.0),
    StarType.YELLOW_SUPERGIANT: (1000.0, 100000.0),
    StarType.BLUE_SUPERGIANT: (10000.0, 300000.0),
    StarType.RED_GIANT: (100.0, 10000.0),
    StarType.BLUE_GIANT: (1000.0, 100000.0),
    StarType.YELLOW_GIANT: (100.0, 10000.0),
    StarType.YELLOW_DWARF: (0.1, 10),
    StarType.ORANGE_DWARF: (0.01, 0.6),
    StarType.WHITE_DWARF: (0.0001, 0.01),
    StarType.RED_DWARF: (0.0001, 0.1),
    StarType.NEUTRON_STAR: (0.000003, 0.00001),
    StarType.BLACKHOLE: (0.000000001, 0.000000001),
}

# 至少距离宜居带多近的范围才可能生成该行星 一单位 0.05au，负数代表接近恒星
planet_HZproximity = {
    (0.3, 0.8): PlanetType.DESOLATE,
    (-0.25, -0.05): PlanetType.DRY,
    (1.5, 10): PlanetType.GAS,
    (0.99, 1.02): PlanetType.TERRESTRIAL,
    (0.97, 1.02): PlanetType.SEA,
    (-100, -30): PlanetType.LAVA,
    (-0.5, -0.1): PlanetType.VOLCANIC,
    (-35, 100): PlanetType.ROCK,
    (-0.27, 0.1): PlanetType.TOXIC,
    (0.5, 100): PlanetType.ICE,
    (0.5, 100): PlanetType.ICE_GIANT,
}

planet_type_desc = {
    PlanetType.DESOLATE: "曾经或许是地球一般宜居的行星，但是环境的改变让这颗行星变成了遍布尘土，空气稀薄的恶地，被狂风与沙尘肆虐着...",
    PlanetType.DRY: "",
    PlanetType.FUNGI: "满是菌类的星球，已经见不到任何",
    PlanetType.CITY: "",
    PlanetType.TERRESTRIAL: "",
    PlanetType.GAS: "",
    PlanetType.SEA: "",
    PlanetType.LAVA: "",
    PlanetType.VOLCANIC: "",
    PlanetType.ROCK: "",
    PlanetType.TOXIC: "",
    PlanetType.UNNATURAL: "",
    PlanetType.ICE: "",
    PlanetType.ICE_GIANT: "",
    PlanetType.STRUCTURE: ""
}