import time
import os
from xme.xmetools import file_tools
from PIL import Image
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
        # 获取所有的屏幕信息
        monitors = sct.monitors
        # 检查是否有第二个屏幕
        if len(monitors) < num + 1:
            state = False
            num = 0
        # 获取第二个屏幕的信息（第一个元素是全部屏幕，第一个屏幕是monitors[1]，第二个屏幕是monitors[2]）
        second_monitor = monitors[num]
        # 截取第二个屏幕
        screenshot = sct.grab(second_monitor)
        # 转换为PIL图像
        img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
        return img, state


def take_screenshot(screen_num=1):
    os.makedirs("./screenshots", exist_ok=True)
    file_tools.delete_files_in_folder('./screenshots')
    image, state = screenshot(screen_num)
    name = f'./screenshots/screenshot{screen_num}{time.strftime(r"%Y%m%d-%H-%M-%S")}.png'
    image.save(name)
    name = os.path.abspath(name)
    return name, state


if __name__ == "__main__":
    os.makedirs("./screenshots", exist_ok=True)
    take_screenshot(2)