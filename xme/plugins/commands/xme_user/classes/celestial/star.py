from . import *
import math
from xme.xmetools.randtools import random_percent
from xme.xmetools.jsontools import read_from_path, save_to_path
import random

class Star(Celestial, CanDevelop):
    """恒星类型"""
    def __init__(self, name: str, desc: str, galaxy_location, location: tuple[int, int], star_type: StarType = None, buildings=[], faction_id = 0, thermal_luminosity=-1, uid=None) -> None:
        Celestial.__init__(self, galaxy_location=galaxy_location, location=location, name=name, desc=desc, faction_id=faction_id, uid=uid)
        CanDevelop.__init__(self, buildings)
        # 恒星类型
        self.star_type = star_type
        if not self.star_type:
            # self.star_type = random.choice(list(StarType))
            for star_type, probability in star_probabilities.items():
                self.star_type = star_type if random_percent(probability) else self.star_type
            if not self.star_type:
                # 红矮星默认
                self.star_type = StarType.RED_DWARF
        # 建筑物
        self.buildings = buildings
        # 辐射热发光度
        if thermal_luminosity < 0:
            self.thermal_luminosity = self.calc_thermal_luminosity()
        else:
            self.thermal_luminosity = thermal_luminosity
        # 宜居带中心距离
        self.habitable_zone = math.sqrt(self.thermal_luminosity) / 0.05
        self.gen_random_info()
        self.img_path = f"./static/img/stars/{self.star_type.value}/imgs"

    def __str__(self):
        return f"[{self.star_type.value}] {self.name}\n{self.desc}\n发光度：{self.thermal_luminosity}\n宜居带距离：{self.habitable_zone:.2f}"

    def calc_thermal_luminosity(self) -> float:
        # self.star_type
        return random.uniform(*star_thermal_luminosity_range[self.star_type])

    def gen_random_info(self):
        if not self.name:
            used_names: list = read_from_path("data/used_names.json")
            first = random.choice(["MER", "H", "TZ", "P", "AST"])
            num = random.randint(0, 12800)
            suffix = random.choice(["D", "D", "D", "D" "C", "C", "C", "C", "C" "B", "B"])
            suffix = "A" if random_percent(10) else suffix
            if self.star_type in [
                StarType.BLACKHOLE,
                StarType.RED_GIANT,
                StarType.RED_GIANT,
                StarType.YELLOW_GIANT,
                StarType.RED_SUPERGIANT,
                StarType.BLUE_SUPERGIANT,
                StarType.YELLOW_SUPERGIANT,
                StarType.NEUTRON_STAR]:
                suffix = random.choice(["B", "B", "A"])
            suffix = "R" if random_percent(3) else suffix
            if self.faction.id in [4, 5, 7, 9]:
                suffix = suffix + "Z" if random_percent(50) else suffix
                suffix = suffix + "X" if random_percent(50) else suffix
            self.name = f"{first}-{num}{suffix}"
            used_names.append(self.name)
            save_to_path("data/used_names.json", used_names)
        if not self.desc:
            self.desc = self.star_type.value

    def __dict__(self):
        return {
            "type": "Star",
            "uid": self.uid,
            "name": self.name,
            "desc": self.desc,
            "galaxy_location": self.galaxy_location,
            "location": self.location,
            "faction": self.faction.id,
            "star_type": self.star_type.value,
            "buildings": self.buildings,
            "thermal_luminosity": self.thermal_luminosity,
        }

    @staticmethod
    def load(celestial_dict):
        # from ..xme_map import get_starfield_map
        return Star(
            # starfield_map=get_starfield_map(celestial_dict["galaxy_location"]),
            uid=celestial_dict["uid"],
            name=celestial_dict["name"],
            desc=celestial_dict["desc"],
            galaxy_location=celestial_dict["galaxy_location"],
            location=tuple([x for x in celestial_dict["location"]]),
            faction_id=celestial_dict["faction"],
            thermal_luminosity=celestial_dict["thermal_luminosity"],
            star_type=StarType(celestial_dict["star_type"]),
            buildings=celestial_dict["buildings"]
        )