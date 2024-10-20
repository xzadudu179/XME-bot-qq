
class FixedList:
    """定长列表
    """
    def __init__(self, length) -> None:
        self.length = length
        self.items = []

    def append(self, item):
        if len(self.items) >= self.length:
            raise ValueError("列表长度超过最大限制")
        self.items.append(item)

    def __str__(self) -> str:
        return str(self.items)

    def __repr__(self) -> str:
        return repr(self.items)