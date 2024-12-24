from .faction import Faction
from ..tools.map_tools import *
from xme.xmetools import json_tools
import random
from nonebot import get_bot
# from .faction import Faction
class GalaxyMap:
    def __init__(self, maxwidth=500, maxheight=500) -> None:
        self.max_size = (maxwidth, maxheight)
        self.starfields = self.init_starfields(0.01)
        # print(self.starfields)

    def init_starfields(self, percent):
        xys = set()
        if percent > 1 or percent <= 0:
            raise ValueError(f"百分比不能小于0 或大于1：precent: {percent}")
        count = self.max_size[0] * self.max_size[1] * percent
        while len(xys) < count:
            x = random.randint(0, self.max_size[0])
            y = random.randint(0, self.max_size[1])
            xys.add((x, y))
        return {index: StarfieldMap() for index in xys}

    def __dict__(self):
        # print(self.starfields)
        return {
            "max_size": self.max_size,
            "starfields": {index: m.__dict__() for index, m in self.starfields.items()}
        }

    def save(self):
        json_tools.save_to_path("data/init_data/galaxymap.json")

    def create_starfield_block(self, position: tuple[int, int], maxwidth: int = 500, maxheight: int = 500):
        """创建星域地图块

        Args:
            position (tuple[int, int]): 星域块位置
            maxwidth (int, optional): 星域块内坐标系最大宽度. Defaults to 500.
            maxheight (int, optional): 星域块内坐标系最大高度. Defaults to 500.
        """
        if position[0] > self.max_size[0] or position[1] > self.max_size[1] or position[0] < 0 or position[1] < 0:
            raise ValueError("星域地图块坐标超过范围")
        self.starfields[position] = StarfieldMap(position, self, maxwidth, maxheight)

    def draw_galaxy_map(self, center=(0, 0), zoom_fac=1, ui_zoom_fac=1, padding=100, background_color="black", line_width=1, grid_color='#102735') -> Image.Image:
        # 图片大小
        img_zoom = 2
        map_width, map_height = self.max_size

        zoom_width, zoom_height = map_width // zoom_fac // 2, map_height // zoom_fac // 2
        append = (((-center[0] + zoom_width) * zoom_fac), (-center[1] + zoom_height) * zoom_fac)

        # 计算图像宽高
        width, height = int(zoom_width * 2 * zoom_fac + padding * 2) * img_zoom, int(zoom_height * 2 * zoom_fac + padding * 2) * img_zoom
        print(width, height)

        # 创建画布
        img = Image.new('RGB', (width, height), background_color)
        draw = ImageDraw.Draw(img)

        # 背景
        # 绘制随机线条
        random_node_lines(draw, 50, (2, 6), (10, 30), int(line_width * zoom_fac) * img_zoom, width * (width // (zoom_width * 2)), height * (height // (zoom_height * 2)), max_length=int(50 * zoom_fac * img_zoom), node_size=int(1 * zoom_fac))
        # 绘制网格
        write_grid(draw, int(15 * zoom_fac * img_zoom), width, height, grid_color, int(1 * zoom_fac * img_zoom))

        # for i, (point, starfield) in enumerate(self.starfields.items()):
        for point, starfield in self.starfields.items():
            color = "#FFEE55" # TODO 计算颜色，颜色跟种族和信号强度有关
            draw_point(draw, zoom_fac * img_zoom, point, (width, height), color)
        # 保存图片
        img.save('data/images/temp/chart.png')
        return img

class StarfieldMap:
    """星域地图
    """
    def __init__(self, maxwidth: int = 500, maxheight: int = 500) -> None:
        """创建星域地图

        Args:
            faction (Faction, None): 所属阵营
            maxwidth (int, optional): 坐标最大宽度. Defaults to 500.
            maxheight (int, optional): 坐标最大高度. Defaults to 500.
        """
        self.max_size = (maxwidth, maxheight)
        self.celestials = {}

    def calc_color(self):
        # 通过大型星体所属阵营数量等来判断属于哪个阵营
        ...

    def __dict__(self):
        return {
            "max_size": self.max_size,
            "celestials": self.celestials
        }