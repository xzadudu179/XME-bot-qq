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
from ..llm import registry

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
    """OCR 图片文字：按能力配置 LLM_CAPABILITIES["ocr"] 分派实现。

    api = "glm_layout_parsing"（默认）：GLM 专用版面解析接口（效果最好）；
    api = "chat"：走统一 provider 的视觉模型 + 提取文字的提示词（任意兼容端点可用）。
    """
    cap = registry.get_capability("ocr")
    api = cap.get("api") or "glm_layout_parsing"
    if api == "chat":
        provider = registry.get_provider(cap.get("provider", ""))
        if provider is None:
            return f"[图片 OCR 失败：provider {cap.get('provider')} 未配置]"
        try:
            result = await provider.chat(
                [{"role": "user", "content": [
                    {"type": "text", "text": "请提取这张图片里的全部文字，按原样输出，不要添加解释。"},
                    {"type": "image_url", "image_url": {"url": url}}]}],
                model=cap.get("model", ""), temperature=0.1)
            if agent is not None:
                # 计费：缓存倍率取自该 OCR 模型在目录里的配置（未命中则用默认）
                billing_entry = registry.model_by_name(cap.get("model", "")) or {}
                agent.tokens += result.usage.billable_tokens(
                    registry.cache_credit_ratio(billing_entry)) * 0.125
            return result.text or "[没有识别到内容]"
        except Exception as ex:
            logger.exception(f"图片 OCR 失败: {ex}")
            return f"[图片 OCR 失败: {ex}]"
    if api != "glm_layout_parsing":
        return f"[图片 OCR 失败：未知的 OCR 实现 {api}（LLM_CAPABILITIES['ocr']）]"
    client = ZhipuAiClient(api_key=cap.get("api_key") or GLM_API_KEY)
    try:
        response = await asyncio.to_thread(
            client.layout_parsing.create,
            model=cap.get("model") or "glm-ocr",
            file=url
        )
        result = response.md_results
        if agent is not None:
            agent.tokens += response.usage.total_tokens * 0.125
        if result is None:
            return "[没有识别到内容]"
        return result
    except Exception as ex:
        logger.exception(f"图片 OCR 失败: {ex}")
        return f"[图片 OCR 失败: {ex}]"

async def gen_image(prompt, action: str = "send", size="1024x1024", agent=None):
    cap = registry.get_capability("image_gen")
    client = ZhipuAiClient(api_key=cap.get("api_key") or GLM_API_KEY)
    try:
        response = await asyncio.to_thread(
            client.images.generations,
            model=cap.get("model") or "glm-image",
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

