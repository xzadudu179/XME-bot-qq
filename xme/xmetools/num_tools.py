import re
import math

def is_prime(n: int) -> bool:
    """检查是否为质数

    Args:
        n (int): 被检查的数

    Returns:
        bool: 是否为质数
    """
    # 处理小于2的情况（0, 1不是质数）
    if n <= 1:
        return False
    # 2 和 3 是质数
    if n <= 3:
        return True
    # 排除能被2或3整除的数
    if n % 2 == 0 or n % 3 == 0:
        return False
    # 从5开始检查，跳过偶数（步长为6）
    for i in range(5, int(math.sqrt(n)) + 1, 6):
        if n % i == 0 or n % (i + 2) == 0:
            return False
    return True


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