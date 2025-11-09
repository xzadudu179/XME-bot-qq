import colorspacious as cs
import numpy as np
import re
import math

def rgb_text(text, f=(255, 255, 255), b=(0, 0, 0), background=False):
    """给文字上色

    Args:
        r (_type_): red
        g (_type_): green
        b (_type_): blue
        text (str): 文字内容

    Returns:
        _type_: 上色的文字
    """
    fr, fg, fb = f
    reset_sequence = "\033[0m"
    fg_color_sequence = f"\033[38;2;{fr};{fg};{fb}m"

    return_content = f"{fg_color_sequence}{text}{reset_sequence}"
    if background:
        br, bg, bb = b
        bg_color_sequence = f"\033[48;2;{br};{bg};{bb}m"
        return_content = f"{fg_color_sequence}{bg_color_sequence}{text}{reset_sequence}"
    return return_content

def hex_text(text, f="#FFFFFF", b="#000000", background=False):
    rgb_text(text=text , f=hex_to_rgb(f), b=hex_to_rgb(b))

def hex_to_rgb(hex_color):
    """Convert hex color to RGB."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def rgb_to_hex(rgb_color):
    """Convert RGB color to hex."""
    return '#{:02x}{:02x}{:02x}'.format(*rgb_color)

def get_color_differences(color1: str | tuple, color2: str | tuple):
    """得到两个颜色的向量差距

    Args:
        color1 (str | tuple): 颜色1
        color2 (str | tuple): 颜色2

    Returns:
        floating[Any]: 颜色差距
    """
    # print("111")
    color1, color2 = to_rgb_and_verify(color1, color2)
    c1 = np.array(color1)
    c2 = np.array(color2)
    distance = np.linalg.norm(c1 - c2)
    # print("222")
    return distance

def to_rgb_and_verify(*colors: str | tuple) -> tuple:
    result_colors = []
    for color in colors:
        if type(color) == str:
            color = hex_to_rgb(color)
        if type(color) == tuple and len(color) != 3:
            raise ValueError("颜色 RGB 值元组长度不等于 3")
        result_colors.append(color)
    return tuple(result_colors)

def get_color_luminance(color: str | tuple) -> float:
    """得到颜色亮度

    Args:
        color (str | tuple): 颜色

    Returns:
        float: 亮度值（最高为 255）
    """
    # print("xwx")
    color = to_rgb_and_verify(color)[0]
    # print(color)
    luminance = 0.299 * color[0] + 0.587 * color[1] + 0.114 * color[2]
    # print("uwu")
    return luminance

def invent_color(color: str | tuple) -> str | tuple:
    """反转颜色

    Args:
        color (str | tuple): 颜色（十六进制或 RGB）

    Returns:
        str | tuple: 返回的颜色（与输入的颜色类型相同）
    """
    to_hex = False
    if type(color) == str:
        color = hex_to_rgb(color)
        to_hex = True
    color = [255 - c for c in color]
    if to_hex:
        color = rgb_to_hex(color)
    return color

def hex_to_lab(hex_color):
    """Convert hex color to LAB using colorspacious."""
    rgb_color = np.array(hex_to_rgb(hex_color)) / 255.0
    lab_color = cs.cspace_convert(rgb_color, "sRGB1", "CIELab")
    return lab_color

def lab_to_hex(lab_color):
    """Convert LAB color to hex using colorspacious."""
    rgb_color = cs.cspace_convert(lab_color, "CIELab", "sRGB1")
    rgb_color = np.clip(rgb_color * 255, 0, 255).astype(int)
    return rgb_to_hex(tuple(rgb_color))

def clear_text_color(text: str) -> str:
    """清除文本里的颜色字符

    Args:
        text (str): 文本

    Returns:
        str: 没有颜色的字符串
    """
    # ANSI转义序列的正则表达式模式
    ansi_escape = re.compile(r'\x1b(\[.*?[@-~]|\].*?(\x07|\x1b\\))')
    return ansi_escape.sub('', text)

def mix_hex_color_lab(hex_color1, hex_color2, ratio):
    # 混合颜色
    lab1 = np.array(hex_to_lab(hex_color1))
    lab2 = np.array(hex_to_lab(hex_color2))
    mixed_lab = lab1 * (1 - ratio) + lab2 * ratio
    return lab_to_hex(mixed_lab)


def gradient_hex_color(hex_color1, hex_color2, num_colors):
    """将两个十六进制颜色进行渐变处理，返回指定数量的十六进制颜色列表

    Args:
        hex_color1 (_type_): 第一个颜色
        hex_color2 (_type_): 第二个颜色
        num_colors (_type_): 列表长度

    Returns:
        _type_: 渐变颜色列表
    """
    lab1 = hex_to_lab(hex_color1)
    lab2 = hex_to_lab(hex_color2)

    # 进行渐变
    interpolated_colors = np.linspace(lab1, lab2, num_colors)

    # 返回列表
    gradient_colors = [lab_to_hex(color) for color in interpolated_colors]

    return gradient_colors

def gradient_text(*hex_colors, text: str, background=False, bgc=(255, 255, 255), use_list = False) -> str:
    """生成渐变字符串

    Args:
        text (str): 需要渐变的字符串
        background (bool): 是否启用背景颜色
        bgc (tuple): 背景颜色rgb
        use_list (bool): 是否将颜色识别为列表
    Returns:
        str: 渐变后的字符串
    """
    # 分成几份
    parsed_colors = list(hex_colors)
    if use_list:
        parsed_colors = []
        for color in hex_colors:
            parsed_colors += color
    text_split_count = len(parsed_colors) - 1
    if text_split_count > len(text):
        raise ValueError("颜色数量需要比字符数量少")
    elif len(parsed_colors) <= 1:
        raise ValueError("颜色数量至少为2")
    # print(parsed_colors)
    splits = []
    reg_splits = split_string(text, text_split_count)
    for i, split in enumerate(reg_splits):
        colors = gradient_hex_color(parsed_colors[i], parsed_colors[i + 1], len(split))
        color_split = ""
        split = split[1:] if i > 0 else split
        for j, char in enumerate(split):
            r, g, b = hex_to_rgb(colors[j + 1] if i > 0 else colors[j])
            color_split += rgb_text(char, f=(r, g, b), background=background, b=bgc)
        splits.append(color_split)
    return "".join(splits)


def split_string(s, group_count):
    # 将字符串分成几个组
    n = len(s) + group_count - 1
    step = math.ceil(n / group_count)
    groups = []
    for i in range(group_count):
        start = i * step - i if i > 0 else 0
        # end = start + step + (1 if i < n % (group_count + 1) else 0)
        split = s[start: start + step]
        groups.append(split)

    return groups

if __name__ == "__main__":
    gra_text = gradient_text("#FF5555", "#FFFF55", "#55FF55", "#55FFFF", "#5555FF", "#FF55FF", text="测试一下渐变字符串的效果嗷呜, 测试")
    print(gra_text)
    print(invent_color("#1f1e33"))