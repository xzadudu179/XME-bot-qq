from .database import Xme_database
from .faction import Faction

class GalaxyMap:
    def __init__(self, database, maxwidth=1000, maxheight=1000) -> None:
        self.database = database
        self.max_size = (maxwidth, maxheight)
        self.starfields = {
        }

    def create_starfield_block(self, position: tuple[int, int], maxwidth: int=500, maxheight: int=500):
        """创建星域地图块

        Args:
            position (tuple[int, int]): 星域块位置
            maxwidth (int, optional): 星域块内坐标系最大宽度. Defaults to 500.
            maxheight (int, optional): 星域块内坐标系最大高度. Defaults to 500.
        """
        if position[0] > self.max_size[0] or position[1] > self.max_size[1] or position[0] < 0 or position[1] < 0:
            raise ValueError("星域地图块坐标超过范围")
        self.starfields[position] = StarfieldMap(position, self, maxwidth, maxheight)

    def draw_map(self):
        # 绘制地图
        pass

class StarfieldMap:
    """星域地图
    """
    def __init__(self, map_position: tuple[int, int], galaxymap: GalaxyMap, faction: Faction, maxwidth: int=500, maxheight: int=500) -> None:
        """创建星域地图

        Args:
            map_position (tuple[int, int]): 地图所在坐标
            galaxymap (GalaxyMap): 银河地图
            faction (Faction): 所属阵营
            maxwidth (int, optional): 坐标最大宽度. Defaults to 500.
            maxheight (int, optional): 坐标最大高度. Defaults to 500.
        """
        self.position = map_position
        self.faction = faction
        self.starmap = galaxymap
        self.max_size = (maxwidth, maxheight)