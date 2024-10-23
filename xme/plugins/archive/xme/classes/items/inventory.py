from .item import Tag, Item, item_table, init_item_table
from .itemblock import ItemBlock
from ..fixed_list import FixedList

class Inventory:
    """物品栏类
    """
    def __init__(self, length: int, itemblocks: list=None) -> None:
        if length <= 0:
            raise ValueError("长度必须大于 0")
        if not itemblocks:
            self.blocks: FixedList = FixedList(length)
            # for _ in range(length):
            #     self.blocks.append(ItemBlock())
        else:
            self.blocks = FixedList(length, itemblocks.getlist())
        self.blocks.fillwith(ItemBlock())
        self.length = length

    def find_item_by_index(self, index: int) -> Item:
        try:
            return self.blocks[index].item
        except:
            return None

    def get_itemblocks(itemblocks_str: str | None, length: int=20):
        """从字符串获取物品栏到列表

        Args:
            itemblocks_str (str | None): 物品栏字符
            length (int, optional): 列表长度. Defaults to 20.

        Returns:
            FixedList: 物品栏列表
        """
        itemblocks = FixedList(length)
        if not itemblocks_str:
            for _ in range(length):
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

    # def drop_item(self, index: int, count: int) -> tuple[bool, int]:
    #     """尝试丢弃物品

    #     Args:
    #         index (int): 物品栏索引
    #         count (int): 数量

    #     Returns:
    #         bool: 是否丢弃成功
    #     """
    #     return self.del_item(self.blocks[index], count)

    def del_item(self, item: Item, count: int) -> tuple[bool, int]:
        """尝试删除物品

        Args:
            item (Item): 物品类型
            count (int): 删除数量

        Returns:
            bool: 是否删除成功
        """
        if count <= 0:
            return (False, -1)
        curr_count = count
        for block in reversed(self.blocks):
            # print(f"还剩 {curr_count} 个物品")
            if block.item != item: continue
            (stats, curr_count) = block.del_item(curr_count)
            if stats and curr_count <= 0:
                print("删除成功")
                return (True, 0)
        print(f"删除失败，还剩余 {curr_count} 个物品")
        return (False, curr_count)

    def add_item(self, itemid: int, count: int) -> tuple[bool, int]:
        """尝试添加物品

        Args:
            item (Item): 物品类型
            count (int): 添加的数量

        Returns:
            bool: 是否成功
        """
        if count <= 0:
            return (False, -1)
        curr_count = count
        for block in self.blocks:
            (stats, curr_count) = block.add_item(itemid, curr_count)
            # print(curr_count, curr_count)
            if stats and curr_count <= 0:
                print("添加成功")
                return (True, 0)
        if curr_count == count:
            print("添加失败")
            return (False, curr_count)
        print(f"添加成功，但是还剩余 {curr_count} 个物品")
        return (True, curr_count)

    def __str__(self) -> str:
        return '|'.join([str(block) for block in self.blocks])

if __name__ == "__main__":
    inv = Inventory(20, Inventory.get_itemblocks('0,12|-1,0|-1,0|-1,0|-1,0|-1,0|-1,0|-1,0|-1,0|-1,0'))
    print(inv)
    print(inv.get_block_info(0))