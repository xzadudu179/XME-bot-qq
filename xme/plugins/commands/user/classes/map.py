from .faction import Faction
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
        return {index: StarfieldMap(None) for index in xys}


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

    def __dict__(self):
        return {
            "max_size": self.max_size,
            "celestials": self.celestials
        }