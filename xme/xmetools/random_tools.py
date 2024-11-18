import random
from .json_tools import read_from_path

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


def rand_str(*strings) -> str:
    """返回参数中的随机一个字符串

    Returns:
        str: 随机字符串
    """
    return random.choice(list(strings))

def character_message(character, message_name) -> str | bool:
    """返回指定角色设定的文本

    Args:
        character (str): 角色设定名键
        message_name (str): 消息名键

    Returns:
        str | bool: 消息文本，或者 False 代表无消息/角色
    """
    message = read_from_path("./characters.json")
    chac = message.get(character, False)
    if not chac:
        return False
    result = message[character].get(message_name, False)
    return result

def messy_string(string_input, temperature: float=50):
    """返回一个混乱的字符串

    Args:
        string_input (str): 输入字符串
        temperature (float): 混乱程度 (0 ~ 100)

    Returns:
        str: 混乱字符串
    """
    random_chars = [
        "!",
        "?",
        "@",
        "%",
        "&",
        "*",
        ".",
        "..",
        "??"
    ]
    result = ""
    for c in string_input:
        if c in ['\n', '\r', ' ']:
            result += c
            continue
        if random_percent(temperature):
            if random_percent(temperature):
                result += random.choice(random_chars)
            else:
                result += c
                result += random.choice(random_chars)
        else:
            result += c
    return result

# print(messy_string('你捡到了一个漂流瓶~\n[#101号漂流瓶，来自 "寻找无处不在的179（？）"]：\n-----------\n你不许玩了！*抢走你的.pick\n-----------\n由 "仍然是一只AOS 喵～" 在2024年10月15日 15:24:12 投出\n这个瓶子被捡到了26次，还没有任何赞ovo\n你可以马上发送 "-like" 以点赞，或发送 "-rep" 以举报。\n'))