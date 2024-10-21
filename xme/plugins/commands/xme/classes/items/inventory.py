from .item import Tag, Item, item_table, init_item_table
from .itemblock import ItemBlock

class Inventory:
    """物品栏类
    """
    def __init__(self, length: int, itemblocks: list[ItemBlock]=None) -> None:
        if length <= 0:
            raise ValueError("长度必须大于 0")
        if not itemblocks:
            self.blocks: list[ItemBlock] = []
            for _ in range(length):
                self.blocks.append(ItemBlock())
        elif len(itemblocks) < length:
            self.blocks: list[ItemBlock] = itemblocks
            for _ in range(length - len(itemblocks)):
                self.blocks.append(ItemBlock())
        else:
            self.blocks = itemblocks
        self.length = length

    def get_itemblocks(itemblocks_str: str | None):
        itemblocks = []
        if not itemblocks_str:
            for _ in range(20):
                itemblocks.append(ItemBlock())
                return itemblocks
        for itemblock_str in itemblocks_str.split("|"):
            b = itemblock_str.split(",")
            if b[0] == '-1':
                itemblocks.append(ItemBlock())
            else:
                itemblocks.append(ItemBlock(item_table[b[0]], int(b[1])))
        return itemblocks

    def get_space(self) -> int:
        """获取物品栏所占用的空间

        Returns:
            int: 所占用的空间
        """
        space = 0
        for block in self.blocks:
            if not block.item: continue
            space += 1
        return space

    def get_block_info(self, index: int) -> tuple[bool, tuple[Item, int]|str]:
        """得到物品栏内物品信息

        Args:
            index (int): 物品索引

        Returns:
            tuple[bool, tuple[Item, int]|str]: 返回是否成功以及物品信息和物品数量
        """
        try:
            block = self.blocks[index]
            if not block.item:
                return (False, "没有物品")
            return (True, (block.item, block.itemcount))
        except IndexError:
            return (False, "超出长度上限")

    def sell(self, item: Item, count) -> tuple[bool, str | int]:
        """出售物品

        Args:
            item (Item): 物品类型
            count (int): 份数

        Returns:
            tuple[bool, str| int]: 出售是否成功以及消息或价格
        """
        if not item.has_tag(Tag.SALEABLE):
            return (False, "物品不可出售")
        if self.del_item(item, count):
            return (True, count * item.price)
        return (False, "物品数量不足")

    def use(self, item: Item) -> tuple:
        """调用物品的使用方法来使用物品

        Args:
            item (Item): 物品类型

        Returns:
            tuple: 状态 (bool, 状态字符串或者函数返回)
        """
        if x:=item.actions.get('use', None):
            action = x
        if not self.del_item(item, 1): return (False, "物品数量不足")
        return (True, action())

    def del_item(self, item: Item, count: int) -> bool:
        """尝试删除物品

        Args:
            item (Item): 物品类型
            count (int): 删除数量

        Returns:
            bool: 是否删除成功
        """
        for block in self.blocks:
            if block.item != item: continue
            if block.del_item(count): return True
        return False

    def add_item(self, item: Item, count: int) -> bool:
        """尝试添加物品

        Args:
            item (Item): 物品类型
            count (int): 添加的数量

        Returns:
            bool: 是否成功
        """
        curr_count = count
        for block in self.blocks:
            (stats, curr_count) = block.add_item(item, curr_count)
            print(curr_count, curr_count)
            if stats and curr_count <= 0:
                print("fanhuie")
                return True
        return False

    def __str__(self) -> str:
        return '|'.join([str(block) for block in self.blocks])

if __name__ == "__main__":
    inv = Inventory(20, Inventory.get_itemblocks('0,12|-1,0|-1,0|-1,0|-1,0|-1,0|-1,0|-1,0|-1,0|-1,0'))
    print(inv)
    print(inv.get_block_info(0))