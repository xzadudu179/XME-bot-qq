# 背包里的一格
from .item import item_table, Item
import copy

class ItemBlock:
    def __init__(self, item: Item=None, count: int=0) -> None:
        self.item = item
        if self.item != None and count > self.item.maxcount:
            raise ValueError("物品堆叠过多")
        self.itemcount = count

    def add_item(self, item: Item, count) -> tuple[bool, int]:
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
        if not self.item:
            self.item = item
        elif self.item != item:
            # 不同类物品不允许添加
            return (False, 0)
        new_count = self.itemcount + count
        if new_count > self.item.maxcount:
            # new_count = self.item.maxcount
            self.itemcount = self.item.maxcount
            return (True, new_count - self.item.maxcount)
        self.itemcount = new_count
        return (True, 0)

    def del_item(self, count) -> tuple[bool, int]:
        """尝试删除物品

        Args:
            count (int): 物品数量

        Returns:
            bool: 是否成功删除
        """
        if self.item == None:
            return (False, count)
        item_left = self.itemcount - count
        if item_left <= 0:
            # return False
            self.item = None
        else:
            self.itemcount = item_left
            return (True, 0)
        # 剩余物品
        last_item = abs(item_left)
        self.itemcount = 0
        return (True, last_item)

    def __str__(self) -> str:
        return f"{self.item if self.item else -1},{self.itemcount}"

    # def __getstate__(self):
    #     return str(self)

    # def __setstate__(self, s):
    #     item_name = s.split(",")[0]
    #     item = item_table.get(item_name, None)
    #     amount = int(s.split(",")[1])

    #     # 如果 item 是可变对象，确保它不会被共享
    #     if item is not None:
    #         self.__init__(copy.deepcopy(item), amount)
    #     else:
    #         self.__init__(None, amount)