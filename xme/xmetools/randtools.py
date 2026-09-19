import random
from .jsontools import read_from_path
from PIL import Image
import numpy as np
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
    混乱图片，建议图片小一点。返回扰动后的新图，不修改入参
    """
    from .imgtools import get_image
    img = get_image(path_or_image)
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGBA")
    w, h = img.size

    # 根据强度计算次数与块最大尺寸
    boxsize = (w + h) / 2
    max_block_size = max(1, int(min(max((messy_rate / 50) * (boxsize / 4), boxsize / 50), boxsize / 5)))
    region_count = int((messy_rate) * (boxsize / max_block_size / 8))
    # 最大的
    if messy_rate >= 100 and max_messy_break:
        # 每行一个随机色的全图噪声。numpy 向量化替代逐像素 Python 循环
        # （几十万~数百万次循环会同步卡住调用方数秒）
        row_colors = np.random.randint(0, 256, size=(h, 3), dtype=np.uint8)
        noise = np.broadcast_to(row_colors[:, None, :], (h, w, 3)).copy()
        if img.mode == "RGBA":
            noise = np.concatenate(
                [noise, np.full((h, w, 1), 255, dtype=np.uint8)], axis=2)
        return Image.fromarray(noise, "RGBA" if img.mode == "RGBA" else "RGB")

    arr = np.asarray(img).copy()

    def random_color():
        color = np.random.randint(0, 256, size=3, dtype=np.uint8)
        if img.mode == "RGBA":
            color = np.append(color, 255)
        return color

    for _ in range(region_count):
        block_size = random.randint(1, max_block_size)

        x1, y1 = random.randint(0, w - block_size), random.randint(0, h - block_size)
        x2, y2 = random.randint(0, w - block_size), random.randint(0, h - block_size)

        if rand_color and random.random() < 0.1:
            # 随机颜色
            arr[y1:y1 + block_size, x1:x1 + block_size] = random_color()
            arr[y2:y2 + block_size, x2:x2 + block_size] = random_color()
            continue
        block1 = arr[y1:y1 + block_size, x1:x1 + block_size].copy()
        arr[y1:y1 + block_size, x1:x1 + block_size] = arr[y2:y2 + block_size, x2:x2 + block_size]
        arr[y2:y2 + block_size, x2:x2 + block_size] = block1
    return Image.fromarray(arr)


def messy_string(string_input, temperature: float=50, resample_times=0, t:int = 1):
    """返回一个混乱的字符串

    Args:
        string_input (str): 输入字符串
        temperature (float): 混乱程度 (0 ~ 100)
        resample_times (int): 重新采样次数

    Returns:
        str: 混乱字符串
    """
    random_types = {
        0: "ⰀⰁⰂⰃⰄⰅⰆⰇᚖᚗᚘⰈⰉⰊⰋⰌⰍⰎⰏⰐⰑⰒⰓⰔⰕⰖⰗꚠꚡꚢꚣꚤꚥꚦꚧꚨꚩꚪꚫꚬꚭꚮꚯꚰꚱꚲꚳꚴꚵꚶꚷꚸꚹꚺꚻꚼꚽꚾꚿꛀꛁꛂꛃꛄꛅꛆꛇꛈꛉꛊꛋꛌꛍꛎꛏꛐꛑꛒꛓꛔꛕ𓇠ᐱⵇ",
        1: "𒀀𒀁𒀂𒀃𒀄𒀅𒀆𒀇𒀈𒀉𒀊𒀒𒀓𒀭𒂊𒄿𒅀𒆠𒇻𒈠𒉌𒊒𒋗𒌋𒍣𒎙ᚏᚠᚢᚦᚨᚱᚲᚳᚴᚵᚶᚷᚸᚹᚺᚻᚼᚽᚾᚿᛀᛁᛂᛃᛄᛅᛆᛇᛈᛉᛊᛋᛌᛍᛎᛏᛐᛑᛒᛓ𓇠ꚡꚢꚣꚤꚥꚦꚧꚨꚩꚪꚫꚬꚭꚮꚯꚰꚱꚲꚳꚴꚵꚶꚷꚸꚹꚺꚻꚼꚽꚾꚿꛀꛁꛂꛃꛄᐱⵇ"
    }
    # random_chars = ["!", "?", "@", "%", "#", "&", "*", "**", "^", ".", "..", "??", "$", "\"", "¿", "¡", "=", "<", ">", ",",]
    random_chars = random_types[t]
    result = ""
    for c in string_input:
        if c in ['\n', '\r', ' ']:
            result += c
            continue
        if random_percent(temperature):
            if random_percent(temperature):
                for _ in range(random.randint(1, 3)):
                    result += random.choice(random_chars)
            else:
                result += c
                for _ in range(random.randint(1, 2)):
                    result += random.choice(random_chars)
        else:
            result += c
    # 重新采样
    if resample_times > 0:
        result = messy_string(result, temperature, resample_times-1)
    return result
# print(messy_string('你捡到了一个漂流瓶~\n[#101号漂流瓶，来自 "寻找无处不在的179（？）"]：\n-----------\n你不许玩了！*抢走你的.pick\n-----------\n由 "仍然是一只AOS 喵～" 在2024年10月15日 15:24:12 投出\n这个瓶子被捡到了26次，还没有任何赞ovo\n你可以马上发送 "-like" 以点赞，或发送 "-rep" 以举报。\n'))