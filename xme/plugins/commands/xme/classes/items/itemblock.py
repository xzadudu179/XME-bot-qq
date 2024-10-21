# 背包里的一格
from .item import item_table, Item

class ItemBlock:
    def __init__(self, item: Item|None=None, count: int=0) -> None:
        self.item: Item = item
        if self.item and count > self.item.maxcount:
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
        if not self.item:
            return (False, 0)
        new_count = self.itemcount - count
        if new_count <= 0:
            # return False
            self.item = None
        last_item = abs(new_count)
        new_count = 0
        self.itemcount = new_count
        return (True, last_item)

    def __str__(self) -> str:
        return f"{self.item if self.item else -1},{self.itemcount}"