from items.itemblock import ItemBlock
class FixedList:
    """定长列表
    """
    def __init__(self, length, default_list=[]) -> None:
        if length <= 0:
            raise ValueError("列表长度必须大于 0")
        elif len(default_list) > length:
            raise ValueError("默认列表长度不能比设定长度大")
        self.length = length
        self.__items = default_list
        # for _ in range(length):
        #     self.items.append(None)
        self.fillwith(None)

    @property
    def items(self):
        # 只读访问 items，返回副本以避免外部修改
        return self.__items[:]

    def append(self, item):
        # if len(self.items) >= self.length:
        #     raise ValueError("列表长度超过最大限制")
        for index, i in enumerate(self.items):
            if i != None:
                continue
            # i 为 None 时增加内容
            # print(index)
            self.__items[index] = item
            return
        raise ValueError("列表长度超过最大限制")

    def getlist(self) -> list:
        return self.items

    def __getitem__(self, index):
        return self.items[index]

    def __setitem__(self, index, value):
        if self.items[index] == None:
            raise ValueError("索引范围过大，请先使用 append() 添加默认值再更改内容")
        self.__items[index] = value

    def fillwith(self, item, replace=False):
        """将定长列表填充默认值

        Args:
            item (Any): 想要的值
            replace (bool): 是否替换原有的值
        """
        filled = []
        for i in range(self.length):
            try:
                ri = self.items[i]
            except IndexError:
                ri = None
            if ri != None and not replace:
                filled.append(ri)
                continue
            filled.append(item)
        self.__items = filled

    def __add__(self, addlist: list):
        for additem in addlist:
            self.append(additem)

    def __str__(self) -> str:
        return str(self.items)

    def __repr__(self) -> str:
        return repr(self.items)

# l = FixedList(20, [4, 5, 6])
# l.append(1)
# l.append(2)
# l.append(3)
# l + [5, 6, 7]
# ll = []
# print(l)
# print(len(l.items))