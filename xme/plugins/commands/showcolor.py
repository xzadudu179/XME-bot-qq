from nonebot import message_preprocessor, NoneBot
from nonebot.plugin import PluginManager
import aiocqhttp
from xme.xmetools.doctools import SpecialDoc
from ...xmetools import colortools as c
from character import get_message
from xme.xmetools.msgtools import send_event_msg
from xme.xmetools.texttools import fullwidth_to_halfwidth
from xme.xmetools.filetools import has_file
from xme.xmetools.imgtools import image_msg
from nonebot.log import logger
from PIL import Image, ImageDraw, ImageFont

# alias = ['系统状态', 'stats']
__plugin_name__ = '色号显示'
__plugin_usage__ = str(SpecialDoc(
    name=__plugin_name__,
    desc=get_message("plugins", __plugin_name__, 'desc'),
    introduction=get_message("plugins", __plugin_name__, 'introduction'),
))

@message_preprocessor
async def is_it_command(bot: NoneBot, event: aiocqhttp.Event, _: PluginManager):
    raw_msg = fullwidth_to_halfwidth(event.raw_message.strip()).upper()
    # print(raw_msg)
    color_num_str = raw_msg.split("#")[-1]
    if not raw_msg.startswith("#") or len(color_num_str) not in [3, 6]:
        return
    elif len(color_num_str) == 3:
        color_num_str = "".join([c + c for c in color_num_str])
    try:
        path = gen_color_image(color_num_str)
        # return await event_send_msg(bot, event, f"[CQ:image,file=http://server.xzadudu179.top:17980/temp/{name}]", False)
        return await send_event_msg(bot, event, await image_msg(path, to_jpeg=False))
    except ValueError:
        return

def gen_color_image(color_num, size=(300, 200)):
    name = f"color_{color_num}.png"
    path = f"./data/images/temp/{name}"
    if has_file(path):
        logger.debug("使用缓存")
        return path
    width, height = size
    color = f"#{color_num}"
    image = Image.new("RGB", (width, height), color)
    draw = ImageDraw.Draw(image)#1
    font_size = 48
    font = ImageFont.truetype("static/fonts/Cubic_11.ttf", font_size)

    text_bbox = draw.textbbox((0, 0), color, font=font)  # 返回 (x_min, y_min, x_max, y_max)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    text_x = (width - text_width) // 2
    text_y = (height - text_height) // 2 - (font_size // 8)
    # 文字颜色
    text_color = c.invent_color(color)
    if c.get_color_differences(text_color, color) < 30:
        text_color = "#000000" if c.get_color_luminance(color) > 128 else "#FFFFFF"
    # 绘制文字
    draw.text((text_x, text_y), color, fill=text_color, font=font)
    image.save(path)
    return path