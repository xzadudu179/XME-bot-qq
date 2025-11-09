import re
import math
from decimal import Decimal, getcontext

def is_prime(n: int) -> bool:
    """检查是否为质数

    Args:
        n (int): 被检查的数

    Returns:
        bool: 是否为质数
    """
    if n <= 1:
        return False
    # 2 和 3 是质数
    if n <= 3:
        return True
    if n % 2 == 0 or n % 3 == 0:
        return False
    # 从5开始检查，跳过偶数（步长为6）
    for i in range(5, int(math.sqrt(n)) + 1, 6):
        if n % i == 0 or n % (i + 2) == 0:
            return False
    return True

def to_nums_base(num: int, num_strs: list[str]):
    """将数字转换为任意进制字符列表，例如定义 ["a", "b", "c"]，会将十进制数字替换为数字字符为 a b c 的三进制数字

    Args:
        num (int): 输入的数字
        num_strs (list[str]): 定义的字符列表

    Returns:
        _type_: _description_
    """
    base = len(num_strs)
    if len(num_strs) < 2:
        raise ValueError("进制不可小于2")
    # if base > len(nums):
    #     return "进制过大"
    result = ""
    div_num = abs(num)
    while div_num != 0:
        result += num_strs[div_num % base]
        div_num = div_num // base
    if num < 0:
        result += '-'
    elif num == 0:
        result = num_strs[0]
    return result[::-1]

def divs(n):
    ds = []
    n = Decimal(n)
    for i in range(2, int(Decimal(math.sqrt(n))) + 1):
        if n % i == 0:
            ds.append(f"{i} * {n // i} = {n}")
        if len(ds) >= 20:
            ds.append("...")
            return ds
    return ds

def extract_numbers(s):
    """提取数字

    Args:
        s (str): 要提取的字符串

    Returns:
        list: 数字组
    """
    # 使用正则表达式提取所有数字
    numbers = re.findall(r'\d+', s)
    # 将提取到的数字转换为整数列表
    return [int(num) for num in numbers]

# if __name__ == "__main__":
#     print(to_nums_base(1, ["a", "b"]))