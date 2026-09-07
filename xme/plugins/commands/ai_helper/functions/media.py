# some are made by Deepseek-v4-flash-vison-exp at Deepseek Harness
"""视觉/图像类工具：图片生成与 OCR。"""
import asyncio
import traceback

from nonebot import MessageSegment
from nonebot.log import logger
from xme.xmetools.imgtools import get_url_image, image_to_base64, limit_size
from xme.xmetools.msgtools import create_image_message
from zai import ZhipuAiClient
from keys import GLM_API_KEY
from ..constants import IMAGE_GEN_CREDITS

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

def get_skill_md(name: str, agent=None):
    skill = ""
    content = ""
    try:
        with open(f"./static/skills/{name}.md", 'r', encoding="utf-8") as file:
            skill = file.read()
    except Exception as ex:
        content = f"[寻找 skill 文件发生错误：{ex}]"
    if skill == "":
        content = "[这个 skill 似乎是空白的。]"
    content = skill
    agent.activate_skills.append(name)
    return {"result": content, "no_compress": True}

async def ocr_image(url, agent=None):
    client = ZhipuAiClient(api_key=GLM_API_KEY)
    try:
        response = await asyncio.to_thread(
            client.layout_parsing.create,
            model="glm-ocr",
            file=url
        )
        result = response.md_results
        if agent is not None:
            agent.tokens += response.usage.total_tokens * 0.125
        # response.usage.prompt_tokens_details.
        if result is None:
            return "[没有识别到内容]"
        return result
    except Exception as ex:
        logger.exception(f"图片 OCR 失败: {ex}")
        return f"[图片 OCR 失败: {ex}]"

async def gen_image(prompt, action: str = "send", size="1024x1024", agent=None):
    client = ZhipuAiClient(api_key=GLM_API_KEY)
    try:
        response = await asyncio.to_thread(
            client.images.generations,
            model="glm-image",
            prompt=prompt,
            size=size,
            # quality=quality,
            quality="hd",
        )
        if agent is not None:
            # 图片生成按 80000 tokens 算
            agent.other_credits += IMAGE_GEN_CREDITS
        action = action or "send"
        if action == "send":
            image_msg = await get_image_msg(response.data[0].url)
            return image_msg
        elif action == "url":
            return response.data[0].url
        raise ValueError(f"[未知的图片生成操作: {action}]")
    except Exception as e:
        logger.exception(f"图片生成失败: {e}")
        return f"[图片生成失败: {e}]"

