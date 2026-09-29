import time
from dataclasses import dataclass
import base64
import os
from xme.xmetools import filetools
# import asyncio
import asyncio
import aiohttp
from config import IMAGE_TEMP_PATH
# from aiocqhttp import MessageSegment
from io import BytesIO
from PIL import Image, ImageChops, ImageDraw
import imagehash
# from collections import defaultdict
from xme.xmetools.reqtools import PROXY_URL, fetch_data, fetch_file_stream
import traceback
from xme.xmetools.debugtools import debug_msg
from nonebot.log import logger
try:
    import pyautogui
except Exception:
    pyautogui = None
# from character import get_message
from xme.xmetools.texttools import hash_byte, is_url, object_moderations
import mss
from html2image import Html2Image
from uuid import uuid4
# from PIL import Image
from pyzbar.pyzbar import decode

hti = Html2Image(
)
hti.output_path = IMAGE_TEMP_PATH

async def _is_images_url_can_send(image_urls: list[str]):
    return await object_moderations([{"type": "image_url", "image_url": {"url": u}} for u in image_urls])

def compress_moderation_image(image: Image.Image):
    w, h = image.size
    if w > 6000 or h > 6000:
        image = limit_size(image, 5000)
    buffer = BytesIO()
    image_format = "JPEG"
    image = convert_no_alpha(image)
    if image.mode == "P":
        image_format = "GIF"
        image.save(
            buffer,
            format=image_format,
        )
    else:
        image.save(
            buffer,
            format=image_format,
            quality=75
        )
    original_bytes = buffer.getvalue()
    image_bytes = compress_image_to_size(image, True, True, original_bytes, max_bytes=2 * 1024 * 1024)
    path = f"./data/images/temp/{uuid4().hex}.{image_format}"
    with open(path, "wb") as f:
        f.write(image_bytes)
    # url = filetools.get_local_file_url(path)
    return path

async def get_moderation_image_paths(images: list[Image.Image]):
    paths = []
    for i in images:
        p = await asyncio.to_thread(compress_moderation_image, image=i)
        # url = filetools.get_local_file_url(p)
        paths.append(p)
    return paths

async def is_images_can_send(bot, event, images: list[Image.Image], session=None):
    """图片内容安全检测

    Args:
        session (CommandSession): 当前会话
        images (list[Image.Image]): 待检测图片
    """
    from xme.xmetools.msgtools import analyze_risk
    if len(images) < 1:
        return {"result": True, "reason": ""}
    is_url_invalid = True
    try_times = 0
    results = None
    paths = await get_moderation_image_paths(images)
    while is_url_invalid and try_times < 10:
        try_times += 1  # 计数在循环体推进：空 result_list 等异常响应也能退出，不会死循环
        urls = [filetools.get_local_file_url(p) for p in paths]
        response = await _is_images_url_can_send(urls)
        results = response.get("result_list") if isinstance(response, dict) else None
        if not results:
            logger.warning(f"图片风控返回异常（第 {try_times} 次重试）: {str(response)[:200]}")
            await asyncio.sleep(1)
            continue
        for result in results:
            risk = result['risk_level']
            risk_type = result.get("risk_type", ['未知'])
            if risk == "REJECT" and len(risk_type) < 1:
                logger.info(f"有无效链接, 尝试重新解析 (第 {try_times} 次)")
                continue
            is_url_invalid = False
        if is_url_invalid:
            await asyncio.sleep(1)
    if not results:
        # 风控持续异常：按不通过处理（fail-closed），不让 None 流进 analyze_risk
        return {"result": False, "reason": "风控服务暂时不可用，请稍后再试"}
    return await analyze_risk(results, bot, event, True, session)

def make_circle_image(path_or_image: str | Image.Image) -> Image.Image:

    img = get_image(path_or_image).convert("RGBA")
    w, h = img.size


    d = min(w, h)

    left = (w - d) // 2
    top = (h - d) // 2
    right = left + d
    bottom = top + d
    img_cropped = img.crop((left, top, right, bottom))

    # 创建圆形 mask
    mask = Image.new("L", (d, d), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, d, d), fill=255)

    # 应用 mask
    result = Image.new("RGBA", (d, d))
    result.paste(img_cropped, (0, 0), mask)
    return result

def detect_qrcode(path_or_image: str | Image.Image) -> tuple[bool, list[str]]:
    logger.info("正在检测二维码")
    # RGBA（动图透明帧）转 RGB，避免 pyzbar 不支持透明通道
    results = decode(limit_size(get_image(path_or_image), 800).convert("RGB"))
    if results:
        return True, [r.data.decode("utf-8") for r in results]
    return False, []


def get_hash(path_or_image):
    try:
        return imagehash.phash(get_image(path_or_image))
    except Exception:
        # traceback.logger.debug_exc()
        logger.exception(traceback.format_exc())
        return None

def phash_compare_folder(path_or_image, folder, threshold=5) -> list[tuple[str, int]]:
    """HASH 查重图片

    Args:
        path_or_image (str): 目标图片（路径或 Image）
        folder (str): 查重图片文件夹
        threshold (int, optional): HASH 差别，越低越严格，最大64. Defaults to 5.

    Returns:
        list[tuple[str, int]]: 结果列表（文件路径，差距）
    """
    # target_hash = get_hash(path_or_image)

    result = []   # (filepath, diff)
    for filename in os.listdir(folder):
        path = os.path.join(folder, filename)
        if not os.path.isfile(path):
            continue
        # if path == path_or_image:
        #     continue
        diff = phash_compare(path_or_image, path, threshold=threshold)
        if diff >= 999:
            continue
    # diff 越小越相似
    result.sort(key=lambda x: x[1])
    return result

def phash_compare(target_image: str | Image.Image, compare_image: str| Image.Image, threshold=5):
    # debug_msg("比较", target_image, compare_image)
    target_hash = get_hash(target_image)
    h = get_hash(compare_image)
    result = 999
    if h is None or target_hash is None:
        return result
    diff = target_hash - h
    if diff <= threshold:
        result = diff
    return result


def get_image(path_or_image: str | Image.Image) -> Image.Image:
    """把「路径或图片对象」统一成 PIL 图片；其他类型直接拒绝。

    协议端 get_image 之类的返回是 dict，误传给图片工具时在此立刻报错，
    否则会在深处的 img.size 处抛难以定位的 AttributeError。
    """
    if isinstance(path_or_image, str):
        return read_image(path_or_image)
    if isinstance(path_or_image, Image.Image):
        return path_or_image
    raise TypeError(f"get_image 只接受路径或 PIL 图片，收到 {type(path_or_image).__name__}"
                    f"（协议端的图片响应请先经 get_url_image 取成图片）")

def read_image(path):
    image = Image.open(path)
    return image

def get_html_image(html_str, height=2500, width=1920) -> Image.Image:
    name = f"image-{uuid4()}.png"
    pth = os.path.join(IMAGE_TEMP_PATH, name)
    x = time.time()
    hti.screenshot(html_str=html_str, save_as=name, size=(width, height))
    s = time.time()
    p = s - x
    print(f"ppp{p=}")
    image = crop_transparent_area(pth)
    # os.remove(name)
    return image

async def get_html_image_async(html_str, height=2500, width=1920) -> Image.Image:
    """get_html_image 的异步版：Chrome 渲染 + PIL 裁剪都是秒级同步操作，
    必须经后台线程执行，避免冻结事件循环（async 命令处理器一律用本入口）。
    """
    return await asyncio.to_thread(get_html_image, html_str, height=height, width=width)

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

def                                                                                                                                                                                                                          screenshot(num=1):
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
        except Exception:
            img = pyautogui.screenshot()
            state = False

        # img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
        return img, state

def decode_image_bytes(data: bytes, source: str = "") -> Image.Image:
    """把图片字节解码为 PIL 图片（整图解码校验）；不可识别时抛 ValueError。

    source 只用于错误文案（URL 或文件路径），不参与读取逻辑。
    """
    if not isinstance(data, (bytes, bytearray)):
        raise TypeError(f"图片数据不是字节: {type(data)!r}")
    if len(data) == 0:
        raise ValueError(f"图片数据为空（来源 {source or '未知'}）")
    try:
        image = Image.open(BytesIO(data))
        # 确认整个图片文件确实可被 PIL 解码
        image.load()
        return image
    except Exception as e:
        raise ValueError(
            f"无法识别图片，来源={source or '未知'}, "
            f"数据大小={len(data)} bytes"
        ) from e


async def get_url_image(url, headers={}):
    response = await fetch_data(url, "byte", headers=headers)
    return decode_image_bytes(response, source=f"URL={url!r}")


# 公网图片单次下载的墙钟超时（秒）；失败重试一次，最坏耗时约两倍
IMAGE_FETCH_TIMEOUT = 45.0
# 直链取图失败时的兜底建议：先落到本地再插入，绕开站点的直链访问限制
IMAGE_FETCH_FALLBACK_HINT = "可改用 download 下载到本地后传 ref 插入，或换一个图片直链"


def _image_http_error_text(status: int) -> str:
    """把图片下载的 HTTP 错误码转成可操作的中文说明（含兜底建议）。"""
    if status == 400:
        return (f"目标站点拒绝了该请求（HTTP 400）——链接可能不被允许直接访问"
                f"（部分站点的缩略图只接受固定尺寸参数），{IMAGE_FETCH_FALLBACK_HINT}")
    if status in (401, 403):
        return (f"目标站点拒绝访问（HTTP {status}）——可能需要特定请求头/来源或登录，"
                f"{IMAGE_FETCH_FALLBACK_HINT}")
    if status == 404:
        return f"图片不存在（HTTP 404）——链接可能已失效，{IMAGE_FETCH_FALLBACK_HINT}"
    return f"目标站点返回 HTTP {status}，{IMAGE_FETCH_FALLBACK_HINT}"


async def get_public_url_image(url, *, max_bytes: int, headers: dict | None = None,
                               proxy: str | None = PROXY_URL, retries: int = 1) -> Image.Image:
    """下载公网 URL 的图片并解码，返回 PIL 图片（失败抛 ValueError）。

    面向"接受外部传入 URL"的调用方：经 fetch_file_stream 下载，自带 SSRF 校验
    （DNS 逐 IP 检查 + 钉扎解析 + 重定向逐跳复检）、大小上限与超时，
    并按配置走代理（proxy 缺省取 keys/config 决定的 PROXY_URL，与 download /
    view_image 等取图路径一致；显式传 None 强制直连）。需要访问协议端本地地址的
    调用方请继续使用 get_url_image（它不做公网校验）。
    失败会重试至多 retries 次：仅瞬时故障（超时/连接错误/5xx）重试，
    4xx、超限、SSRF 拒绝等确定性失败立即抛出，避免把等待时间翻倍。
    """
    attempts = max(1, int(retries) + 1)
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            data, _content_type = await fetch_file_stream(
                url, max_size=max_bytes, headers=headers, proxy=proxy,
                timeout=IMAGE_FETCH_TIMEOUT)
            return decode_image_bytes(data, source=f"URL={url!r}")
        except ValueError:
            # SSRF 拒绝/协议不符/大小超限/无法解码：重试无意义，保留原始说明
            raise
        except aiohttp.ClientResponseError as ex:
            if ex.status >= 500 and attempt + 1 < attempts:
                last_error = ex
                continue
            raise ValueError(_image_http_error_text(ex.status)) from ex
        except (asyncio.TimeoutError, aiohttp.ClientError, OSError) as ex:
            if attempt + 1 < attempts:
                last_error = ex
                continue
            raise ValueError(f"下载图片失败（{type(ex).__name__}），"
                             f"{IMAGE_FETCH_FALLBACK_HINT}") from ex
    raise ValueError(f"下载图片失败（{type(last_error).__name__}），"
                     f"{IMAGE_FETCH_FALLBACK_HINT}") from last_error

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

def convert_no_alpha(img: Image.Image):
    if img.mode in ("LA", "RGBA"):
        background = Image.new("RGB", img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[-1])
        img = background
    return img

def image_to_base64(img: Image.Image, to_jpeg=True, ignore_alpha=False) -> str:
    output_buffer = BytesIO()
    # if img.mode == "P":
    #     img = img.convert("RGBA")
    debug_msg("正在将图片转为base64")
    # if (img.mode in ["RGBA", "P"] and not ignore_alpha) or not to_jpeg:
    #     img_mode_dict = {
    #         "RGBA": "PNG",
    #         "LA": "PNG",
    #         "P": "GIF"
    #     }
    #     debug_msg("save to normal")
    #     logger.info("使用 PNG 存储")
    #     img.save(output_buffer, format=img_mode_dict.get(img.mode, "PNG"))
    # else:
    #     logger.info("使用 JPEG 格式")
    #     img = convert_no_alpha(img)
    #     img.save(output_buffer, format="JPEG", quality=75)
    # b64 必须压缩
    if (img.mode in ["RGBA", "P"] and not ignore_alpha) or not to_jpeg:
        # Prefer PNG for modes with transparency. Avoid saving palette (P) as GIF
        # because PIL may expose transparency bytes leading to TypeError.
        img_mode_dict = {
            "RGBA": "PNG",
            "LA": "PNG",
            # Save palette images as PNG after converting to RGBA to be safe
            "P": "PNG",
        }

        debug_msg("save to normal")
        logger.info("使用 PNG 存储")

        # Convert palette images to RGBA to avoid GIF transparency issues
        save_img = img
        if save_img.mode == "P":
            try:
                save_img = save_img.convert("RGBA")
            except Exception:
                # Fallback: convert to RGB if RGBA conversion fails
                save_img = save_img.convert("RGB")

        save_img.save(
            output_buffer,
            format=img_mode_dict.get(img.mode, "PNG")
        )

    else:
        logger.info("使用 JPEG 格式")

        img = convert_no_alpha(img)

        img.save(
            output_buffer,
            format="JPEG",
            quality=75
        )

    original_bytes = output_buffer.getvalue()
    byte_data = compress_image_to_size(img, to_jpeg, ignore_alpha, original_bytes )
    # byte_data = output_buffer.getvalue()
    base64_str = base64.b64encode(byte_data).decode()
    debug_msg("result len", len(base64_str))
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
    debug_msg("result len", len(base64_str))
    return base64_str

def limit_size(image: Image.Image, max_value) -> Image.Image:
    width, height = image.size
    if max(width, height) < max_value:
        return image
    ratio = max_value / float(max(width, height))
    new_width = int(width * ratio)
    new_height = int(height * ratio)
    image_resized = image.resize((new_width, new_height))
    return image_resized

def compress_image_to_size(
    image: Image.Image,
    to_jpeg: bool,
    ignore_alpha: bool,
    original_bytes: bytes,
    max_bytes: int = 5 * 1024 * 1024,
) -> bytes:
    if len(original_bytes) <= max_bytes:
        return original_bytes
    has_alpha = image.mode in ("RGBA", "LA", "PA")

    use_png = (
        (has_alpha and not ignore_alpha)
        or not to_jpeg
    )
    if use_png:
        current = image
        # P 模式如果需要保留透明度，转 RGBA
        if current.mode == "P":
            current = current.convert("RGBA")

        while True:
            buffer = BytesIO()

            current.save(
                buffer,
                format="PNG",
                optimize=True,
            )

            data = buffer.getvalue()

            if len(data) <= max_bytes:
                return data

            width, height = current.size

            if width <= 256 or height <= 256:
                return data

            current = current.resize(
                (
                    max(1, int(width * 0.8)),
                    max(1, int(height * 0.8)),
                ),
                Image.Resampling.LANCZOS,
            )
    else:
        if image.mode not in ("RGB", "L"):
            current = image.convert("RGB")
        else:
            current = image
        quality = 90
        while True:
            while quality >= 30:
                buffer = BytesIO()
                current.save(
                    buffer,
                    format="JPEG",
                    quality=quality,
                    optimize=True,
                )
                data = buffer.getvalue()

                if len(data) <= max_bytes:
                    return data

                quality -= 5
            width, height = current.size
            if width <= 256 or height <= 256:
                return data
            current = current.resize(
                (
                    max(1, int(width * 0.8)),
                    max(1, int(height * 0.8)),
                ),
                Image.Resampling.LANCZOS,
            )
            quality = 90

# async def gif_msg(input_path, scale=1):
#     img = Image.open(input_path)

#     frames = []
#     for frame in range(img.n_frames):
#         img.seek(frame)  # 选中当前帧
#         resized_frame = img.resize(
#             (img.width * scale, img.height * scale), Image.Resampling.NEAREST
#         )  # 放大2倍
#         frames.append(resized_frame.convert("RGBA"))  # 确保格式一致
#     b64 = gif_to_base64(img, frames)
#     debug_msg("gif b64 success")
#     try:
#         # 将消息发送的同步方法放到后台线程执行
#         result = await asyncio.to_thread(create_image_message, b64)
#         return result
#     except Exception as e:
#         logger.error(f"发生错误: {e}")
#         logger.exception(traceback.format_exc())
#         return MessageSegment.text(f"[图片加载失败]")


# async def image_msg(path_or_image, max_size=0, to_jpeg=True, summary=get_message("config", "image_summary")):
#     """获得可以直接发送的图片消息

#     Args:
#         path_or_image (str): 图片路径或图片
#         max_size (int): 图片最大大小，超过会被重新缩放. Defaults to 0.
#         to_jpeg (bool): 是否转换为 Jpeg 格式
#         summary (str): 图片消息预览

#     Returns:
#         MessageSegment: 消息段
#     """
#     is_image = False
#     if not isinstance(path_or_image, str):
#         is_image = True
#     debug_msg(is_image)
#     try:
#         image = path_or_image if is_image else Image.open(path_or_image)
#     except:
#         image = await get_url_image(path_or_image)
#     # image.resize((image.width * scale, image.height * scale), Image.Resampling.NEAREST)
#     if max_size > 0:
#         debug_msg("重新缩放")
#         image = limit_size(image, max_size)
#     debug_msg(image)
#     b64 = image_to_base64(image, to_jpeg)
#     debug_msg("b64 success")
#     # return MessageSegment.image('base64://' + b64, cache=True, timeout=10)
#     try:
#         # 将消息发送的同步方法放到后台线程执行
#         result = await asyncio.to_thread(create_image_message, b64, summary=summary)
#         return result
#     except Exception as e:
#         logger.error(f"发生错误: {e}")
#         logger.exception(traceback.format_exc())
#         return MessageSegment.text(f"[图片加载失败]")

# def create_image_message(b64: str, summary: str="[漠月的图片~]"):
#     """同步发送图片消息"""
#     try:
#         # return MessageSegment.image(f'base64://{b64}', cache=True, timeout=10)
#         return MessageSegment(type_="image", data={
#             'file': f"base64://{b64}",
#             'cache': 1,
#             'timeout': 10,
#             'summary': summary,
#         })
#     except Exception as e:
#         logger.error(f"发送图片时出错: {e}")
#         logger.exception(traceback.format_exc())
#         raise e

if __name__ == "__main__":
    os.makedirs("./data/images/screenshots", exist_ok=True)
    take_screenshot(2)


def split_long_image(data: bytes, max_slices: int = 8) -> tuple[list, tuple[int, int]]:
    """把长截图按宽度切成方形分片（视觉模型会压缩大图，越长的图压得越狠）。

    高度不超过宽度（物理像素）时原样返回单元素列表；超出时按高度 = 宽度逐片切，
    分片数超过 max_slices 则放弃分片原样返回（宁可整图也不无限切）。
    返回 (分片 Image 列表, 原图尺寸 (宽, 高))，只做像素切割，编码与落盘由调用方决定。
    """
    with Image.open(BytesIO(data)) as img:
        img.load()   # 切块/拷贝只在句柄关闭后仍可用：先把像素读进内存
        width, height = img.size
        count = -(-height // width)   # 向上取整的切片数
        if height <= width or count > max_slices:
            return [img.copy()], (width, height)
        parts = [img.crop((0, i * width, width, min((i + 1) * width, height)))
                 for i in range(count)]
        return parts, (width, height)


@dataclass
class ScreenshotOutcome:
    """截图结果：图片字节 + 等待过程信息（供工具层如实汇报给模型）。"""

    png: bytes
    waited_ms: int                  # 真实等待总时长（加载后的缓冲 + 条件等待）
    condition: bool | None = None   # None=未用 wait_until；True=条件满足；False=超时未满足
    via: str = "cdp"                # 出图路径：cdp（真实等待）/ oneshot（降级兜底）


def _file_offline_args(url: str) -> list[str]:
    """file:// 源渲染时整体关闭页面网络：所有 http(s)/ws 子资源请求逼进死代理，
    loopback 与 IP 直连也不例外），页面内容不可信时 iframe/img 借此也探不到内网。"""
    if url.startswith("file:"):
        return ["--proxy-server=http://127.0.0.1:9", "--proxy-bypass-list=<-loopback>"]
    return []


async def _cdp_screenshot(url: str, *, width: int, height: int, wait_ms: int,
                          scale: int, wait_until: str, budget: float) -> ScreenshotOutcome:
    """CDP 路径截图：真实墙钟等待（非虚拟时间）。

    等待顺序为「条件优先、wait_ms 作缓冲」：
    1) 导航并等 readyState 到 complete；
    2) 给了 wait_until 就轮询该 JS 表达式到真值或超时（超时不算失败，如实上报）；
    3) 条件满足（或未给条件）时再真等 wait_ms 作缓冲；条件超时则跳过缓冲。
    """
    from xme.xmetools.browsertools import CDPBrowser, CDPError

    deadline = time.monotonic() + max(5.0, budget)
    waited_ms = 0
    condition: bool | None = None
    async with CDPBrowser(width=width, height=height,
                          extra_args=_file_offline_args(url)) as browser:
        # 1) 导航：readyState 轮询到 complete（navigate 内部用剩余时间兜底）
        await browser.navigate(url, wait_ms=0, timeout=max(5.0, deadline - time.monotonic()))
        expr = (wait_until or "").strip()
        if expr:
            # 2) 条件等待：预算取「剩余总预算」与「条件上限」的较小值
            remain = deadline - time.monotonic()
            if remain > 0.5:
                t0 = time.monotonic()
                condition = await browser.wait_until(expr, timeout=min(remain, wait_until_ms_cap()))
                waited_ms += int((time.monotonic() - t0) * 1000)
        if wait_ms > 0 and condition in (None, True):
            # 3) 缓冲等待：条件超时（condition=False）时跳过
            sleep_ms = min(int(wait_ms), max(0, int((deadline - time.monotonic()) * 1000)))
            if sleep_ms > 0:
                await asyncio.sleep(sleep_ms / 1000)
                waited_ms += sleep_ms
        return ScreenshotOutcome(png=await browser.screenshot(scale=scale),
                                 waited_ms=waited_ms, condition=condition, via="cdp")


def wait_until_ms_cap() -> float:
    """wait_until 条件轮询的时长上限（秒）。"""
    from xme.plugins.commands.ai_helper import constants
    return float(getattr(constants, "SCREENSHOT_MAX_WAIT_UNTIL_MS", 60000)) / 1000


async def chrome_screenshot_bytes(url: str, width: int = 1280, height: int = 800,
                                  wait_ms: int = 1000, timeout_secs: float = 45.0,
                                  scale: int = 1, wait_until: str = "") -> ScreenshotOutcome:
    """用系统 Chrome 无头模式对 url 截图，返回图片字节与等待过程信息。

    wait_ms 是**真实墙钟**等待（页面加载完成后、条件满足后的缓冲等待毫秒数）；
    wait_until 为可选等待条件（CSS 选择器或 JS 表达式），条件优先、wait_ms 作缓冲：
    条件超时会跳过缓冲并如实上报（不是失败）。
    width/height 为视口大小（CSS 像素）；scale 为渲染倍率（>1 时物理分辨率按倍率
    放大，即 Retina 式渲染，文字与小元素更清晰，供视觉模型压缩后仍可读）。
    file:// 源渲染时页面网络整体关闭（见 _file_offline_args）；公网 url 源需正常联网。
    主路径走 CDP（可真等待）；CDP 启动/通信异常时降级为一次性截图兜底（via="oneshot"）。
    """
    from xme.plugins.commands.ai_helper import constants
    budget = float(getattr(constants, "SCREENSHOT_TOTAL_BUDGET", 75))
    try:
        return await _cdp_screenshot(url, width=int(width), height=int(height),
                                     wait_ms=int(wait_ms), scale=int(scale),
                                     wait_until=wait_until, budget=budget)
    except Exception as ex:
        logger.warning(f"CDP 截图失败，降级为一次性截图兜底：{type(ex).__name__}: {ex}")
    return ScreenshotOutcome(
        png=await _oneshot_screenshot(url, width=width, height=height, wait_ms=wait_ms,
                                      timeout_secs=timeout_secs, scale=scale),
        waited_ms=0, condition=None, via="oneshot")


async def _oneshot_screenshot(url: str, width: int = 1280, height: int = 800,
                              wait_ms: int = 1000, timeout_secs: float = 45.0,
                              scale: int = 1) -> bytes:
    """一次性 Chrome 截图（--screenshot + --virtual-time-budget）兜底路径。

    注意 --virtual-time-budget 推进的是**虚拟时钟**（会快进定时器、遇网络请求暂停），
    实际墙钟耗时可能远小于 wait_ms，因此仅作 CDP 不可用时的兜底。
    """
    import asyncio
    import tempfile
    fd, out_path = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    cmd = [
        "google-chrome", "--headless=new", "--disable-gpu",
        "--hide-scrollbars", "--mute-audio", "--no-first-run", "--disable-extensions",
        f"--screenshot={out_path}",
        f"--window-size={int(width)},{int(height)}",
        f"--virtual-time-budget={int(max(0, wait_ms))}",
        f"--timeout={int(timeout_secs * 1000)}",
    ]
    if int(scale) > 1:
        cmd.append(f"--force-device-scale-factor={int(scale)}")
    cmd += _file_offline_args(url)
    cmd.append(url)
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
        try:
            await asyncio.wait_for(proc.wait(), timeout=timeout_secs + 15)
        except asyncio.TimeoutError:
            proc.kill()
            raise RuntimeError(f"Chrome 截图超时（>{timeout_secs + 15:.0f}s）")
        if proc.returncode != 0 or not os.path.exists(out_path) or os.path.getsize(out_path) == 0:
            raise RuntimeError(f"Chrome 截图失败（exit={proc.returncode}）")
        with open(out_path, "rb") as f:
            return f.read()
    finally:
        if os.path.exists(out_path):
            os.unlink(out_path)
