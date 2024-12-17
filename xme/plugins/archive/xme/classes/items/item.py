from enum import Enum
from functools import wraps

class Rarity(Enum):
    """稀有度"""
    COMMON = "常见"
    UNCOMMON = "少见"
    RARE = "稀有"
    EPIC = "罕见"
    LEGEND = "传奇"
    MYSTIC = "神秘"

class Tag(Enum):
    """物品标签"""
    WEAPON = "武器"
    FOOD = "食物"
    DRINK = "饮料"
    SPECIAL = "特殊"
    SALEABLE = "可出售"
    MATERIAL = "材料"
    ARMOR = "护甲"
    WEARABLE = "可穿戴"


class Item:
    """一般物品
    """
    def has_tag(self, tag: Tag):
        return tag in self.tags

    def __init__(self, id: int, name: str, desc: str, rarity: Rarity, tags: list[Tag]=[], maxcount: int=1) -> None:
        """创建一个物品

        Args:
            id (int): 物品唯一 ID
            name (str): 物品名
            desc (str): 物品介绍
            rarity (Rarity): 物品稀有度
            tags (list[Tag], optional): 物品所包含标签. Defaults to [].
            maxcount (int, optional): 物品最大堆叠数量. Defaults to 1.
        """
        self.id = id
        self.name = name
        self.desc = desc
        self.rarity =rarity
        self.tags = tags
        self.maxcount = maxcount
        self.price = 0
        self.actions = {
            # 基本方法
        }

    def __getstate__(self):
        return self.id

    def __setstate__(self, id):
        self.get_item(id)

    def __str__(self) -> str:
        return str(self.id)

    def get_item(id):
        return item_table[id]

    def info(self) -> str:
        price = '\n基准价格: ' + str(self.price) if self.has_tag(Tag.SALEABLE) else ''
        return f"""
[{self.rarity.value}] {self.name}
标签：{', '.join([tag.value for tag in self.tags])}{price}
-------------------------
{self.desc}
-------------------------
最大堆叠数量: {self.maxcount}
    """.strip()

    def set_action(self, name: str, action):
        self.actions[name] = action

    def perform_action(self, action_name, *args):
        """使用物品自定方法

        Args:
            action_name (str): 物品方法名
        """
        if action_name in self.actions and self.actions[action_name]:
            return (True, self.actions[action_name](self, args))
        else:
            return (False)


item_table = {
}

def init_item_table():
    global item_table
    items: list[Item] = []
    # 物品列表在这定义
    # 几何挂件
    geo_pendant = Item(0, "几何挂件", "HIUN 中常见的小挂件，可以散发清香，几何体可以随意编辑样式。", Rarity.COMMON, [Tag.SALEABLE], 20)
    geo_pendant.price = 10
    def get_pendant_sell():
        return geo_pendant.price
    geo_pendant.set_action('sell', get_pendant_sell)
    items.append(geo_pendant)

    for item in items:
        item_table[str(item.id)] = item

    print(f"物品表初始化：{item_table}")

init_item_table()
# item = item_table['0']
# print(item.info())