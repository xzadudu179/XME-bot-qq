
from ..tools.map_tools import *
from .faction import Faction, FACTIONS
from xme.xmetools.xmefunctools import run_with_timeout
from .celestial.station import Station
from .celestial.planet import Planet
from .celestial import Celestial, planet_type_color, star_type_color, PlanetType
from .celestial.star import Star
from .celestial.ship import Ship
from .celestial.tools import load_celestial
from xme.xmetools import jsontools
from xme.xmetools.debugtools import debug_msg
from nonebot.log import logger
from xme.xmetools.randtools import random_percent
import random
random.seed()
from xme.xmetools.colortools import rgb_to_hex
from PIL import Image

# galaxy_initing = False

celestial_draw_sides = {
    Planet: 5,
    Star: 7,
    Ship: 4,
    Station: 3,
}

def get_galaxymap():
    try:
        return GalaxyMap()
    except:
        return False

def get_celestial_from_uid(uid, default=None):
    if not get_galaxymap():
        return default
    for v in GalaxyMap().starfields.values():
        for c in v.celestials.values():
            if c.uid == uid:
                return c
    print("无法通过uid找到星体")
    return default

def get_starfield_map(location, default=None):
    """通过位置获得星域地图

    Args:
        location (tuple[int, int]): 星域坐标
        default (Any, optional): 获取不到时的默认值. Defaults to None.

    Returns:
        StarfieldMap: 星域地图
    """
    location = tuple(location)
    # print(GalaxyMap().starfields)
    return GalaxyMap().starfields.get(location, default)

def init_starfields(percent, max_size):
        # global galaxy_initing
        # galaxy_initing = True
        xys = set()
        if percent > 1 or percent <= 0:
            raise ValueError(f"百分比不能小于0 或大于1：precent: {percent}")
        count = max_size[0] * max_size[1] * percent
        while len(xys) < count:
            x = random.randint(0, max_size[0])
            y = random.randint(0, max_size[1])
            xys.add((x, y))
        print(f"需要生成 {len(xys)} 个星域")
        fields = {index: Starfield(location=(x, y)) for index in xys}
        # galaxy_initing = False
        return fields

class GalaxyMap:
    """星系地图
    """
    def __init__(self, maxwidth=499, maxheight=499) -> None:
        self.max_size = (maxwidth, maxheight)
        # global galaxy_initing
        # if galaxy_initing:
        #     raise ValueError("Galaxy Initing")
        # POSSIBILITY = 0.6
        POSSIBILITY = 0.03
        if map:=jsontools.read_from_path("static/map/map.json"):
            self.max_size = tuple(map["max_size"])
            map = map["starfields"]
            starfields = {}
            for index, starfield in map.items():
                starfield = Starfield.load(starfield)
                starfields[tuple([int(i) for i in index.split(",")])] = starfield
            self.starfields = starfields
            print(self.max_size)
        # elif not galaxy_initing:
        else:
            print("正在生成地图...")
            jsontools.save_to_path("data/used_names.json", [])
            self.starfields = init_starfields(POSSIBILITY, self.max_size)
            self.load_map_from_image("static/img/map-1.png")
            self.save()
        # print(self.starfields)

    def __dict__(self):
        # print(self.starfields)
        return {
            "max_size": self.max_size,
            "starfields": {f"{index[0]},{index[1]}": m.__dict__() for index, m in self.starfields.items()}
        }

    def load_map_from_image(self, path):
        img = Image.open(path)
        img = img.resize(self.max_size, Image.Resampling.NEAREST)
        # img.show()
        for index in self.starfields.keys():
            try:
                pixel = img.getpixel(index)
            except IndexError:
                pixel = (0, 0, 0, 0)
            hex_color = rgb_to_hex(pixel[:3])
            if hex_color == "#000000":
                continue
            for faction in FACTIONS.values():
                # print(hex_color, faction.color)
                if hex_color.upper() != faction.color.upper():
                    continue
                # print("是阵营颜色")
                self.starfields[index] = Starfield(
                    location=index,
                    faction=faction,
                )

    def save(self):
        # jsontools.save_to_path("data/init_data/galaxymap.json")
        jsontools.save_to_path("static/map/map.json", self.__dict__())

    # def create_starfield_block(self, position: tuple[int, int], maxwidth: int = 500, maxheight: int = 500):
    #     """创建星域地图块

    #     Args:
    #         position (tuple[int, int]): 星域块位置
    #         maxwidth (int, optional): 星域块内坐标系最大宽度. Defaults to 500.
    #         maxheight (int, optional): 星域块内坐标系最大高度. Defaults to 500.
    #     """
    #     if position[0] > self.max_size[0] or position[1] > self.max_size[1] or position[0] < 0 or position[1] < 0:
    #         raise ValueError("星域地图块坐标超过范围")
    #     self.starfields[position] = StarfieldMap(position, self, maxwidth, maxheight)

    def draw_galaxy_map(self, img_zoom=2, center=(0, 0), zoom_fac=1, padding=100, background_color="black", line_width=1, grid_color='#102735') -> Image.Image:
        # 图片大小
        # img_zoom = 2
        map_width, map_height = self.max_size[0] + 1, self.max_size[1] + 1

        zoom_width, zoom_height = map_width // zoom_fac // 2, map_height // zoom_fac // 2
        # append_ = (((-center[0] + zoom_width) * zoom_fac), (-center[1] + zoom_height) * zoom_fac)

        # 计算图像宽高
        width, height = int(zoom_width * 2 * zoom_fac + padding * 2) * img_zoom, int(zoom_height * 2 * zoom_fac + padding * 2) * img_zoom
        print(width, height)

        # 创建画布
        img = Image.new('RGB', (width, height), background_color)
        draw = ImageDraw.Draw(img)

        # 背景
        # 绘制随机线条
        random_node_lines(draw, 35, (2, 6), (10, 30), int(line_width * zoom_fac) * img_zoom, width, height, max_length=int(50 * zoom_fac * img_zoom), node_size=int(1 * zoom_fac))
        # 绘制网格
        write_grid(draw, int(15 * zoom_fac * img_zoom), width, height, grid_color, int(1 * zoom_fac * img_zoom))

        # for i, (point, starfield) in enumerate(self.starfields.items()):
        append_ = (((-center[0] + zoom_width) * zoom_fac), (-center[1] + zoom_height) * zoom_fac)
        for point, starfield in self.starfields.items():
            # print(starfield)
            # print("point", point)
            color = starfield.calc_faction().color
            point_to_draw = (int(point[0] * zoom_fac + padding + append_[0]) * img_zoom, int(point[1] * zoom_fac + padding + append_[1]) * img_zoom)
            if point[0] == 42 and point[1] == 48:
                print("4248", point_to_draw, zoom_fac, img_zoom, padding, append_)
            draw_point(draw, zoom_fac, point_to_draw, color)

        # mark_point(draw, (int(0 * zoom_fac + padding + append_[0]) * img_zoom, int(0 * zoom_fac + padding + append_[1]) * img_zoom),(0, 0), 0, 'cyan', int(line_width * 1), int(10 * 1),'测试坐标', int(12 * 1))
        # 保存图片
        img.save('data/images/temp/galaxy_map.png')
        return img

class Starfield:
    """星域地图
    """
    def __init__(self, faction: Faction = FACTIONS[0], celestials = []) -> None:
        """创建星域地图

        Args:
            faction (Faction, None): 所属阵营. Defaults to factions[0].
            maxwidth (int, optional): 坐标最大宽度. Defaults to 500.
            maxheight (int, optional): 坐标最大高度. Defaults to 500.
        """
        # self.max_size = (maxwidth, maxheight)
        self.celestials: list[Celestial] = celestials
        # self.location = location

        if not faction:
            faction = self.calc_faction()
        if not celestials:
            print("正在生成星域...")
            self.init_celestials(min_distance=20, count=1, celestial_type=Star, faction=faction)
            self.init_celestials(min_distance=30, count=random.randint(1, 5) if random_percent(65) else random.randint(5, 14), celestial_type=Planet, faction=faction, target_celestial_type=Star)
            # self.delete_stone()
            # self.init_celestials(min_distance=50, count=random.randint(1, 3) if random_percent(65) else random.randint(3, 5), celestial_type=Planet, faction=faction, target_celestial_type=Star)
            # if faction.id != 0:
                # self.init_celestials(min_distance=10, count=max(0, random.randint(-7, 7)), celestial_type=Station, faction=faction, target_celestial_type=Planet)
                # self.init_celestials(min_distance=10, count=max(0, random.randint(-7, 3)), celestial_type=Ship, faction=faction)


    def init_celestials(self, count, celestial_type, faction):
        """生成天体

        Args:
            min_distance (int): 天体之间最小距离
            count (int): 天体数量
            celestial_type (type): 天体类型
            faction (Faction): 所属阵营
        """
        ATTEMPTS = 50000
        points = []
        # def is_valid(x, y):
        #     """检查距离是否够大"""
        #     if self.celestials.get((x, y)):
        #         return False
        #     for point in self.celestials.keys():
        #         # print(point)
        #         if (x, y) == point:
        #             return False
        #     for px, py in points:
        #         distance = math.dist((x, y), (px, py))
        #         if distance < min_distance or max_distance > min_distance and distance > max_distance:
        #             return False
        #     if target_celestial_type is not None:
        #         for target in [p for p, t in self.celestials.items() if t == target_celestial_type]:
        #             target_distance = math.dist(target, (x, y))
        #             if target_distance < min_distance or max_distance > min_distance and distance > max_distance:
        #                 return False
        #     elif target_position is not None:
        #         distance = math.dist((x, y), (target_position[0], target_position[1]))
        #         if distance > 10:
        #             return False
        #     return True
        # # 生成点
        # i = 0
        # while len(points) < count and i < ATTEMPTS:
        #     x, y = random.randint(0, self.max_size[0] - 1), random.randint(0, self.max_size[1] - 1)
        #     if is_valid(x, y):
        #         points.append((x, y))
        #     i += 1
        result = []
        planet_num = 1
        for cele in range(count):
            if celestial_type == Planet:
                celestial = Planet(
                    name="",
                    desc="",
                    galaxy_location=self.location,
                    star=random.choice([s for s in self.celestials.values() if isinstance(s, Star)]),
                    serial_number=planet_num,
                    faction_id=faction.id,
                    is_known=False if faction.id == 0 else True
                )
                planet_num += 1
                result.append(celestial)
            else:
                celestial = celestial_type(name="", desc="", galaxy_location=self.location, faction_id=faction.id)
        # for point in points:
        #     # print("正在生成天体...")
        #     if celestial_type == Planet:
        #         celestial = Planet(
        #             name="",
        #             desc="",
        #             galaxy_location=self.location,
        #             location=point,
        #             star=random.choice([s for s in self.celestials.values() if isinstance(s, Star)]),
        #             serial_number=planet_num,
        #             faction_id=faction.id,
        #             is_known=False if faction.id == 0 else True
        #         )
        #         planet_num += 1
        #     else:
        #         celestial = celestial_type(name="", desc="", galaxy_location=self.location, location=point, faction_id=faction.id)
        self.celestials = self.celestials + result


    def calc_faction(self) -> Faction:
        # 通过大型星体所属阵营数量等来判断属于哪个阵营
        has_factions = {}
        for c in self.celestials.values():
            if c.faction.id != 0:
                has_factions[c.faction.id] = FACTIONS.get(c.faction, 0) + 1
        if not has_factions:
            return FACTIONS[0]
        # print(has_factions, max(has_factions, key=lambda f: has_factions[f]))
        return FACTIONS[max(has_factions, key=lambda f: has_factions[f])]

    def __dict__(self):
        # print({f"{k[0]},{k[1]}": v.__dict__() for k, v in self.celestials.items()})
        return {
            # "max_size": self.max_size,
            "celestials": {f"{k[0]},{k[1]}": v.__dict__() for k, v in self.celestials.items()},
            "location": self.location
        }

    @staticmethod
    def load(map_json: dict):
        # print(map_json)
        return Starfield(
            # maxwidth=map_json["max_size"][0],
            # maxheight=map_json["max_size"][1],
            # location=map_json["location"],
            celestials={tuple([int(x) for x in k.split(",")]): load_celestial(v) for k, v in map_json["celestials"].items()}
        )

    def get_celestial(self, location, default=None):
        return self.celestials.get(location, default)

    # def draw_starfield_map(self, img_zoom=2, center=(0, 0), zoom_fac=1, ui_zoom_fac=1, padding=100, background_color="black", line_width=1, grid_color='#102735', font_size: int = 12) -> Image.Image:
        # 图片大小
        # img_zoom = 2
        map_width, map_height = self.max_size[0] + 1, self.max_size[1] + 1

        zoom_width, zoom_height = map_width // zoom_fac // 2, map_height // zoom_fac // 2
        append_ = (((-center[0] + zoom_width) * zoom_fac), (-center[1] + zoom_height) * zoom_fac)

        # 计算图像宽高
        width, height = int(zoom_width * 2 * zoom_fac + padding * 2) * img_zoom, int(zoom_height * 2 * zoom_fac + padding * 2) * img_zoom
        # print(width, height)

        # 创建画布
        img = Image.new('RGB', (width, height), background_color)
        draw = ImageDraw.Draw(img)

        # 背景
        # 绘制随机线条
        random_node_lines(draw, 50, (2, 6), (10, 30), int(line_width * zoom_fac) * img_zoom, width * (width // (zoom_width * 2)), height * (height // (zoom_height * 2)), max_length=int(50 * zoom_fac * img_zoom), node_size=int(1 * zoom_fac))
        # 绘制网格
        write_grid(draw, int(15 * zoom_fac * img_zoom), width, height, grid_color, int(1 * zoom_fac * img_zoom))

        # 前景

        for point, celestial in self.celestials.items():
            side = celestial_draw_sides[type(celestial)]
            color = celestial.faction.color
            point_to_draw = (int(point[0] * zoom_fac + padding + append_[0]) * img_zoom, int(point[1] * zoom_fac + padding + append_[1]) * img_zoom)
            prefix = celestial.faction.name
            if isinstance(celestial, Planet):
                color = planet_type_color[celestial.planet_type]
                prefix = celestial.planet_type.value
            elif isinstance(celestial, Star):
                color = star_type_color[celestial.star_type]
                prefix = celestial.star_type.value
            elif isinstance(celestial, Ship):
                ...
            mark_point(draw, point_to_draw, point, side, color, int(line_width * ui_zoom_fac), int(10 * ui_zoom_fac), f'[{prefix}] {celestial.name}', int(font_size * ui_zoom_fac))

        # # 绘制圆加十字
        # mark_point(draw, points[0],regular_points[0], 0, 'cyan', int(line_width * ui_zoom_fac), int(10 * ui_zoom_fac),'xzadudu179 (你)', int(font_size * ui_zoom_fac))

        # 保存图片
        img.save('data/images/temp/starfield_map.png')
        return img