import random
from .jsontools import read_from_path
from PIL import Image
from functools import wraps
random.seed()

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
    # print(rd)
    return rd < percent

def change_seed(seed=None):
    """装饰器，修改函数内 random 的种子或让函数结束后种子重置

    Args:
        func (_type_): 函数
        seed (int | float | str | bytes | bytearray): 种子
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if seed:
                random.seed(seed)
            result = func(*args, **kwargs)
            random.seed()
            return result
        return wrapper
    return decorator

def str_choice(strings) -> str:
    """返回列表中的随机一个字符串，如果参数类型是字符串就直接返回字符串

    Returns:
        str: 随机字符串
    """
    if not isinstance(strings, list):
        return strings
    if len(strings) < 1:
        return ''
    return random.choice(strings)

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

def html_messy_string(string_input, temperature: float=50, resample_times=0, html=True):
    result = messy_string(string_input, temperature, resample_times)
    if not html:
        return result
    return result.replace("<", "&lt;").replace(">", "&gt;").replace(" ", "&nbsp;").replace('"', "&quot;")

def messy_image(path_or_image: str | Image.Image, messy_rate=50, rand_color=True, max_messy_break=False):
    """
    messy_rate: 0~100
    混乱图片，建议图片小一点
    """
    from .imgtools import get_image
    img = get_image(path_or_image)
    w, h = img.size
    pixels = img.load()

    # 根据强度计算次数与块最大尺寸
    boxsize = (w + h) / 2
    max_block_size = int(min(max((messy_rate / 50) * (boxsize / 4), boxsize / 50), boxsize / 5))
    region_count = int((messy_rate) * (boxsize / max_block_size / 8))
    # 最大的
    if messy_rate >= 100 and max_messy_break:
        for y in range(img.height):
            random_color = (
                random.randint(0, 255),
                random.randint(0, 255),
                random.randint(0, 255)
            )
            for x in range(img.width):
                pixels[x, y] = random_color
        return img

    for _ in range(region_count):
        block_size = random.randint(1, max_block_size)

        x1, y1 = random.randint(0, w - block_size), random.randint(0, h - block_size)
        x2, y2 = random.randint(0, w - block_size), random.randint(0, h - block_size)

        block1 = [
            [pixels[x1 + dx, y1 + dy] for dx in range(block_size)]
            for dy in range(block_size)
        ]
        block2 = [
            [pixels[x2 + dx, y2 + dy] for dx in range(block_size)]
            for dy in range(block_size)
        ]
        random_color = (
            random.randint(0, 255),
            random.randint(0, 255),
            random.randint(0, 255)
        )
        random_color1 = (
            random.randint(0, 255),
            random.randint(0, 255),
            random.randint(0, 255)
        )
        for dy in range(block_size):
            random_color = random.random() < 0.1 if rand_color else False
            for dx in range(block_size):
                # 随机颜色
                if random_color:
                    pixels[x1 + dx, y1 + dy] = random_color
                    pixels[x2 + dx, y2 + dy] = random_color1
                    continue
                pixels[x1 + dx, y1 + dy] = block2[dy][dx]
                pixels[x2 + dx, y2 + dy] = block1[dy][dx]
    return img


def messy_string(string_input, temperature: float=50, resample_times=0):
    """返回一个混乱的字符串

    Args:
        string_input (str): 输入字符串
        temperature (float): 混乱程度 (0 ~ 100)
        resample_times (int): 重新采样次数

    Returns:
        str: 混乱字符串
    """
    random_chars = ["!", "?", "@", "%", "#", "&", "*", "**", "^", ".", "..", "??", "$", "\"", "¿", "¡", "=", "<", ">", ",",]
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
    # 重新采样
    if resample_times > 0:
        result = messy_string(result, temperature, resample_times-1)
    return result
# print(messy_string('你捡到了一个漂流瓶~\n[#101号漂流瓶，来自 "寻找无处不在的179（？）"]：\n-----------\n你不许玩了！*抢走你的.pick\n-----------\n由 "仍然是一只AOS 喵～" 在2024年10月15日 15:24:12 投出\n这个瓶子被捡到了26次，还没有任何赞ovo\n你可以马上发送 "-like" 以点赞，或发送 "-rep" 以举报。\n'))