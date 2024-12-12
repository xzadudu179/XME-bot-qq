from .item import Item
from typing import Any

class InvItem:
    """物品栏单位格
    """
    def __init__(self, recorded_item: Item | None = None, count: int = 0) -> None:
        self.recorded_item: Item | None = recorded_item
        self.count: int = count
        pass

    def get_remaining_space(self, id):
        """获得当前物品栏格的剩余空间

        Args:
            id (int): 指定的物品类型

        Returns:
            int: 剩余空间格数
        """
        item = Item.get_item(id)
        if item is None:
            raise ValueError("id 不可为空")
        if self.recorded_item is not None and self.recorded_item != item:
            return 0
        return item.maxcount - self.count

    def __dict__(self):
        return {
            "id": self.recorded_item.id if self.recorded_item is not None else -1,
            "count": self.count
        }

    @staticmethod
    def get_invitem(d: dict):
        if d['id'] == -1 and d['count'] != 0:
            raise ValueError("空物品栏不能指定物品数量")
        item = Item.get_item(d['id'])
        return InvItem(item, d['count'])

    def try_add_item(self, id, count=1) -> bool:
        """尝试添加物品

        Args:
            count (int): 需要增加的数量. Defaults to 1.
            id (int): 物品 id

        Returns:
            bool: 是否添加成功
        """
        if count <= 0:
            return False
        item = Item.get_item(id)
        if item is None:
            return False
        if not self.recorded_item:
            self.recorded_item = item
            self.count = 0
        if self.count < 0:
            self.count = 0
        if self.count + count > self.recorded_item.maxcount:
            return False
        self.count += count
        return True

    def drop_item(self, count, ignore_tags=False) -> bool:
        """丢弃物品

        Args:
            count (int): 需要丢弃的物品数量

        Returns:
            bool: 是否丢弃成功
        """
        if self.recorded_item is None:
            return False
        return self.try_reduce_item(count=count)


    async def try_use_item(self, action, remove_after_use: bool, id: int | None = None, *args, **kwargs) -> tuple[bool, Any]:
        """尝试使用物品

        Args:
            action (str): 物品方法名
            remove_after_use (bool): 是否在用完物品后移除该物品
            id (int, optional): 物品 id. Defaults to None.

        Returns:
            tuple[bool, ...]: 是否使用成功，以及物品返回的结果
        """
        if not self.recorded_item:
            return (False, None)
        id = id if id is not None else self.recorded_item.id
        state, result = await self.recorded_item.call_action(action, *args, **kwargs)
        if state and remove_after_use:
            state = self.try_reduce_item(id)
        return (state, result)

    def try_sell_item(self, count=1, id=None) -> int | bool:
        """尝试出售物品

        Args:
            count (int, optional): 数量. Defaults to 1.
            id (int, optional): 物品 id. Defaults to None.

        Returns:
            int | bool: 出售的总价，或 False
        """
        if not self.recorded_item:
            return False
        id = id if id is not None else self.recorded_item.id
        item = Item.get_item(id)
        if self.recorded_item is not None and self.recorded_item != item:
            return False
        if not item.can_sell():
            return False
        if self.try_reduce_item(id, count):
            return item.price * count
        return False


    def try_reduce_item(self, id=None, count=1) -> bool:
        """尝试减少物品，若指定 id 则会判断记录的物品 id 是否一致

        Args:
            count (int): 需要移除的数量. Defaults to 1.
            id (int, optional): 指定的物品 id. Defaults to None.

        Returns:
            bool: 是否减少成功
        """
        if count <= 0:
            return False
        if not self.recorded_item:
            return False
        id = id if id is not None else self.recorded_item.id
        if self.count - count < 0:
            return False
        elif self.count - count == 0:
            # 如果没东西了就不登记这个物品了
            self.recorded_item = None
        self.count -= count
        return True