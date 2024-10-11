import random

def random_percent(percent : float) -> bool:
    """指定百分比概率返回True

    Args:
        percent (float): 概率

    Raises:
        ValueError: 百分比不在 0 到 100 之间

    Returns:
        bool: 结果
    """
    if not (0 <= percent <= 100):
        raise ValueError("百分比需要设置在 0 到 100 之间")
    rd = random.uniform(0, 100)
    return rd < percent

def random_item(l: list):
    """随机返回列表项

    Args:
        l (list): 列表

    Returns:
        Any: 随机返回一个列表项
    """
    return l[random.randint(0, len(l) - 1)]

def rand_str(*strings) -> str:
    """返回参数中的随机一个字符串

    Returns:
        str: 随机字符串
    """
    return random_item(list(strings))