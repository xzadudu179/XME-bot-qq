# 背包里的一格
from .item import item_table, Item

class ItemBlock:
    def __init__(self, itemid: int=None, count: int=0) -> None:
        self.itemid = itemid
        if self.itemid != None and count > Item.get_item(self.itemid).maxcount:
            raise ValueError("物品堆叠过多")
        self.itemcount = count
        print("itemblock初始化")

    def add_item(self, id: int, count) -> tuple[bool, int]:
        """尝试添加物品

        Args:
            item (Item): 物品类型
            count (int): 物品数量

        Returns:
            bool: 是否成功添加
        """
        # 如果没有就添加第一个物品
        if count < 0:
            return (False, 0)
        if item_table.get(self.itemid, None) == None:
            self.itemid = id
        elif self.itemid != id:
            # 不同类物品不允许添加
            return (False, 0)
        new_count = self.itemcount + count
        if new_count > Item.get_item(self.itemid).maxcount:
            # new_count = self.item.maxcount
            self.itemcount = Item.get_item(self.itemid).maxcount
            return (True, new_count - Item.get_item(self.itemid).maxcount)
        self.itemcount = new_count
        return (True, 0)

    def del_item(self, count) -> tuple[bool, int]:
        """尝试删除物品

        Args:
            count (int): 物品数量

        Returns:
            bool: 是否成功删除
        """
        if self.itemid == None:
            return (False, count)
        item_left = self.itemcount - count
        if item_left <= 0:
            # return False
            self.itemid = None
        else:
            self.itemcount = item_left
            return (True, 0)
        # 剩余物品
        last_item = abs(item_left)
        self.itemcount = 0
        return (True, last_item)

    def __str__(self) -> str:
        return f"{self.itemid if self.itemid else -1},{self.itemcount}"