import time
import base64
import os
from xme.xmetools import file_tools
from aiocqhttp import MessageSegment
from io import BytesIO
from PIL import Image
import pyautogui
import mss

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


def take_screenshot(screen_num=1):
    os.makedirs("./screenshots", exist_ok=True)
    file_tools.delete_files_in_folder('./screenshots')
    image, state = screenshot(screen_num)
    name = f'./screenshots/screenshot{screen_num}{time.strftime(r"%Y%m%d-%H-%M-%S")}.png'
    image.save(name)
    name = os.path.abspath(name)
    return name, state

def image_to_base64(img: Image.Image, format='PNG') -> str:
    output_buffer = BytesIO()
    img.save(output_buffer, format)
    byte_data = output_buffer.getvalue()
    base64_str = base64.b64encode(byte_data).decode()
    return 'base64://' + base64_str

def image_msg(path):
    """获得可以直接发送的图片消息

    Args:
        path (str): 图片位置

    Returns:
        MessageSegment: 消息段
    """
    return MessageSegment.image(image_to_base64(Image.open(path)))

if __name__ == "__main__":
    os.makedirs("./screenshots", exist_ok=True)
    take_screenshot(2)