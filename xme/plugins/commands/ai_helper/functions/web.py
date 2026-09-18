# some are made by Deepseek-v4-flash-vison-exp at Deepseek Harness
"""网络类工具：url 下载、网页阅读、web 搜索与图片/视频/文档内容查看。"""
import asyncio
import io
from pathlib import Path
import html
import mimetypes
import re
import time
from urllib.parse import urlparse
import aiohttp
from uuid import uuid4
from PIL import Image

from zai import ZhipuAiClient

from keys import GLM_API_KEY, DOMAIN, FILE_TOKENS
from nonebot.log import logger
from xme.xmetools.filetools import (
    bytes_to_file, decode_text, detect_file_type, get_local_file_url, FileType,
)
from xme.xmetools.videotools import download_video, is_video_url, parse_video
from xme.xmetools.videotools.probe import get_video_duration
from xme.xmetools.msgtools import create_image_message
from xme.xmetools.reqtools import assert_public_http_url, fetch_file_stream, glm_api_request
from xme.xmetools.imgtools import chrome_screenshot_bytes, image_to_base64, limit_size, read_image
from xme.xmetools.bottools import bot_call_action
from ..constants import MAX_DOWNLOAD_FILE_SIZE
from xme.plugins.commands.ai_helper.llm import registry
from config import IMAGE_TEMP_PATH, CONTAINER_BOT_PATH
from ._common import exception_detail, ImageToolResult
from .. import received_files
# 别名导入：get_received_files 的参数名 save_to_history 会遮蔽同名函数
from .files import save_to_history as _save_to_history

_TYPE_EXTENSIONS = {
    FileType.IMAGE: ".png",
    FileType.PDF: ".pdf",
    FileType.ARCHIVE: ".zip",
    FileType.TEXT: ".txt",
    FileType.BINARY: ".bin",
    FileType.EMPTY: ".bin",
}


def _url_suffix(url: str) -> str:
    """从 URL 路径取扩展名（2~6 位字母数字的 .xxx）；没有则返回空串。"""
    suffix = Path(urlparse(url).path).suffix.lower()
    if 2 <= len(suffix) <= 6 and re.fullmatch(r"\.[a-z0-9]+", suffix):
        return suffix
    return ""


def _save_received_bytes(data: bytes, url: str, content_type: str, agent) -> dict:
    """探测后缀并写入用户 temp（download 与 get_received_files 共用的落盘单点）。

    后缀探测顺序：URL 扩展名 → Content-Type → 魔数探测；文本文件统一转 utf-8。
    """
    probe = agent.get_temp_path() / f"{uuid4().hex}.part"
    probe.write_bytes(data)
    suffix = _url_suffix(url)
    if not suffix:
        main_type = (content_type or "").split(";")[0].strip().lower()
        guessed = mimetypes.guess_extension(main_type, strict=False) if main_type else None
        suffix = guessed if guessed and main_type != "application/octet-stream" else ""
    if not suffix:
        suffix = _TYPE_EXTENSIONS.get(detect_file_type(probe), ".bin")
    if detect_file_type(probe) == FileType.TEXT:
        data = decode_text(data).encode("utf-8")
    probe.unlink(missing_ok=True)
    return bytes_to_file(data, agent.user_id, suffix, agent)

async def download(url: str, agent):
    """异步下载 url 指向的文件到 temp 文件夹（上限 MAX_DOWNLOAD_FILE_SIZE）。
    """
    # 网页里抄来的链接常带 HTML 实体（&amp; 等），还原成原始字符
    url = html.unescape((url or "").strip())
    if urlparse(url).scheme not in ("http", "https"):
        return "[下载失败：url 需要以 http:// 或 https:// 开头]"
    try:
        data, content_type = await fetch_file_stream(url, max_size=MAX_DOWNLOAD_FILE_SIZE)
    except ValueError as ex:
        return f"[下载失败：{ex}]"
    except TimeoutError:
        logger.warning(f"下载超时: {url}")
        return "[下载失败：连接/下载超时（60s），目标站点可能不可达（被墙）或响应过慢]"
    except aiohttp.ClientResponseError as ex:
        # 4xx/5xx 是链接本身的常见问题，报错附带排查方向，省去 AI 盲试下一轮
        logger.warning(f"下载 {url} 失败：HTTP {ex.status}")
        if ex.status == 404:
            return ("[下载失败：404 Not Found——链接失效或路径/分支错误。"
                    "GitHub raw 链接注意分支名（main/master）与文件在仓库内的实际路径；"
                    "不确定时可先用 read_webpage 打开对应页面确认]")
        if ex.status in (401, 403):
            return (f"[下载失败：HTTP {ex.status}——目标站点拒绝访问（可能反爬或需要登录）；"
                    "可尝试换源，或用 read_webpage 查看页面内容]")
        return f"[下载失败：HTTP {ex.status} {ex.message}——目标站点返回错误，可确认链接后重试]"
    except Exception as ex:
        logger.exception(f"下载 {url} 失败")
        return f"[下载失败：{exception_detail(ex)}]"
    if not data:
        return "[下载失败：文件为空]"

    # 后缀探测与落盘（与 get_received_files 共用单点）
    try:
        res = _save_received_bytes(data, url, content_type, agent)
    except FileExistsError as ex:
        # 查重命中：报错中止，不分配新 ref；反查已有引用供 AI 直接使用（不产生第二个引用）
        dup_name = str(ex)
        existing_ref = next((r for r, name in agent.ref_map.items() if name == dup_name), None)
        hint = f"，直接使用已有引用 {existing_ref} 即可" if existing_ref else "（无本会话引用，可能是之前会话遗留）"
        return {"result": f"[下载中止：相同内容的文件已存在于 temp（{dup_name}）{hint}]",
                "ref": existing_ref, "file_name": dup_name, "size": len(data), "no_compress": True}
    result_text = (
        f"已下载到 temp：{res['file_name']}（{res['size'] / 1048576:.2f} MiB），"
        f"引用 {res['ref']}。文本文件可用 check_file 查看内容，"
        f"其他类型可用 view_document_file / view_image / view_video 查看，或用 save_to_history 转存。"
    )
    return {"result": result_text, "ref": res["ref"], "file_name": res["file_name"],
            "size": res["size"], "no_compress": True}


def _from_container_path(path: str) -> Path:
    """协议端（容器）路径 → bot 本地路径：/xmebot/data/... → ./data/...；无前缀则原样返回。"""
    p = Path(path)
    try:
        return Path(".") / p.relative_to(CONTAINER_BOT_PATH)
    except ValueError:
        return p


async def _fetch_received_file_data(item, agent) -> tuple[bytes, str]:
    """下载一条私聊文件记录的原始字节：缓存直链优先，OneBot get_file API 兜底。

    返回 (data, "") 或 (b"", 失败原因)。
    """
    max_size = MAX_DOWNLOAD_FILE_SIZE
    if item.size and item.size > max_size:
        return b"", f"文件 {item.size / 1048576:.1f} MiB 超过 {max_size / 1048576:.0f} MiB 下载上限"
    if item.url and urlparse(item.url).scheme in ("http", "https"):
        try:
            data, _ = await fetch_file_stream(item.url, max_size=max_size)
            if data:
                return data, ""
        except Exception as ex:
            logger.info(f"私聊文件直链下载失败（{item.name}），改走 get_file 兜底: {ex}")
    session = agent.session
    if session is None or getattr(session, "bot", None) is None:
        return b"", "直链下载失败且无会话上下文（无法调用 get_file 兜底）"
    if not item.file_id:
        return b"", "直链下载失败且协议端未提供 file_id（无法调用 get_file 兜底）"
    try:
        info = await bot_call_action(session.bot, "get_file", file_id=item.file_id)
    except Exception as ex:
        return b"", f"get_file 调用失败（{exception_detail(ex)}）"
    if not isinstance(info, dict):
        return b"", "get_file 返回结构不符合预期"
    remote_url = str(info.get("url") or "")
    if remote_url.startswith("http"):
        try:
            data, _ = await fetch_file_stream(remote_url, max_size=max_size)
            if data:
                return data, ""
        except Exception as ex:
            logger.info(f"get_file 返回的 url 下载失败（{item.name}）: {ex}")
    local = _from_container_path(str(info.get("file") or ""))
    if local.is_file():
        try:
            return local.read_bytes(), ""
        except OSError as ex:
            return b"", f"协议端本地文件不可读（{ex}）"
    return b"", "文件已过期或暂不可下载，请让用户重新发送"


async def get_received_files(max_count: int = 5, within_hours: float = 24.0,
                             save_to_history: bool = False, agent=None):
    """获取当前用户最近在私聊里发给机器人的 QQ 文件（数据源见 received_files.py）。"""
    items = received_files.recent_private_files(
        agent.user_id, within_hours=within_hours, max_count=max_count)
    if not items:
        return {"result": "[没有找到你最近在私聊里发送的文件：确认文件是私聊发给机器人的、"
                "且在指定时间范围内；bot 刚重启也可能丢失更早的记录，可让用户重新发送]",
                "no_compress": True}
    files: list[dict] = []
    for item in items:
        sent_at = time.strftime("%m-%d %H:%M", time.localtime(item.time))
        entry = {"file_name": item.name, "sent_at": sent_at}
        data, err = await _fetch_received_file_data(item, agent)
        if err:
            entry["error"] = err
            files.append(entry)
            continue
        try:
            res = _save_received_bytes(data, item.url or item.name, "", agent)
        except FileExistsError as ex:
            dup_name = str(ex)
            existing_ref = next((r for r, name in agent.ref_map.items() if name == dup_name), None)
            if existing_ref:
                entry.update({"ref": existing_ref, "size": item.size, "saved": "temp",
                              "note": f"temp 已有相同内容的文件（{dup_name}），直接使用引用 {existing_ref}"})
            else:
                entry.update({"ref": None, "size": item.size, "saved": "temp",
                              "note": f"temp 已有相同内容的文件（{dup_name}）但本会话没有对应引用，"
                                       f"可直接使用该文件（check_file 引用名 {dup_name}）"})
            files.append(entry)
            continue
        except Exception as ex:
            entry["error"] = f"落盘失败：{exception_detail(ex)}"
            files.append(entry)
            continue
        entry.update({"ref": res["ref"], "size": res["size"], "saved": "temp"})
        if save_to_history:
            hres = _save_to_history(res["ref"], agent=agent)
            if hres.get("ref"):
                entry.update({"ref": hres["ref"], "saved": "history"})
            else:
                entry["history_error"] = (hres.get("result") or "").strip("[]")
        files.append(entry)
    ok = sum(1 for f in files if f.get("ref"))
    parts = []
    for f in files:
        if f.get("ref"):
            line = (f"{f['file_name']}（{f['sent_at']} 发送）→ 引用 {f['ref']}"
                    f"（{f['size'] / 1048576:.2f} MiB，存于 {f['saved']}")
            if f.get("note"):
                line += f"；{f['note']}"
            line += "）"
            if f.get("history_error"):
                line += f"；转存 history 失败：{f['history_error']}"
            parts.append(line)
        else:
            parts.append(f"{f['file_name']}（{f['sent_at']} 发送）→ 获取失败：{f.get('error')}")
    tail = ("文本文件可用 check_file 查看内容，其他类型可用 view_document_file / view_image / view_video 查看。"
            if save_to_history else
            "temp 文件在本轮对话结束会清理，需要保留请用 save_to_history 转存。"
            "文本文件可用 check_file 查看内容，其他类型可用 view_document_file / view_image / view_video 查看。")
    result_text = f"共获取 {ok}/{len(files)} 个私聊文件：" + "；".join(parts) + "。" + tail
    return {"result": result_text, "files": files, "no_compress": True}

async def web_search(query: str, max_results: int = 10, time_range: str = ""):
    """联网搜索薄壳：多引擎抽象层按配置顺序自动回退（keys.SEARCH_PROVIDERS）。"""
    from ..search import search_with_fallback
    resp = await search_with_fallback(query, max_results=max_results, time_range=time_range)
    return {
        "query": resp.query,
        "engine": resp.engine,
        "results": [
            {
                "title": item.title,
                "url": item.url,
                "content": item.content,
                "score": round(item.score, 3),
            }
            for item in resp.results
        ],
    }

async def view_document_file(ref: str = "", url: str = "", prompt: str = "", force_use_agent=False, agent=None):
    return await view_item(ref, url, prompt, item_type="file", force_use_agent=force_use_agent, agent=agent)

async def view_video(ref: str = "", url: str = "", prompt: str = "", force_use_agent=False, agent=None):
    # 平台页面链接（B站/YouTube 等）：yt-dlp 解析时长 + 下载到本地后以限时链接交给模型
    # （GLM 的 video_url 只认媒体直链，页面 URL 会报格式解析错误）；
    # 直链媒体文件/本地文件：ffprobe 校验时长后原样处理
    if not ref and url and is_video_url(url):
        info = await parse_video(url)
        dur = info.duration if info else None
        if not dur:
            return "[查看视频错误：无法解析该平台视频的时长]"
        if dur > 600:
            return "[查看视频错误：视频时长过长 (>10分钟)]"
        result = await download_video(url, agent.get_temp_path(), timeout=600)
        if not result.ok or not result.file_paths:
            return f"[查看视频错误：视频下载失败（{result.error}）]"
        agent.temp_file_paths += result.file_paths  # 对话结束随 temp 清理
        url = get_local_file_url(str(result.file_paths[0]))  # 合集只分析第一个视频
        return await view_item(url=url, prompt=prompt, item_type="video_url", force_use_agent=force_use_agent, agent=agent)
    path_or_url = agent.resolve_ref(ref) if ref else url
    dur = await get_video_duration(path_or_url)
    if not dur:
        return "[查看视频错误：无法解析视频文件时长]"
    if dur > 600:
        return "[查看视频错误：视频时长过长 (>10分钟)]"
    return await view_item(ref, url, prompt, item_type="video_url", agent=agent)

async def view_image(ref: str = "", url: str = "", prompt: str = "", force_use_agent=False, agent=None):
    return await view_item(ref, url, prompt, item_type="image_url", force_use_agent=force_use_agent, agent=agent)


# ---- 媒体可解析性探测（注入前校验，避免"声称已附上但模型实际加载失败"的误判）----

_MEDIA_PROBE_MAX_SIZE = 4 * 1024 * 1024  # 探测下载上限；超限属"无法判定"，按放行处理
_MEDIA_PROBE_HEAD = 64 * 1024            # 本地文件只读头部即可判定格式

# 视频容器文件头（mp4/mov 的 ftyp 在偏移 4 处，单独判断）
_VIDEO_MAGICS = (
    b"\x1a\x45\xdf\xa3",   # webm / mkv
    b"FLV",                # flv
    b"\x00\x00\x01\xba",   # mpeg-ps
    b"\x00\x00\x01\xb3",   # mpeg-ts
)


def _looks_like_video(head: bytes) -> bool:
    """按文件头粗判是否视频容器。"""
    if head[4:8] == b"ftyp":                    # mp4 / mov / m4v
        return True
    if head[:4] in _VIDEO_MAGICS:
        return True
    if head[:4] == b"RIFF" and head[8:12] == b"AVI ":
        return True
    return False


def _check_media_bytes(data: bytes, item_type: str) -> str | None:
    """校验已取到的字节是否为该类型可解析的媒体；不通过返回原因，通过返回 None。"""
    if not data:
        return "内容为空"
    if item_type == "image_url":
        try:
            with Image.open(io.BytesIO(data)) as img:
                img.format  # 触发头部解析（不完整数据也能判定格式）
            return None
        except Exception:
            return "内容不是可解析的图片格式"
    if item_type == "video_url":
        return None if _looks_like_video(data[:16]) else "内容不是可识别的视频格式"
    return None  # 文档类只要可读取即可


async def _media_probe(url: str, item_type: str) -> str | None:
    """探测媒体能否被解析：返回明确的失败原因，None 表示可注入。

    本地限时链接（我们自己的 /file/<token>）反查本地文件校验——零网络且最准，
    顺带能发现链接已过期；外部 http(s) 下载校验，HTTP 错误或内容不是目标媒体即判失败。
    超时/连接错误/体积过大等"无法判定"的情况按放行处理：若模型侧仍加载失败，会由
    1210 兜底把结果显式改写为加载失败，不会静默误判。
    """
    # 1) 本地限时链接：反查 token 直接校验本地文件
    if url.startswith("http") and "/file/" in url and DOMAIN in url:
        token = url.split("/file/", 1)[1].split("?", 1)[0].strip("/")
        info = FILE_TOKENS.get(token)
        if not info:
            return "本地链接无效或已过期，请重新生成"
        path = Path(info["path"])
        if not path.is_file() or path.stat().st_size == 0:
            return "本地文件不存在或为空"
        try:
            with open(path, "rb") as f:
                return _check_media_bytes(f.read(_MEDIA_PROBE_HEAD), item_type)
        except OSError as ex:
            return f"本地文件读取失败（{ex}）"
    # 2) 外部地址：下载校验
    if not url.startswith(("http://", "https://")):
        return None  # data:/file: 等无法本地校验，放行
    try:
        data, _ctype = await fetch_file_stream(url, max_size=_MEDIA_PROBE_MAX_SIZE, timeout=15)
    except aiohttp.ClientResponseError as ex:
        return f"无法访问该地址（HTTP {ex.status}）"
    except ValueError as ex:
        msg = str(ex)
        return None if "超出" in msg else msg  # 体积超限不判定；SSRF/协议类明确失败
    except (asyncio.TimeoutError, aiohttp.ClientError):
        return None  # 网络类不确定：放行，兜底显式告知
    except Exception:
        return None
    return _check_media_bytes(data, item_type)

async def view_item(ref: str = "", url: str ="", prompt: str ="", item_type: str ="", force_use_agent: bool = False, agent=None):
    """查看 url 里的内容（图片/视频/文件），按 prompt 让模型解读并返回结果。

    作为 AI 可调用 tool 使用：当前轮模型本身是视觉模型（flash）时不再发起独立
    GLM 调用，而是返回 ImageToolResult 把内容直接注入当前对话由模型亲眼看；
    否则（无视觉能力的模型）走原路径：用配置的视觉模型（LLM_CAPABILITIES.vision）单独分析后返回文本。
    单独调用消耗的 tokens 会通过 agent 计入用户 credits。
    """
    if ref:
        url = get_local_file_url(agent.resolve_ref(ref))
    if not url:
        return "[分析 url 内容错误：ref 与 url 均无内容]"
    name = ""
    match item_type:
        case "file":
            name = "file_url"
        case "image_url":
            name = "url"
        case "video_url":
            name = "url"
        case _:
            raise ValueError(f"无法识别的输入类型 \"{item_type}\"")
    part = {"type": item_type, item_type: {name: url}}
    # 视觉轮直注入：省一次独立调用与重复计费，模型在原对话里直接看
    if agent is not None and getattr(agent, "current_vision", False) and not force_use_agent:
        type_names = {"file": "文件", "image_url": "图片", "video_url": "视频"}
        label = type_names.get(item_type, item_type)
        # 注入前探测：解析不了的媒体绝不谎称"已附上"，显式报告给模型
        probe_error = await _media_probe(url, item_type)
        if probe_error:
            return (f"[{label}无法解析，未附入输入：{probe_error}]"
                    f"（可让用户重新发送该{label}，或先下载到本地改用 ref 传入）")
        return ImageToolResult(
            f"[{label}内容已直接附在输入中，请针对该{label}完成：{prompt}]",
            [part])
    system_prompt = (
        "你是一个用于查看并解析指定 url 内容的模型。"
        "请根据用户给出的 prompt，仔细查看 url 里的内容并回答。"
        "如果内容是一张图片或视频，描述/分析其内容；如果是文件，提取并总结关键信息。"
        "输出应当准确、简洁、直接，不要编造图片或文本里不存在的内容。"
        "若用户提出要你审查，请严谨、严格、苛刻地说明其中所有可能有问题的地方"
        "（但是没有问题不要编造）并且详细审查内容"
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": [
            {"type": "text", "text": prompt},
            part,
        ]},
    ]
    try:
        # 视觉分析走统一 provider（能力配置 vision：默认 GLM flash，可改为其他兼容端点）
        entry = registry.vision_entry()
        provider = registry.get_provider(entry["provider"])
        if provider is None:
            return f"[查看文件失败：provider {entry['provider']} 未配置]"
        result = await provider.chat(messages, model=entry["model"], temperature=0.3)
        # 计费 tokens 到 credits（带外调用，跟随会话模型倍率折算）
        if agent is not None:
            agent.other_credits += result.usage.billable_tokens(registry.cache_credit_ratio(entry))
        return result.text or "[没有识别到内容]"
    except Exception as ex:
        logger.exception(f"查看 url 内容失败: {ex}")
        return f"[查看文件失败: {ex}]"

async def read_webpage(
    url: str,
    timeout: int = 20,
    return_format: str = "markdown",
    no_cache: bool = False,
    retain_images: bool = True,
):
    """读取并解析指定 url 的网页内容，返回网页正文（默认 markdown）。

    作为 AI 可调用 tool 使用：AI 传入 url 与可选参数，调用智谱「网页阅读」工具 API
    （POST /paas/v4/reader），返回网页解析后的主要内容。
    """
    if timeout > 100:
        return f"[网页阅读：timeout 值不能大于 100 秒]"
    try:
        result = await glm_api_request(
            "/paas/v4/reader",
            url=url,
            timeout=timeout,
            return_format=return_format,
            no_cache=no_cache,
            retain_images=retain_images,
        )
        if not isinstance(result, dict) or "reader_result" not in result:
            err = result.get("error") if isinstance(result, dict) else None
            if isinstance(err, dict):
                # 上游阅读服务的错误（如网络错误）：去掉无用的错误 id，附上替代方案
                reason = str(err.get("message") or "未知错误").split("，错误id")[0]
                logger.warning(f"网页阅读服务报错: {err}")
                return (f"[网页阅读失败：阅读服务暂时不可用（{reason}）；"
                        "可稍后重试，或改用 web_search / download 获取内容]")
            return f"[网页阅读失败: {result}]"
        reader_result = result.get("reader_result", {}) or {}
        content = reader_result.get("content", "")
        description = reader_result.get("description", "")
        if not reader_result:
            return "[网页内容为空或无法解析]"
        # 计费 tokens 到 credits（接口不返回用量，按内容长度估算）
        # if agent is not None:
            # agent.other_credits += len(content) / CHARS_PER_TOKEN
        title = reader_result.get("title", "")
        return f"{('【' + title + '】') if title else ''}{description}\n{content}" if title else content
        # return reader_result
    except Exception as ex:
        logger.exception(f"网页阅读失败: {ex}")
        return f"[网页阅读失败: {ex}]"


async def screenshot_page(url: str = "", ref: str = "", width: int = 1280, height: int = 800, wait_ms: int = 1000, prompt: str = "", agent=None):
    """对网页/SVG/HTML 做内部预览截图：存入 data/images/temp 并返回限时 url 给 AI。

    url 与 ref 二选一（url 为公网地址，ref 为已下载的 svg/html 引用）；
    wait_ms 控制动态内容的等待时间。prompt 非空时截图会直接交给 GLM 视觉模型
    按 prompt 分析并返回分析文本（等价于截图后自行调用 view_image）。
    """
    if bool(url) == bool(ref):
        return "[截图失败：url 与 ref 二选一]"
    width = min(max(int(width), 100), 3840)
    height = min(max(int(height), 100), 3840)
    wait_ms = min(max(int(wait_ms), 0), 15000)
    if ref:
        try:
            p = Path(agent.resolve_ref(ref))
        except KeyError:
            return "[截图失败：没有找到引用 {0}]".format(ref)
        if not p.is_file():
            return "[截图失败：引用 {0} 指向的文件不存在]".format(ref)
        source = p.resolve().as_uri()  # 本地 svg/html 直接渲染，无 SSRF 面
    else:
        source = html.unescape((url or "").strip())
        if urlparse(source).scheme not in ("http", "https"):
            return "[截图失败：url 需要以 http:// 或 https:// 开头]"
        try:
            assert_public_http_url(source)  # 拒绝本机/内网/元数据目标
        except ValueError as ex:
            return f"[截图失败：{ex}]"
    try:
        png = await chrome_screenshot_bytes(source, width=width, height=height,
                                            wait_ms=wait_ms, timeout_secs=45.0)
    except ValueError as ex:
        return f"[截图失败：{ex}]"
    except Exception as ex:
        logger.exception(f"截图失败 {source}")
        return f"[截图失败：{exception_detail(ex)}]"
    # 存入图片缓存目录，生成限时 url 供 GLM 读取（直链不作为文本暴露给模型）
    image_dir = Path(IMAGE_TEMP_PATH)
    image_dir.mkdir(parents=True, exist_ok=True)
    png_path = image_dir / f"screenshot-{uuid4().hex}.png"
    png_path.write_bytes(png)
    file_url = get_local_file_url(str(png_path))
    prompt = (prompt or "").strip()
    if not prompt:
        # 无分析需求：不暴露直链，登记 temp 引用供后续 view_image(ref) 使用
        ref = ""
        try:
            res = bytes_to_file(png, agent.user_id, ".png", agent)
            ref = res["ref"]
        except FileExistsError as ex:
            # 同内容截图已存在：反查既有引用复用，不产生第二个引用
            ref = next((r for r, name in agent.ref_map.items() if name == str(ex)), "")
        return (f"截图完成（{width}x{height}），已保存到 temp（引用 {ref}）。\n"
                f"需要分析内容时可用 view_image 传入该引用。")
    # 视觉轮直注入：截图直接进当前对话，不再单独调 view_item 分析
    if agent is not None and getattr(agent, "current_vision", False):
        return ImageToolResult(
            f"截图完成（{width}x{height}），截图已直接附在输入中。请针对该截图完成：{prompt}",
            [{"type": "image_url", "image_url": {"url": file_url}}])
    analysis = await view_item(url=file_url, prompt=prompt, item_type="image_url", agent=agent)
    return f"[对截图（{width}x{height}）的分析结果]\n{analysis}"
