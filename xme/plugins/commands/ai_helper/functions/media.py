# some are made by Deepseek-v4-flash-vison-exp at Deepseek Harness
"""视觉/图像类工具：图片生成、图片插入与 OCR。"""
import asyncio
import io
from pathlib import Path

from nonebot import MessageSegment
from nonebot.log import logger
from PIL import Image
from xme.xmetools.filetools import bytes_to_file
from xme.xmetools.imgtools import get_public_url_image, image_to_base64, limit_size
from xme.xmetools.msgtools import create_image_message
from xme.xmetools.reqtools import PROXY_URL, fetch_file_stream
from zai import ZhipuAiClient
from keys import GLM_API_KEY
from ..constants import (IMAGE_GEN_CREDITS_HD, IMAGE_GEN_CREDITS_NORMAL,
                         IMAGE_GEN_MAX_REF_IMAGES, MAX_INSERT_IMAGE_SIZE)
from ..llm import LLMError, registry
from ._common import exception_detail
from .files import save_to_history

# 插入消息的图片长边上限（超出等比缩小；不开放给模型传参，防大图打爆内存）。
# 超长图（宽高比 > 3）放宽到 LONG_EDGE：按单一边长压会把手
# 机长截图/网页长截图宽压到几百像素以下（1:6 的长图只剩 ~160px 宽，完全看不清）
INSERT_IMAGE_MAX_EDGE = 2048
INSERT_IMAGE_LONG_EDGE = 4096
# 图片消息的预览文字（summary）
INSERT_IMAGE_SUMMARY = "[AI_helper的图片]"


async def build_image_message(*, url: str = "", path: str | Path | None = None,
                             image: Image.Image | None = None,
                             headers: dict | None = None,
                             proxy: str | None = PROXY_URL) -> MessageSegment:
    """构造「插入用户消息」用的图片消息段；url（公网地址）/path（本地文件）/image（内存图）三选一。

    返回的 MessageSegment 由 agent 收进 pending_messages，随本轮最终回复一起发给用户。
    url 经 get_public_url_image 下载（SSRF 校验 + MAX_INSERT_IMAGE_SIZE 上限 + 瞬时
    故障重试），默认按配置走代理（与 download / view_image 取图一致）。
    headers 仅供来源可信的调用方附带认证（如 gen_image 拿到的 GLM 生成结果），
    接受外部 URL 的场景一律不要传，避免把密钥带到第三方主机。
    image 供已持有像素的调用方直连（如 b64 型生成结果），免落盘、免下载。
    失败统一抛 ValueError（含中文原因与兜底建议），由调用方决定如何回报给模型。
    """
    if sum(1 for v in (url, path, image) if v) != 1:
        raise ValueError("url、path、image 必须三选一")
    if image is None:
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
    width, height = image.size
    ratio = max(width, height) / max(1, min(width, height))
    cap = INSERT_IMAGE_LONG_EDGE if ratio > 3 else INSERT_IMAGE_MAX_EDGE
    image = limit_size(image, cap)
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

def _image_suffix(data: bytes) -> str:
    """按魔数取图片扩展名（存 temp 时决定文件名后缀；识别不出按 png）。"""
    if data[:3] == b"\xff\xd8\xff":
        return ".jpg"
    if data[:4] == b"\x89PNG":
        return ".png"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return ".gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp"
    return ".png"


async def _resolve_reference_images(ref, url, cap, agent) -> tuple[list[bytes], str]:
    """解析参考图双入口（文件引用 ref + 公网直链 url，可混用）为字节列表。

    返回 (字节列表, "") 或 ([], 错误文案)。直链走 fetch_file_stream 的
    SSRF 校验 + 体积上限，默认经代理（与 download 取图行为一致）。
    """
    refs = [str(r).strip() for r in (ref or []) if str(r).strip()]
    urls = [str(u).strip() for u in (url or []) if str(u).strip()]
    if not refs and not urls:
        return [], ""
    if "image" not in (cap.get("input") or ["text"]):
        return [], "[图片生成失败：当前模型不支持参考图输入，请只用文字描述]"
    if len(refs) + len(urls) > IMAGE_GEN_MAX_REF_IMAGES:
        return [], f"[图片生成失败：参考图最多 {IMAGE_GEN_MAX_REF_IMAGES} 张（ref 与 url 合计）]"
    images: list[bytes] = []
    for r in refs:
        try:
            path = Path(agent.resolve_ref(r))
        except KeyError:
            return [], f"[图片生成失败：没有找到参考图引用 {r}]"
        if not path.is_file():
            return [], f"[图片生成失败：参考图引用 {r} 指向的文件不存在]"
        images.append(path.read_bytes())
    for u in urls:
        if not u.lower().startswith(("http://", "https://")):
            return [], f"[图片生成失败：参考图 url 需以 http(s) 开头：{u}]"
        try:
            data, _ctype = await fetch_file_stream(
                u, max_size=MAX_INSERT_IMAGE_SIZE, timeout=30)
        except Exception as ex:
            return [], f"[图片生成失败：参考图下载失败 {u}（{exception_detail(ex)}）]"
        images.append(data)
    return images, ""


async def gen_image(prompt, action: str = "send", size="2k",
                    quality: str = "normal", ref=None, url=None,
                    save_to: str = "", agent=None):
    """生成图片（OpenAI 兼容 images 抽象层；供应商与档位模型在 image_gen 能力里配置）。

    action="send"（默认）把成图插入本轮结束消息发给用户，base64 只在这一步产生；
    action="save" 把成图存为文件返回引用——save_to 填 history 保存名（如
    "画作/日落.png"，文件夹须已存在）则转存 history，不填存 temp。
    ref（文件引用）与 url（公网直链）为参考图双入口；模型不支持图片输入时显式报错。
    """
    if agent is None:
        return "[图片生成失败：缺少会话上下文]"
    cap = registry.get_capability("image_gen")
    models = cap.get("models") or {}
    if quality not in models:
        return f"[图片生成失败：quality 只支持 {'、'.join(models) or '（未配置）'}]"
    ref_images, ref_error = await _resolve_reference_images(ref, url, cap, agent)
    if ref_error:
        return ref_error
    provider = registry.get_image_provider(cap.get("provider", ""))
    if provider is None:
        return f"[图片生成失败：图片服务 {cap.get('provider')} 未配置（keys.LLM_PROVIDERS）]"
    try:
        result = await provider.generate(
            prompt, model=models[quality], size=size,
            quality=(cap.get("quality_map") or {}).get(quality, ""),
            images=ref_images, extra_body=cap.get("extra_body") or {})
    except LLMError as ex:
        logger.warning(f"图片生成失败 [{ex.provider}/{models[quality]}] {ex}")
        return f"[图片生成失败：{ex}]"
    except Exception as ex:
        logger.exception(f"图片生成失败: {ex}")
        return f"[图片生成失败：{exception_detail(ex)}]"
    # 生成成功即按质量档位计费（tokens 等效值；normal ≈ 现价 0.1 元/张）
    agent.other_credits += (IMAGE_GEN_CREDITS_HD if quality == "hd"
                            else IMAGE_GEN_CREDITS_NORMAL)
    action = (action or "send").strip()
    if action == "send":
        if result.urls:
            # 直链来自图片服务（可信来源），按需附带认证头下载；直连不经代理更稳
            return await build_image_message(url=result.urls[0],
                                             headers=result.download_headers, proxy=None)
        with Image.open(io.BytesIO(result.b64_images[0])) as opened:
            return await build_image_message(image=opened.copy())
    if action == "save":
        if result.urls:
            try:
                data, _ctype = await fetch_file_stream(
                    result.urls[0], max_size=MAX_INSERT_IMAGE_SIZE,
                    headers=result.download_headers, proxy=None, timeout=60)
            except Exception as ex:
                return f"[图片生成失败：成图下载失败（{exception_detail(ex)}）]"
        else:
            data = result.b64_images[0]
        try:
            temp_ref = bytes_to_file(data, agent.user_id, _image_suffix(data), agent)["ref"]
        except FileExistsError as ex:
            # 同内容成图已存在：反查既有引用复用
            temp_ref = next((r for r, name in agent.ref_map.items() if name == str(ex)), "")
        if not temp_ref:
            return "[图片生成失败：成图保存失败（引用分配异常）]"
        if save_to:
            folder, _, name = save_to.strip().rpartition("/")
            saved = save_to_history(temp_ref, history_ref=name, path=folder, agent=agent)
            detail = saved.get("result", "") if isinstance(saved, dict) else str(saved)
            return f"图片已生成并转存 history。\n{detail}"
        return (f"图片已生成，保存在 temp（引用 {temp_ref}）。\n"
                f"可用 send_file 发给用户、insert_image 插入消息或 save_to_history 转存。")
    return f"[图片生成失败：未知的操作 {action}（仅支持 send/save）]"

