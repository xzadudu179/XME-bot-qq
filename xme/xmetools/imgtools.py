import time
import base64
import os
from xme.xmetools import filetools
import asyncio
from aiocqhttp import MessageSegment
from io import BytesIO
from PIL import Image, ImageChops
from xme.xmetools.reqtools import fetch_data
try:
    import pyautogui
except Exception:
    pyautogui = None
from character import get_message
from xme.xmetools.texttools import hash_byte
import mss
from html2image import Html2Image
from uuid import uuid4
hti = Html2Image()



def get_image(path_or_image: str | Image.Image) -> Image.Image:
    if isinstance(path_or_image, str):
        return read_image(path_or_image)
    return path_or_image

def read_image(path):
    image = Image.open(path)
    return image

def get_html_image(html_str) -> Image.Image:
    name = f"image-{uuid4()}.png"
    hti.screenshot(html_str=html_str, save_as=name, size=(1920, 2500))
    image = crop_transparent_area(name)
    os.remove(name)
    return image

def crop_transparent_area(input_path) -> Image.Image:
    """将透明底 PNG 图片的外侧透明部分切除

    Args:
        input_path (str): 需要处理的图片路径

    Returns:
        Image.Image: 处理完成的图片
    """
    image = Image.open(input_path).convert("RGBA")
    # image = image.convert("RGBA")
    bg = Image.new("RGBA", image.size, (0, 0, 0, 0))
    diff = ImageChops.difference(image, bg)
    bbox = diff.getbbox()

    if bbox:
        cropped = image.crop(bbox)
        return cropped
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

async def get_url_image(url):
    response = await fetch_data(url, 'byte')
    # 将图片数据转换为二进制流
    img_data = BytesIO(response)

    # 打开图片
    img = Image.open(img_data)
    return img

def hash_image(img):
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    img_bytes = buffer.getvalue()
    return hash_byte(img_bytes)

async def get_qq_avatar(qq, size=640):
    return await get_url_image(f"https://q1.qlogo.cn/g?b=qq&nk={qq}&s={size}")

def take_screenshot(screen_num=1):
    os.makedirs("./data/images/screenshots", exist_ok=True)
    filetools.delete_files_in_folder('./data/images/screenshots')
    image, state = screenshot(screen_num)
    name = f'./data/images/screenshots/screenshot{screen_num}{time.strftime(r"%Y%m%d-%H-%M-%S")}.png'
    image.save(name)
    name = os.path.abspath(name)
    return name, state

def get_image_format(image: Image.Image, default="PNG") -> str:
    formats = {
        "1": "PNG",
        "L": "PNG",
        "P": "PNG",
        "RGB": "JPG",
        "RGBA": "PNG",
        "CMYK": "TIFF",
        "YCbCr": "JPG",
        "LAB": "TIFF",
        "I": "TIFF",
        "F": "TIFF",
    }
    return formats.get(image.mode, default)

def image_to_base64(img: Image.Image, to_jpeg=True) -> str:
    output_buffer = BytesIO()
    print("正在将图片转为base64")
    if img.mode in ["RGBA", "P"] or not to_jpeg:
        img_mode_dict = {
            "RGBA": "PNG",
            "P": "GIF"
        }
        print("save to normal")
        img.save(output_buffer, format=img_mode_dict.get(img.mode, "PNG"))
    else:
        img.save(output_buffer, format="JPEG", quality=75)
    byte_data = output_buffer.getvalue()
    base64_str = base64.b64encode(byte_data).decode()
    print("result len", len(base64_str))
    return base64_str

def gif_to_base64(img, frames: list[Image.Image]):
    """将 GIF 以 base64 编码

    Args:
        img (Image): 原 gif 图片
        frames (list[Image.Image]): GIF 帧
    """
    output_buffer = BytesIO()
    frames[0].save(
        output_buffer,
        save_all=True,
        append_images=frames[1:],
        loop=img.info.get("loop", 0),
        duration=img.info.get("duration", 100),
        format="GIF",
        disposal=2,
    )
    byte_data = output_buffer.getvalue()
    base64_str = base64.b64encode(byte_data).decode()
    print("result len", len(base64_str))
    return base64_str

def limit_size(image: Image.Image, max_value) -> Image.Image:
    width, height = image.size
    ratio = max_value / float(max(width, height))
    new_width = int(width * ratio)
    new_height = int(height * ratio)
    image_resized = image.resize((new_width, new_height))
    return image_resized

async def gif_msg(input_path, scale=1):
    img = Image.open(input_path)

    frames = []
    for frame in range(img.n_frames):
        img.seek(frame)  # 选中当前帧
        resized_frame = img.resize(
            (img.width * scale, img.height * scale), Image.Resampling.NEAREST
        )  # 放大2倍
        frames.append(resized_frame.convert("RGBA"))  # 确保格式一致
    b64 = gif_to_base64(img, frames)
    print("gif b64 success")
    try:
        # 将消息发送的同步方法放到后台线程执行
        result = await asyncio.to_thread(create_image_message, b64)
        return result
    except Exception as e:
        print(f"发生错误: {e}")
        return MessageSegment.text(f"[图片加载失败]")


async def image_msg(path_or_image, max_size=0, to_jpeg=True, summary=get_message("config", "image_summary")):
    """获得可以直接发送的图片消息

    Args:
        path_or_image (str): 图片路径或图片
        max_size (int): 图片最大大小，超过会被重新缩放. Defaults to 0.
        to_jpeg (bool): 是否转换为 Jpeg 格式
        summary (str): 图片消息预览

    Returns:
        MessageSegment: 消息段
    """
    is_image = False
    if not isinstance(path_or_image, str):
        is_image = True
    print(is_image)
    try:
        image = path_or_image if is_image else Image.open(path_or_image)
    except:
        image = await get_url_image(path_or_image)
    # image.resize((image.width * scale, image.height * scale), Image.Resampling.NEAREST)
    if max_size > 0:
        print("重新缩放")
        image = limit_size(image, max_size)
    # print(image)
    b64 = image_to_base64(image, to_jpeg)
    print("b64 success")
    # return MessageSegment.image('base64://' + b64, cache=True, timeout=10)
    try:
        # 将消息发送的同步方法放到后台线程执行
        result = await asyncio.to_thread(create_image_message, b64, summary=summary)
        return result
    except Exception as e:
        print(f"发生错误: {e}")
        return MessageSegment.text(f"[图片加载失败]")

def create_image_message(b64: str, summary: str="[漠月的图片~]"):
    """同步发送图片消息"""
    try:
        # return MessageSegment.image(f'base64://{b64}', cache=True, timeout=10)
        return MessageSegment(type_="image", data={
            'file': f"base64://{b64}",
            'cache': 1,
            'timeout': 10,
            'summary': summary,
        })
    except Exception as e:
        print(f"发送图片时出错: {e}")
        raise e

if __name__ == "__main__":
    os.makedirs("./data/images/screenshots", exist_ok=True)
    take_screenshot(2)