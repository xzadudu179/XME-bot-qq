from enum import Enum
from ..faction import FACTIONS
import uuid
import os
from PIL import Image
# from xme.xmetools.randtools import change_seed
import random

class Celestial:
    """天体地点 可被雷达显示
    """
    # 天体会有 uid 所属星域地图 所属银河系地图位置 所属星域地图位置 名称 介绍 位置坐标
    def __init__(self, galaxy_location: tuple[int, int], location: tuple[int, int], name: str = "", desc: str = "", faction_id: int = 0, uid=None) -> None:
        # from ..xme_map import get_starfield_map
        if not uid:
            self.uid: str = str(uuid.uuid4())
        else:
            self.uid = uid
        self.name = name
        self.desc = desc
        self.galaxy_location = galaxy_location
        self.location = location
        self.faction = FACTIONS.get(faction_id, FACTIONS[0])
        self.img_path = None

    def get_image(self, default=None) -> str | None:
        random.seed(self.uid)
        if self.img_path is None:
            random.seed()
            return default
        # path = f"./static/img/planets/{t.value}/imgs"
        try:
            imgs =  os.listdir(self.img_path)
        except FileNotFoundError:
            imgs = []
        results = []
        for img in imgs:
            try:
                with Image.open(os.path.join(self.img_path, img)) as i:
                    i.verify()  # 只验证文件，不加载完整内容
                results.append(img)
            except Exception:
                continue
        if not results:
            random.seed()
            return default
        random.seed()
        img_path = random.choice(results)
        return os.path.join(self.img_path, img_path)

    def __str__(self):
        return self.desc

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
            uid=celestial_dict["uid"],
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
    PlanetType.DESOLATE: 45,
    PlanetType.DRY: 45,
    PlanetType.GAS: 15,
    PlanetType.SEA: 10,
    PlanetType.LAVA: 50,
    PlanetType.VOLCANIC: 10,
    PlanetType.TERRESTRIAL: 13,
    PlanetType.ROCK: 60,
    PlanetType.TOXIC: 20,
    PlanetType.ICE: 6,
    PlanetType.ICE_GIANT: 15,
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
    StarType.RED_SUPERGIANT: 0.2,
    StarType.YELLOW_SUPERGIANT: 0.15,
    StarType.BLUE_SUPERGIANT: 0.15,
    StarType.RED_GIANT: 5,
    StarType.BLUE_GIANT: 0.7,
    StarType.YELLOW_GIANT: 1,
    StarType.YELLOW_DWARF: 40,
    StarType.ORANGE_DWARF: 26,
    StarType.WHITE_DWARF: 8,
    StarType.RED_DWARF: 50,
    StarType.NEUTRON_STAR: 0.1,
    StarType.BLACKHOLE: 0.1,
}

star_type_color = {
    StarType.RED_SUPERGIANT: "#F14336",
    StarType.YELLOW_SUPERGIANT: "#F1ED18",
    StarType.BLUE_SUPERGIANT: "#3180FF",
    StarType.RED_GIANT: "#DB3024",
    StarType.BLUE_GIANT: "#6694DF",
    StarType.YELLOW_GIANT: "#EFEC57",
    StarType.YELLOW_DWARF: "#ECEBBF",
    StarType.ORANGE_DWARF: "#F5A453",
    StarType.WHITE_DWARF: "#BCBAB8",
    StarType.RED_DWARF: "#DB8F8F",
    StarType.NEUTRON_STAR: "#98FDF4",
    StarType.BLACKHOLE: "#9667E6",
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
    StarType.RED_DWARF: (0.01, 0.1),
    StarType.NEUTRON_STAR: (1, 1000),
    StarType.BLACKHOLE: (0.000000001, 0.000000001),
}

# 至少距离宜居带多近的范围才可能生成该行星 一单位相较于太阳 0.05au，负数代表接近恒星
planet_HZproximity = {
    (0.3, 0.8): PlanetType.DESOLATE,
    (-0.25, -0.05): PlanetType.DRY,
    (-1.5, 25): PlanetType.GAS,
    (-0.05, 0.05): PlanetType.TERRESTRIAL,
    (-0.05, 0.04): PlanetType.SEA,
    (-10000000000, -60): PlanetType.LAVA,
    (-10, -3): PlanetType.VOLCANIC,
    (-60, 10000000000): PlanetType.ROCK,
    (-2.7, 1): PlanetType.TOXIC,
    (2, 90): PlanetType.ICE,
    (20, 120): PlanetType.ICE_GIANT,
}

planet_type_color = {
    PlanetType.DESOLATE: "#aba873",
    PlanetType.DRY: "#F5BE4F",
    PlanetType.FUNGI: "#3E695D",
    PlanetType.CITY: "#405F88",
    PlanetType.TERRESTRIAL: "#47b32f",
    PlanetType.GAS: "#D6CFB8",
    PlanetType.SEA: "#3D93FB",
    PlanetType.LAVA: "#F05232",
    PlanetType.VOLCANIC: "#7C2D09",
    PlanetType.ROCK: "#5B5B5B",
    PlanetType.TOXIC: "#91FF26",
    PlanetType.UNNATURAL: "#782DD3",
    PlanetType.ICE: "#98deee",
    PlanetType.ICE_GIANT: "#6271FC",
    PlanetType.STRUCTURE: "#DABAFF",
}

planet_type_desc = {
    PlanetType.DESOLATE: "曾经或许是地球一般宜居的行星，但是环境的改变让这颗行星变成了遍布尘土，空气稀薄的恶地，被狂风与沙尘肆虐着...",
    PlanetType.DRY: "干燥，植物稀少的星球，沙漠随处可见，恶劣的环境让开发这颗星球变得困难，但是相比于宇宙中大部分极端危险的星球来说，这样的星球已经有足够价值。",
    PlanetType.FUNGI: "表面几乎被真菌覆盖的星球，已经见不到太多原本地表的环境。除了那些真菌本身以外，这样的星球在大多数生物眼里都是极度危险的。",
    PlanetType.CITY: "城市化完全的星球，大气控制系统维持着环境的舒适，已经见不到太多天然景观与地形。人造的生物圈维持着星球上仅有的一片绿色，而生物圈之外就是由钢铁铸成的世界。",
    PlanetType.TERRESTRIAL: "漂亮且稀有的行星，植被与生物遍布，到处都有独特的自然景观可供欣赏。",
    PlanetType.GAS: "由氢，氦气为主构成的气态巨行星，看起来庞大又神秘。",
    PlanetType.SEA: "遍布海洋的类地行星，陆地面积极少。尽管生态圈非常丰富，但那些生物们大多都潜伏在海底...",
    PlanetType.LAVA: "由于地质或位置的影响，让这颗星球充斥着熔岩，地狱一般的景象也说明其地表环境极端危险。",
    PlanetType.VOLCANIC: "尽管没有熔岩星球那样骇人，但是遍布星球的火山多少让这颗星球极度危险和不稳定，在地表进行探险时一定要万分小心。",
    PlanetType.ROCK: "宇宙中最常见的一类星球，几乎没有任何生命的痕迹...不过有的时候能在这样的星球上发现非常丰富的矿产资源。",
    PlanetType.TOXIC: "或是由于温室失控，又或是因为某些奇怪的事情让这颗星球拥有厚厚的有毒大气层，其地表温度很可能不理想。",
    PlanetType.UNNATURAL: "一种奇怪的星球...其大气成分非常独特，可能会导致幻觉...",
    PlanetType.ICE: "由于寒冷被冰封的星球，地表勉强可以居住，冰层之下可能有丰富的生态圈。",
    PlanetType.ICE_GIANT: "另一类巨行星，由氧，碳，氮气等较重的气体组成，这种行星有狂暴且多变的气候，且内部压力极大。",
    PlanetType.STRUCTURE: "这颗行星的表面完全被各种构造体覆盖了...完全看不出来它曾经是什么样子了。"
}