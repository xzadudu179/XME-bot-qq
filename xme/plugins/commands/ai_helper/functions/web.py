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
from xme.xmetools.imgtools import chrome_screenshot_bytes, image_to_base64, limit_size, read_image, split_long_image
from xme.xmetools.bottools import bot_call_action
from ..constants import (MAX_DOWNLOAD_FILE_SIZE, SCREENSHOT_MAX_WAIT_MS,
                         SCREENSHOT_MAX_WAIT_UNTIL_MS, VIDEO_URL_TTL)
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
        if ex.status == 400:
            return ("[下载失败：HTTP 400——目标站点拒绝了该请求：部分站点的图片/文件只允许在网页内访问"
                    "（防盗链），或缩略图只接受固定尺寸参数。请换一个直链或换一个来源，"
                    "也可用 read_webpage 打开页面找可用的链接]")
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
    from ..search import SearchError, search_with_fallback
    try:
        resp = await search_with_fallback(query, max_results=max_results, time_range=time_range)
    except SearchError as ex:
        # 所有引擎都失败：明确告诉模型下一步怎么办，别让它反复重试同一个搜索
        return {"result": f"[搜索失败：{ex.message}。可改用 read_webpage 直接读取已知站点页面，"
                          f"或稍后再试；不要用同样的关键词反复重试]", "no_compress": True}
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

async def view_document_file(ref: str = "", url: str = "", prompt: str = "", attach=False, agent=None):
    return await view_item(ref, url, prompt, item_type="file", attach=attach, agent=agent)

async def view_video(ref: str = "", url: str = "", prompt: str = "", attach=False, agent=None):
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
        # 视频链接用更长的有效期：模型服务端要拉取数 MB 视频，30s 太紧
        url = get_local_file_url(str(result.file_paths[0]), ttl=VIDEO_URL_TTL)  # 合集只分析第一个视频
        return await view_item(url=url, prompt=prompt, item_type="video_url", attach=attach, agent=agent)
    path_or_url = agent.resolve_ref(ref) if ref else url
    dur = await get_video_duration(path_or_url)
    if not dur:
        return "[查看视频错误：无法解析视频文件时长]"
    if dur > 600:
        return "[查看视频错误：视频时长过长 (>10分钟)]"
    return await view_item(ref, url, prompt, item_type="video_url", attach=attach, agent=agent)

async def view_image(ref: str = "", url: str = "", prompt: str = "", attach=False, agent=None):
    return await view_item(ref, url, prompt, item_type="image_url", attach=attach, agent=agent)


# ---- 媒体可解析性探测（注入前校验，避免"声称已附上但模型实际加载失败"的误判）----

_MEDIA_PROBE_MAX_SIZE = 4 * 1024 * 1024  # 探测下载上限；超限属"无法判定"，按放行处理
_MEDIA_PROBE_HEAD = 64 * 1024            # 本地文件只读头部即可判定格式

# 独立模型分析结果的来源标注：告诉模型这是第三方结论、自己没亲眼看，
# 避免把别人的描述当成"我看过"（自查自己产出时尤其容易因此放过问题）
INDEPENDENT_ANALYSIS_NOTE = "（以下为独立视觉模型的分析结论，你本人并未直接查看该内容）\n"

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

async def view_item(ref: str = "", url: str ="", prompt: str ="", item_type: str ="", attach: bool = False, agent=None):
    """查看 url/ref 里的媒体内容并按 prompt 解析。

    默认交给独立模型分析（返回文本，中立第三方视角）；attach=True 时若本轮模型
    支持该媒体类型，则把内容直接附进当前对话由模型自己看（仅适合看别人的东西）。
    """
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
    # 默认交给独立模型分析（中立第三方），而不是直接附进当前对话自己看：
    # 自己看自己产出的东西容易带自证偏差（觉得没问题就没细看），
    # 只有明确要看"别人的东西"时才由调用方传 attach=True 直注入。
    # 能力按媒体类型判：视频段（video_url）只有 GLM 之类的端点接受，
    # 只支持图片的端点收下会 422，因此不能用同一个 vision 判据
    can_inject = agent is not None and attach \
        and getattr(agent, "supports_media", lambda _t: False)(item_type)
    if can_inject:
        type_names = {"file": "文件", "image_url": "图片", "video_url": "视频"}
        label = type_names.get(item_type, item_type)
        # 注入前探测：解析不了的媒体绝不谎称"已附上"，显式报告给模型
        probe_error = await _media_probe(url, item_type)
        if probe_error:
            return (f"[{label}无法解析，未附入输入：{probe_error}]"
                    f"（可让用户重新发送该{label}，或先下载到本地改用 ref 传入）")
        if item_type == "image_url":
            slice_urls = _long_image_slice_urls(url)
            if slice_urls and len(slice_urls) > 1:
                return ImageToolResult(
                    f"[图片内容已直接附在输入中（长图已自动分 {len(slice_urls)} 片，从上到下），"
                    f"请逐片查看后完成：{prompt}]",
                    [{"type": "image_url", "image_url": {"url": u}} for u in slice_urls])
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
    try:
        # 独立分析按媒体类型选模型：图片走 vision 能力，视频走 video 能力
        # （video_url 段只有 GLM 之类端点接受，用只支持图片的端点会直接 422）
        entry = registry.video_entry() if item_type == "video_url" else registry.vision_entry()
        provider = registry.get_provider(entry["provider"])
        if provider is None:
            return f"[查看文件失败：provider {entry['provider']} 未配置]"
        # 本地长图按方形分片逐片分析（整图会被视觉模型压缩成缩略图）；普通内容单目标
        targets = (_long_image_slice_urls(url) if item_type == "image_url" else None) or [url]
        texts, failed = [], []
        for i, target in enumerate(targets):
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": item_type, item_type: {name: target}},
                ]},
            ]
            try:
                result = await provider.chat(messages, model=entry["model"], temperature=0.3)
            except Exception as ex:
                # 单片失败不整体作废：已分析的片保留，失败片显式标注
                # （模型端回源拉图偶发失败，AI 可据此只重试缺失的片）
                flag = "限流" if getattr(ex, "kind", "") == "rate_limit" else type(ex).__name__
                failed.append(f"第 {i + 1} 片（{flag}: {str(ex)[:80]}）")
                continue
            # 计费 tokens 到 credits（带外调用，跟随会话模型倍率折算）
            if agent is not None:
                agent.other_credits += result.usage.billable_tokens(registry.cache_credit_ratio(entry))
            text = result.text or "[没有识别到内容]"
            texts.append(f"[第 {i + 1}/{len(targets)} 片（从上到下）]\n{text}"
                         if len(targets) > 1 else text)
        if failed:
            logger.warning(f"查看 url 内容部分分片失败: {'；'.join(failed)}")
        if not texts:
            return f"[查看文件失败：{'全部' if len(targets) > 1 else ''}分片分析失败（{'；'.join(failed)}）]"
        # 标注来源：让模型知道这是第三方分析结论、自己并未亲眼看过，
        # 避免它把别人的描述当成"我看过"（尤其自查自己产出时）
        missed = (f"[注意：{len(failed)} 片分析失败，结果缺少这些部分：{'；'.join(failed)}]\n"
                  if failed else "")
        return INDEPENDENT_ANALYSIS_NOTE + missed + "\n".join(texts)
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


def _cache_image_url(data: bytes, ext: str = ".png") -> str:
    """把图片字节写入限时 url 缓存目录并返回直链（供视觉模型读取，直链不作为文本暴露）。"""
    image_dir = Path(IMAGE_TEMP_PATH)
    image_dir.mkdir(parents=True, exist_ok=True)
    png_path = image_dir / f"screenshot-{uuid4().hex}{ext}"
    png_path.write_bytes(data)
    return get_local_file_url(str(png_path))


def _jpeg_view_bytes(data: bytes) -> bytes:
    """把图片字节编码成给视觉模型看的 JPEG（q88）。

    视觉模型要经公网回源拉取直链，大 PNG 实测频繁下载失败（DeepSeek 400
    media_invalid），同内容 JPEG 体积小一个数量级、拉取稳定；模型看图无需无损。
    """
    buf = io.BytesIO()
    with Image.open(io.BytesIO(data)) as img:
        img.load()
        img.convert("RGB").save(buf, format="JPEG", quality=88)
    return buf.getvalue()


def _long_image_slice_urls(url: str, max_slices: int = 8) -> list[str] | None:
    """图片 url 指向本地长图（高>宽）时切成方形分片，返回各分片限时 url；否则 None。

    只处理能反查到本地文件的 url（我们自己的 /file/ 限时直链，如截图缓存与
    temp 引用）；外链长图不下载、不分片。视觉模型按长边压缩整图，长图直接看
    会糊成缩略图，分片后每片都是方形清晰图。分片统一转 JPEG 提高模型端拉取成功率。
    """
    if not (url.startswith("http") and "/file/" in url and DOMAIN in url):
        return None
    token = url.split("/file/", 1)[1].split("?", 1)[0].strip("/")
    info = FILE_TOKENS.get(token)
    if not info:
        return None
    path = Path(info["path"])
    if not path.is_file():
        return None
    try:
        parts, (width, height) = split_long_image(path.read_bytes(), max_slices=max_slices)
        if height <= width:
            return None
        has_alpha = parts[0].mode in ("RGBA", "LA", "PA") or \
            (parts[0].mode == "P" and "transparency" in parts[0].info)
        urls = []
        for part in parts:
            buf = io.BytesIO()
            if has_alpha:
                part.save(buf, format="PNG")
                ext = ".png"
            else:
                part.convert("RGB").save(buf, format="JPEG", quality=88)
                ext = ".jpg"
            urls.append(_cache_image_url(buf.getvalue(), ext))
            part.close()
    except Exception as ex:
        logger.info(f"长图分片跳过（{ex}）：{path.name}")
        return None
    return urls


def wait_until_budget_s() -> float:
    """wait_until 条件轮询的时长上限（秒），仅用于给模型的提示文案。"""
    return SCREENSHOT_MAX_WAIT_UNTIL_MS / 1000


async def screenshot_page(url: str = "", ref: str = "", width: int = 1280, height: int = 800,
                          wait_ms: int = 1000, wait_until: str = "", prompt: str = "",
                          attach: bool = False, scale: int = 2, agent=None):
    """对网页/SVG/HTML 做内部预览截图：整图存入 temp 并返回引用给 AI。

    url 与 ref 二选一（url 为公网地址，ref 为已下载的 svg/html 引用）；
    等待是**真实墙钟**的，两者可一起用、顺序为「条件优先、wait_ms 作缓冲」：
    先轮询 wait_until（CSS 选择器或 JS 表达式，如加载动画消失的条件），
    条件满足后再额外等 wait_ms 让收尾动画/懒加载稳定；条件超时则跳过缓冲、
    照常截图并在结果里注明「条件未满足」，不静默假装页面已就绪。
    scale 为渲染倍率（默认 2，Retina 式物理分辨率翻倍——视觉模型会压缩大图，
    源越清晰压完越可读）。
    存储的始终是完整原图（发给用户/转存都用它）；页面较长（高>宽）时 view_image
    查看会自动分片逐片读取，AI 无需关心。
    prompt 非空时截图默认交给独立视觉模型按 prompt 分析并返回文本（中立视角；
    长图自动逐片分析拼接）；attach=True 且本轮模型支持图片输入时，
    才把截图（各分片）直接附进当前对话自己看（适合看别人的页面，不适合验收自己的产出）。
    """
    if bool(url) == bool(ref):
        return "[截图失败：url 与 ref 二选一]"
    width = min(max(int(width), 100), 3840)
    height = min(max(int(height), 100), 8192)
    scale = min(max(int(scale), 1), 2)
    wait_ms = min(max(int(wait_ms), 0), SCREENSHOT_MAX_WAIT_MS)
    wait_until = (wait_until or "").strip()
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
        outcome = await chrome_screenshot_bytes(source, width=width, height=height,
                                               wait_ms=wait_ms, timeout_secs=45.0,
                                               scale=scale, wait_until=wait_until)
    except ValueError as ex:
        return f"[截图失败：{ex}]"
    except Exception as ex:
        logger.exception(f"截图失败 {source}")
        return f"[截图失败：{exception_detail(ex)}]"
    png = outcome.png
    # 等待过程如实汇报：条件超时不等于失败，但要明确告诉模型"页面可能还没就绪"
    wait_note = ""
    if outcome.condition is False:
        wait_note = (f"\n（等待条件 {wait_until!r} 在 {wait_until_budget_s():g}s 内未满足："
                     f"页面可能仍处于加载/过渡状态，已按当前状态截图，"
                     f"不要把这张图当作「页面已就绪」的证据）")
    elif outcome.condition is True:
        wait_note = f"\n（等待条件 {wait_until!r} 已满足，等待 {outcome.waited_ms / 1000:.1f}s 后截图）"
    elif outcome.waited_ms > 0:
        wait_note = f"\n（页面加载完成后等待 {outcome.waited_ms / 1000:.1f}s 截图）"
    if outcome.via == "oneshot":
        wait_note += "（本次为降级截图路径：真实等待不可用，等待时长可能短于请求值）"
    with Image.open(io.BytesIO(png)) as img:
        phys_w, phys_h = img.size
    dims = f"{width}x{height}"
    if scale > 1:
        dims += f"，{scale}x 渲染（物理 {phys_w}x{phys_h}）"

    prompt = (prompt or "").strip()
    if not prompt:
        # 无分析需求：整图登记 temp 引用（唯一本体，发给用户/转存都用它）；
        # 长图的分片是查看动作（view_image 内处理），不落存储
        ref = ""
        try:
            ref = bytes_to_file(png, agent.user_id, ".png", agent)["ref"]
        except FileExistsError as ex:
            # 同内容截图已存在：反查既有引用复用，不产生第二个引用
            ref = next((r for r, name in agent.ref_map.items() if name == str(ex)), "")
        tail = ("页面较长，用 view_image 查看该引用时会自动分片逐片读取。"
                if phys_h > phys_w else "需要分析内容时可用 view_image 传入该引用。")
        return f"截图完成（{dims}），已保存到 temp（引用 {ref}）。{wait_note}\n{tail}"
    # 带 prompt：统一交给 view_item 分析（长图在查看时自动分片——attach 直附与
    # 独立分析两条路径行为与 view_image 完全一致，避免两处分片逻辑）；
    # 交给模型的缓存图转 JPEG：大 PNG 回源拉取实测频繁失败
    analysis = await view_item(url=_cache_image_url(_jpeg_view_bytes(png), ".jpg"),
                               prompt=prompt, item_type="image_url", attach=attach, agent=agent)
    if isinstance(analysis, ImageToolResult):
        return ImageToolResult(f"[截图完成（{dims}）]{wait_note}\n{analysis}", analysis.image_parts)
    return f"[对截图（{dims}）的分析结果]{wait_note}\n{analysis}"
