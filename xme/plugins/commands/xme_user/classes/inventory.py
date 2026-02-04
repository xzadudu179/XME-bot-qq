from .inv_item import InvItem
from .item import Item
from character import get_message

class Inventory:
    """物品栏类
    """
    def __init__(self, length=20, inv_list: list[dict] | None = None):
        self.inv_items: list[InvItem] = []
        if inv_list is not None:
            for item in inv_list:
                self.inv_items.append(InvItem.get_invitem(item))
            return
        for _ in range(length):
            self.inv_items.append(InvItem())

    def __list__(self):
        self.sort_items()
        items = []
        for inv_item in self.inv_items:
            items.append(inv_item.__dict__())
        return items

    def get_space_left(self) -> str:
        i = 0
        for inv_item in self.inv_items:
            if not inv_item.recorded_item:
                continue
            i += 1
        return f"{i} / {len(self.inv_items)}"

    def __str__(self):
        """输出物品栏内容
        """
        self.sort_items()
        result = ""
        i = 0
        for inv_item in self.inv_items:
            if not inv_item.recorded_item:
                continue
            result += '\n' + get_message("user", "inventory_item", num=i + 1, name=inv_item.recorded_item.name, count=inv_item.count)
            i += 1
        if i == 0:
            return get_message("user", "empty_inventory")
        result = get_message("user", "inventory_prefix", space=self.get_space_left()) + result
        return result


    @staticmethod
    def get_inventory(inv_list):
        return Inventory(inv_list=inv_list)

    def sort_items(self):
        self.inv_items = sorted(self.inv_items, key=lambda x: x.recorded_item.id if x.recorded_item is not None else -1, reverse=True)

    def find_item(self, index):
        """根据索引找到物品

        Args:
            index (int): 索引

        Returns:
            InvItem | None: 物品栏格子
        """
        self.sort_items()
        return self.inv_items[index]

    def scaling(self, length):
        """扩容物品栏

        Args:
            length (int): 长度
        """
        for _ in range(length):
            self.inv_items.append(InvItem())
        self.sort_items()

    def count_item(self, item: Item):
        """获取某个物品的数量

        Args:
            item (Item): 物品

        Returns:
            int: 得到的数量
        """
        result = 0
        for inv_item in self.inv_items:
            if inv_item.recorded_item and inv_item.recorded_item.id != item.id:
                continue
            result += inv_item.count
        return result

    def reduce_item(self, id, count) -> bool:
        """尝试减少物品

        Args:
            id (int): 物品 id
            count (int): 移除的数量

        Raises:
            ValueError: id 指向的物品不存在
            Exception: 未知错误

        Returns:
            bool: 是否移除成功
        """
        self.sort_items()
        if count < 0:
            return False
        item = Item.get_item(id)
        if item is None:
            raise ValueError(f"id 为 {id} 的物品不存在")
        total_count = 0
        for inv_item in self.inv_items:
            if inv_item.recorded_item != item:
                continue
            total_count += inv_item.count
        if total_count < count:
            return False
        for inv_item in self.inv_items:
            if inv_item.recorded_item != item:
                continue
            reduce_count = inv_item.count
            if reduce_count > count:
                reduce_count = count
            if not inv_item.try_reduce_item(id, reduce_count):
                continue
            count -= reduce_count
            if count <= 0:
                return True
        raise Exception("移除物品时出错")

    def add_item(self, id, count) -> bool:
        """尝试添加指定数量的物品

        Args:
            id (int): 物品 id
            count (int): 添加的数量

        Raises:
            ValueError: id 指向的物品不存在
            Exception: 未知错误

        Returns:
            bool: 是否添加成功
        """
        if count < 0:
            return False
        if Item.get_item(id) is None:
            raise ValueError(f"id 为 {id} 的物品不存在")
        # 先判断能不能添加
        total_space = 0
        for inv_item in self.inv_items:
            total_space += inv_item.get_remaining_space(id)
        if total_space < count:
            return False
        # 添加
        for inv_item in self.inv_items:
            add_count = inv_item.get_remaining_space(id)
            if add_count <= 0:
                continue
            elif add_count > count:
                add_count = count
            if not inv_item.try_add_item(id, add_count):
                continue
            count -= add_count
            if count <= 0:
                self.sort_items()
                return True
        raise Exception("添加物品时出错")