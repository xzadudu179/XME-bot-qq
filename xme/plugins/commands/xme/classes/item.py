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
    CAN_USE = "可使用"
    MATERIAL = "材料"
    ARMOR = "护甲"
    WEARABLE = "可穿戴"

class Item:
    """一般物品
    """
    def __init__(self, id: int, name: str, desc: str, rarity: Rarity, tags: list[Tag]=[]) -> None:
        self.id = id
        self.name = name
        self.desc = desc
        self.rarity =rarity
        self.tags = tags

    def use_tag(tag: Tag, errormsg):
        """标记函数为使用了标签
        """
        def decorator(func):
            @wraps(func)
            def wrapper(self, *args, **kwargs):
                if tag in self.tags:
                    result = func(self, *args, **kwargs)
                else:
                    result = errormsg
                return result
            return wrapper
        return decorator

    @use_tag(tag=Tag.WEAPON, errormsg=None)
    def attack():
        """攻击
        """
