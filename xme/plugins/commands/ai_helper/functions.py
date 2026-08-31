import traceback

from nonebot import MessageSegment

from nonebot.log import logger
from xme.xmetools.imgtools import get_url_image, image_to_base64, limit_size
from xme.xmetools.timetools import TELIA_CLOCK
from zai import ZhipuAiClient
from keys import GLM_API_KEY
from typing import Literal
from xme.xmetools.msgtools import create_image_message
import asyncio

def get_telia_clock_state():
    return TELIA_CLOCK.get_current_state()

async def get_image_msg(url, max_size = 1024):
    image = await get_url_image(url, headers={
        "Authorization": f"Bearer {GLM_API_KEY}"
    })
    # image.resize((image.width * scale, image.height * scale), Image.Resampling.NEAREST)
    if max_size > 0:
        image = limit_size(image, max_size)
    b64 = image_to_base64(image)
    # return MessageSegment.image('base64://' + b64, cache=True, timeout=10)
    try:
        result = await asyncio.to_thread(create_image_message, b64, summary="[AI_helper的图片]")
        return result
    except Exception as e:
        logger.error(f"发生错误: {e}")
        logger.exception(traceback.format_exc())
        return MessageSegment.text("[图片加载失败]")

async def gen_image(prompt, size="1024x1024", quality: Literal['standard', 'hd'] ="standard"):
    client = ZhipuAiClient(api_key=GLM_API_KEY)
    try:
        response = await asyncio.to_thread(
            client.images.generations,
            model="cogview-3-plus",
            prompt=prompt,
            size=size,
            quality=quality,
        )
        return response.data[0].url
    except Exception as e:
        logger.exception(f"图片生成失败: {e}")
        return f"图片生成失败: {e}"
