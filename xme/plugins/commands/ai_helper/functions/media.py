# some are made by Deepseek-v4-flash-vison-exp at Deepseek Harness
"""视觉/图像类工具：图片生成、图片插入与 OCR。"""
import asyncio
from pathlib import Path

from nonebot import MessageSegment
from nonebot.log import logger
from PIL import Image
from xme.xmetools.imgtools import get_public_url_image, image_to_base64, limit_size
from xme.xmetools.msgtools import create_image_message
from xme.xmetools.reqtools import PROXY_URL
from zai import ZhipuAiClient
from keys import GLM_API_KEY
from ..constants import IMAGE_GEN_CREDITS, MAX_INSERT_IMAGE_SIZE
from ..llm import registry

# 插入消息的图片长边上限（超出等比缩小；不开放给模型传参，防大图打爆内存）
INSERT_IMAGE_MAX_EDGE = 1024
# 图片消息的预览文字（summary）
INSERT_IMAGE_SUMMARY = "[AI_helper的图片]"


async def build_image_message(*, url: str = "", path: str | Path | None = None,
                             headers: dict | None = None,
                             proxy: str | None = PROXY_URL) -> MessageSegment:
    """构造「插入用户消息」用的图片消息段；url（公网地址）与 path（本地文件）二选一。

    返回的 MessageSegment 由 agent 收进 pending_messages，随本轮最终回复一起发给用户。
    url 经 get_public_url_image 下载（SSRF 校验 + MAX_INSERT_IMAGE_SIZE 上限 + 瞬时
    故障重试），默认按配置走代理（与 download / view_image 取图一致）。
    headers 仅供来源可信的调用方附带认证（如 gen_image 拿到的 GLM 生成结果），
    接受外部 URL 的场景一律不要传，避免把密钥带到第三方主机。
    失败统一抛 ValueError（含中文原因与兜底建议），由调用方决定如何回报给模型。
    """
    if bool(url) == bool(path):
        raise ValueError("url 与 path 必须二选一")
    if path is not None:
        file = Path(path)
        if not file.is_file():
            raise ValueError(f"本地文件不存在（{file}）")
        size = file.stat().st_size
        if size > MAX_INSERT_IMAGE_SIZE:
            raise ValueError(f"图片过大（{size / 1048576:.1f}MiB > "
                             f"{MAX_INSERT_IMAGE_SIZE // 1048576}MiB）")
        try:
            with Image.open(file) as opened:
                # 复制出独立图片：with 退出后底层文件即关闭，后续缩放/编码不再依赖文件句柄
                image = opened.copy()
        except Exception as ex:
            raise ValueError(f"无法识别图片（{ex}）") from ex
    else:
        image = await get_public_url_image(
            url, max_bytes=MAX_INSERT_IMAGE_SIZE, headers=headers, proxy=proxy)
    image = limit_size(image, INSERT_IMAGE_MAX_EDGE)
    # 编码与消息构造是同步 CPU/IO 操作，放后台线程避免卡事件循环
    b64 = await asyncio.to_thread(image_to_base64, image)
    return await asyncio.to_thread(create_image_message, b64, summary=INSERT_IMAGE_SUMMARY)


async def insert_image(url: str = "", ref: str = "", agent=None):
    """把一张图片插入到本轮要发送给用户的消息里（url 与 ref 二选一）。

    url：公网图片地址（http/https）；ref：已在本会话的 temp/history 文件引用。
    插入的图片会附在本轮最终回复里一起发给用户，无需再调 send_file。
    """
    if bool(url) == bool(ref):
        return "[插入图片失败：url 与 ref 二选一]"
    if ref:
        if agent is None:
            return "[插入图片失败：缺少会话上下文，无法解析文件引用]"
        try:
            path = Path(agent.resolve_ref(ref))
        except KeyError:
            return f"[插入图片失败：没有找到引用 {ref}]"
        try:
            return await build_image_message(path=path)
        except ValueError as ex:
            return f"[插入图片失败：{ex}]"
    try:
        return await build_image_message(url=url.strip())
    except ValueError as ex:
        return f"[插入图片失败：{ex}]"

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
            # url 来自 GLM 生成结果（可信来源），附带认证头下载后复用同一插入逻辑；
            # proxy=None 保持该路径原有的直连行为（GLM 为国内服务，不经代理更稳）
            return await build_image_message(
                url=response.data[0].url,
                headers={"Authorization": f"Bearer {GLM_API_KEY}"},
                proxy=None)
        elif action == "url":
            return response.data[0].url
        raise ValueError(f"[未知的图片生成操作: {action}]")
    except Exception as e:
        logger.exception(f"图片生成失败: {e}")
        return f"[图片生成失败: {e}]"

