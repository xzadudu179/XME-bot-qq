
class FixedList:
    """定长列表
    """
    def __init__(self, length, _type=None) -> None:
        if length <= 0:
            raise ValueError("列表长度必须大于 0")
        self.length = length
        self.items = []
        for _ in range(length):
            self.items.append(_type)

    def append(self, item):
        if len(self.items) >= self.length:
            raise ValueError("列表长度超过最大限制")
        self.items.append(item)

    def __str__(self) -> str:
        return str(self.items)

    def __repr__(self) -> str:
        return repr(self.items)