from . import *
from ..faction import FACTIONS
from xme.xmetools.randtools import random_percent
import random
from .star import Star
from xme.xmetools.jsontools import read_from_path, save_to_path
import math

class Planet(Celestial, CanDevelop):
    """行星类型"""
    def __init__(self, galaxy_location: tuple[int, int], location: tuple[int, int], serial_number, star: Star = None, planet_type: PlanetType = None, name: str = "", desc: str = "", is_known=False, buildings=[], faction_id: int = 0) -> None:
        Celestial.__init__(self, galaxy_location=galaxy_location, location=location, name=name, desc=desc, faction_id=faction_id)
        CanDevelop.__init__(self, buildings)
        # 是否被开发
        # 未知的行星不可被雷达 / 星图发现
        self.is_known = is_known
        # 行星需要有恒星
        # star = star
        self.star_uid = star.uid
        # 序号
        self.serial_number = serial_number
        # 行星类型
        self.planet_type = planet_type
        if not planet_type:
            self.gen_planet_type(star)
        if not self.name or not self.desc:
            self.gen_random_info(star)

    def calc_habitable_zone_ratio(self, range, star: Star) -> tuple[float, float]:
        return tuple([r * star.thermal_luminosity for r in range])

    def gen_planet_type(self, star):
        can_gen_types = []
        habitable_zone_distance = math.dist(star.location, self.location) - star.habitable_zone
        print(habitable_zone_distance, star.star_type)
        for r, planet_type in planet_HZproximity.items():
            r = self.calc_habitable_zone_ratio(r, star)
            # print(r)
            if habitable_zone_distance < r[0] and habitable_zone_distance < r[1]:
                continue
            # 谁见过黑洞旁边有类地行星的
            if star.star_type in [
                StarType.BLACKHOLE,
                StarType.NEUTRON_STAR,
                StarType.WHITE_DWARF,
                StarType.RED_SUPERGIANT,
                StarType.YELLOW_SUPERGIANT,
                StarType.RED_GIANT,
                StarType.BLUE_GIANT] and planet_type in [PlanetType.TERRESTRIAL, PlanetType.DRY, PlanetType.SEA, PlanetType.DESOLATE, PlanetType.VOLCANIC]:
                continue
            can_gen_types.append(planet_type)
        # print(star.name, can_gen_types)
        for planet_type, probability in planet_probabilities.items():
            self.planet_type = planet_type if random_percent(probability) else self.planet_type
        # 默认岩石星球
        if not self.planet_type:
            self.planet_type = PlanetType.ROCK if PlanetType.ROCK in can_gen_types else PlanetType.LAVA
        # self.planet_type = random.choice(can_gen_types)

    def gen_random_info(self, star):
        used_names: list = read_from_path("data/used_names.json")
        first = random.choice(["FE", "TS", "EF", "LI", "RST", "ET", "T", "ME"])
        suffix = random.choice(["D", "D", "D", "D" "C", "C", "C", "C", "C" "B", "B"])
        suffix = "A" if random_percent(10) else suffix
        suffix = "R" if random_percent(3) else suffix
        if self.faction.id in [4, 5, 7, 9]:
            suffix = suffix + "Z" if random_percent(50) else suffix
            suffix = suffix + "X" if random_percent(50) else suffix
        self.name = f"{star.name}-{first}{self.serial_number}{suffix}"
        used_names.append(self.name)
        save_to_path("data/used_names.json", used_names)
        self.desc = x if (x:=planet_type_desc[self.planet_type]) else self.planet_type.value

    def __dict__(self):
        return {
            "type": "Planet",
            "uid": self.uid,
            "name": self.name,
            "desc": self.desc,
            "galaxy_location": self.galaxy_location,
            "star": self.star_uid,
            "location": self.location,
            "faction": self.faction.id,
            "is_known": self.is_known,
            "serial_number": self.serial_number,
            "planet_type": self.planet_type.value,
            "buildings": self.buildings,
        }

    @staticmethod
    def load(celestial_dict):
        return Planet(
            name=celestial_dict["name"],
            desc=celestial_dict["desc"],
            galaxy_location=celestial_dict["galaxy_location"],
            location=tuple([x for x in celestial_dict["location"]]),
            faction_id=celestial_dict["faction"],
            is_known=celestial_dict["is_known"],
            serial_number=celestial_dict["serial_number"],
            planet_type=PlanetType(celestial_dict["planet_type"]),
            buildings=celestial_dict["buildings"]
        )