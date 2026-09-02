from pathlib import Path
import time
import traceback

from nonebot import MessageSegment

from nonebot.log import logger
from xme.xmetools.filetools import search_json
from xme.xmetools.imgtools import get_url_image, image_to_base64, limit_size
from xme.xmetools.texttools import regex_filter
from xme.xmetools.timetools import TELIA_CLOCK
from zai import ZhipuAiClient
from keys import GLM_API_KEY, TAVILY_API_KEY
from typing import Literal
from tavily import AsyncTavilyClient
from xme.xmetools.msgtools import create_image_message, send_session_msg
from character import get_message
import asyncio

def get_telia_clock_state():
    return TELIA_CLOCK.get_current_state()

# 将其作为内部函数
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

def get_skill_md(name: str):
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

async def inprocess_report(message: str, agent):
    from . import __plugin_name__
    # 最小间隔s
    MIN_INTERVAL = 30
    try:
        last_response_time = agent.last_response
        curr_response_time = time.time()
        interval = curr_response_time - last_response_time
        if interval < 30:
            return f"[调用回复失败：最小间隔为 {MIN_INTERVAL}s，当前距离上次调用间隔为 {interval}s。]"
        # 中途汇报内容给用户
        await send_session_msg(agent.session, get_message("plugins", __plugin_name__, "inprocess_report", msg=message))
        agent.last_response = time.time()
        return f"成功向用户发送消息"
    except Exception as ex:
        return f"[发送消息失败：{ex}]"

async def gen_image(prompt, size="1024x1024", agent=None):
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
            agent.other_credits += 80000
        image_msg = await get_image_msg(response.data[0].url)
        return image_msg
    except Exception as e:
        logger.exception(f"图片生成失败: {e}")
        return f"[图片生成失败: {e}]"

def get_webs_partial(key, file_ref, search_str, search_method: Literal["fuzzy_match", "re_search", "re_filter"] = "fuzzy_match", agent=None):
    file_name = agent.REF_MAP[file_ref]
    path = agent.get_temp_path() / file_name
    method = None
    search_methods = {
        # "re_search": regex_search,
        "re_search": None,
        "re_filter": regex_filter,
        # "fuzzy_match": None,
    }
    method = search_methods.get(search_method, None)

    return {"result": "\n".join([f"{i + 1}. {c}" for i, c in enumerate(search_json(search_str, path, key, search_func=method))]), "no_compress": True}

async def web_search(query: str, max_results: int = 10, depth: Literal["basic", "advanced", "fast", "ultra-fast"] = "basic", time_range: str = "year"):
    tavily = AsyncTavilyClient(
        api_key=TAVILY_API_KEY
    )
    result = await tavily.search(
        query=query,
        max_results=max_results,
        search_depth=depth,
        time_range=time_range
    )
    return {
        "query": query,
        "results": [
            {
                "title": item["title"],
                "url": item["url"],
                "content": item["content"],
            }
            for item in result["results"]
        ]
    }
