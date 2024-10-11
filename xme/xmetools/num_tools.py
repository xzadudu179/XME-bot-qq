import re

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