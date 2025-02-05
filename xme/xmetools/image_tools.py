import time
import base64
import os
from xme.xmetools import file_tools
from xme.xmetools.text_tools import hash_text
from aiocqhttp import MessageSegment
from io import BytesIO
from PIL import Image
import pyautogui
import mss
import requests

def read_image(path):
    image = Image.open(path)
    return image

def screenshot(num=1):
    """检测是否有第 num 个显示器并截图，如果没有指定的显示器就截取全部

    Args:
        num (int, optional): 显示器序号. Defaults to 2.
    """
    state = True
    with mss.mss() as sct:
    # with mss.mss() as sct:
        # 获取所有的屏幕信息
        monitors = sct.monitors
        # 检查是否有那么多屏幕
        if len(monitors) < num + 1:
            state = False
            num = 0
        monitor = monitors[num]
        try:
            screenshot = sct.grab(monitor)
            # 转换为PIL图像
            img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
        except:
            img = pyautogui.screenshot()
            state = False

        # img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
        return img, state

def get_url_image(url):
    response = requests.get(url)

    if response.status_code == 200:
        # 将图片数据转换为二进制流
        img_data = BytesIO(response.content)

        # 打开图片
        img = Image.open(img_data)
        return img
    else:
        raise Exception("获取图片失败")

def get_qq_avatar(qq, size=640):
    return get_url_image(f"https://q1.qlogo.cn/g?b=qq&nk={qq}&s={size}")

def take_screenshot(screen_num=1):
    os.makedirs("./screenshots", exist_ok=True)
    file_tools.delete_files_in_folder('./screenshots')
    image, state = screenshot(screen_num)
    name = f'./screenshots/screenshot{screen_num}{time.strftime(r"%Y%m%d-%H-%M-%S")}.png'
    image.save(name)
    name = os.path.abspath(name)
    return name, state

def image_to_base64(img: Image.Image) -> str:
    output_buffer = BytesIO()
    img.save(output_buffer, "PNG")
    byte_data = output_buffer.getvalue()
    base64_str = base64.b64encode(byte_data).decode()
    return 'base64://' + base64_str


def image_msg(path_or_image):
    """获得可以直接发送的图片消息

    Args:
        path_or_image (str): 图片路径或图片

    Returns:
        MessageSegment: 消息段
    """
    is_image = False
    if not isinstance(path_or_image, str):
        is_image = True
    # print(is_image)
    image = path_or_image if is_image else Image.open(path_or_image)
    # print(image_to_base64(image))
    return MessageSegment.image(image_to_base64(image))

if __name__ == "__main__":
    os.makedirs("./screenshots", exist_ok=True)
    take_screenshot(2)