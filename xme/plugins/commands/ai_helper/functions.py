# some are made by Deepseek-v4-flash-vison-exp at Deepseek Harness
from pathlib import Path
import html
import mimetypes
import random
import re
import time
import traceback
import functools
from urllib.parse import urlparse
from uuid import uuid4

from config import CONTAINER_BOT_PATH
from nonebot import MessageSegment

from nonebot.log import logger
from xme.xmetools.filetools import (
    bytes_to_file,
    decode_text,
    detect_file_type,
    get_local_file_url,
    search_json,
    history_file_name,
    safe_join,
    dir_usage,
    text_to_file,
    FileType,
    to_container_path,
)
from xme.xmetools.videotools.probe import get_video_duration
from xme.xmetools.bottools import bot_call_action
from .session import AISession
from xme.xmetools.dicttools import reverse_dict
from xme.xmetools.imgtools import get_url_image, image_to_base64, limit_size
from xme.xmetools.reqtools import fetch_file_stream, glm_api_request
from xme.xmetools.texttools import regex_filter
from xme.xmetools.timetools import TELIA_CLOCK
from zai import ZhipuAiClient
from keys import GLM_API_KEY, TAVILY_API_KEY
from typing import Literal
from tavily import AsyncTavilyClient
from xme.xmetools.msgtools import aget_arg_with_timeout, create_image_message, send_session_msg, is_text_can_send
from character import get_message
import asyncio
from .constants import HISTORY_MAX_FILES, HISTORY_MAX_SIZE, IMAGE_GEN_CREDITS, MAX_DOWNLOAD_FILE_SIZE

# AI 用到的函数名列表，需要与实际定义的函数名相符
__tools__ = [
    "get_telia_clock_state",
    "gen_image",
    "get_skill_md",
    "check_file",
    "list_files",
    "save_to_history",
    "find_history_file",
    "write_to_history",
    "write_to_temp",
    "delete_history_file",
    "rename_history_file",
    "clear_history_files",
    "inprocess_report",
    "ocr_image",
    "view_document_file",
    "view_image",
    "view_video",
    "read_webpage",
    "web_search",
    "content_search",
    "get_webs_partial",
    "get_user_input_urls",
    "download",
    "send_file",
    "edit_file",
    "name_session",
    "dice",
    "ask_user"
]

# 低优先级 TODO: 给 AI 一个受限 python 沙箱（需要能防住卡死、rm -rf /*、等等攻击内容的完全受控制 python 沙箱，沙箱可以单独封装至 xmetools，并给 AI 提供一个工具，若能保证完全安全，以后还能给用户使用（但是要加很多限制，比如性能方面的各种还有防注入和突破限制。


# detect_file_type 的文件类别 → 默认扩展名（URL 与 Content-Type 都无法识别时兜底）
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


def _exception_detail(ex: BaseException) -> str:
    """异常的可读描述：始终带类型名；str() 失败或为空（如 TimeoutError）时退化为类型名/repr。"""
    try:
        msg = str(ex).strip()
    except Exception:
        msg = ""
    return f"{type(ex).__name__}: {msg}" if msg else type(ex).__name__

async def ask_user(prompt: str, session, timeout: int = 120):
    from .agent import AISTOP
    from . import __plugin_name__
    send_time = time.time()
    if timeout > 400:
        timeout = 400
    interval = 0
    islegal = False
    while interval < 3 and not islegal:
        reply = await aget_arg_with_timeout(session, timeout_secs=timeout, prompt=get_message("plugins", __plugin_name__, "ai_ask", prompt=prompt, timeout=timeout))
        reply_time = time.time()
        interval = reply_time - send_time
        if interval < 3:
            await send_session_msg(session, get_message("plugins", __plugin_name__, "reply_too_fast"))
            continue
        islegal = await is_text_can_send(session, reply, 4)
        if not islegal:
            await send_session_msg(session, get_message("plugins", __plugin_name__, "reply_is_illegal"))
            continue
    if not reply:
        return "[用户未在时限内回复任何内容]"
    if reply == "aistop":
        return AISTOP
    await send_session_msg(session, get_message("plugins", __plugin_name__, "user_content_reply"))
    return f"[用户回复] {reply}"

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
    except Exception as ex:
        logger.exception(f"下载 {url} 失败")
        return f"[下载失败：{_exception_detail(ex)}]"
    if not data:
        return "[下载失败：文件为空]"

    # 先落盘探测类型：扩展名（URL → Content-Type → detect_file_type）+ 文本转 utf-8
    probe = agent.get_temp_path() / f"{uuid4().hex}.part"
    probe.write_bytes(data)
    suffix = _url_suffix(url)
    if not suffix:
        main_type = content_type.split(";")[0].strip().lower()
        guessed = mimetypes.guess_extension(main_type, strict=False) if main_type else None
        suffix = guessed if guessed and main_type != "application/octet-stream" else ""
    if not suffix:
        suffix = _TYPE_EXTENSIONS.get(detect_file_type(probe), ".bin")
    if detect_file_type(probe) == FileType.TEXT:
        data = decode_text(data).encode("utf-8")
    probe.unlink(missing_ok=True)

    try:
        res = bytes_to_file(data, agent.user_id, suffix, agent)
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


async def send_file(ref: str, agent):
    """把 ref 指向的文件（temp/history 均可）以私聊文件消息发送给当前用户。"""
    try:
        path = Path(agent.resolve_ref(ref))
    except KeyError:
        return {"result": f"[发送失败：没有找到引用 {ref}]", "no_compress": True}
    path = path.resolve()
    if not path.is_file():
        return {"result": f"[发送失败：引用 {ref} 指向的文件不存在]", "no_compress": True}
    if path.stat().st_size == 0:
        return {"result": "[发送失败：文件为空]", "no_compress": True}
    session = agent.session
    if session is None or getattr(session, "bot", None) is None:
        return {"result": "[发送失败：无法获取会话上下文]", "no_compress": True}
    try:
        await bot_call_action(
            session.bot, "upload_private_file",
            user_id=session.event.user_id,
            file=str(to_container_path(path)),
            name=path.name
        )
    except Exception as ex:
        logger.exception(f"私聊发送文件失败: {path}")
        return {"result": f"[发送失败：{_exception_detail(ex)}]",
                "no_compress": True}
    return {"result": f"已把文件 {path.name}（{path.stat().st_size} 字节）通过私聊发送给用户。",
            "file_name": path.name, "no_compress": True}


def edit_file(ref: str, content: str = "", line_start: int = 1, line_end: int = 0, agent=None):
    """按行改写文本文件（temp/history 通用）。

    把第 line_start ~ line_end 行（1 起算、含端点）替换为 content：
    - line_end 为 0 或缺省 = 只改 line_start 一行；
    - content 为空串 = 删除这些行；
    - line_start 大于总行数 = 在文件末尾追加（忽略 line_end）。
    仅支持文本文件；行号可来自 content_search 的结果。
    """
    content = content or ""
    if len(content) > 100000:
        return {"result": "[改写失败：新内容过长 (>100000 字)]", "no_compress": True}
    try:
        path = Path(agent.resolve_ref(ref))
    except KeyError:
        return {"result": f"[改写失败：没有找到引用 {ref}]", "no_compress": True}
    if not path.is_file():
        return {"result": f"[改写失败：引用 {ref} 指向的文件不存在]", "no_compress": True}
    if detect_file_type(path) != FileType.TEXT:
        return {"result": "[改写失败：该文件不是文本文件]", "no_compress": True}
    line_start = int(line_start)
    line_end = int(line_end)
    if line_start < 1:
        return {"result": "[改写失败：line_start 从 1 开始]", "no_compress": True}
    raw = decode_text(path.read_bytes())
    lines = raw.splitlines()
    trailing_newline = raw.endswith("\n") or not lines
    if line_start > len(lines):
        # 追加模式：追加到文件末尾
        new_lines = lines + content.splitlines()
        changed_at = len(lines) + 1
    else:
        end = line_start if line_end in (0, None) else line_end
        if end < line_start:
            return {"result": f"[改写失败：line_end({end}) 不能小于 line_start({line_start})]", "no_compress": True}
        end = min(end, len(lines))
        new_part = content.splitlines() if content else []
        new_lines = lines[:line_start - 1] + new_part + lines[end:]
        changed_at = line_start
    new_text = "\n".join(new_lines) + ("\n" if new_lines and (trailing_newline or content) else "")
    # 若目标是 history 文件，写入前检查其资源上限
    try:
        if Path(path).is_relative_to(agent.get_history_path().resolve()):
            quota_error = _check_history_quota(path, len(new_text.encode("utf-8")), agent)
            if quota_error:
                return {"result": quota_error, "no_compress": True}
    except (AttributeError, ValueError):
        pass
    path.write_text(new_text, encoding="utf-8")
    preview = "\n".join(
        f"{i}: {line}" for i, line in
        enumerate(new_lines[max(0, changed_at - 2): changed_at + 3], max(1, changed_at - 1))
    )
    return {"result": (f"已改写 {ref} 第 {changed_at} 行附近（现共 {len(new_lines)} 行），"
                       f"可再次用 content_search / check_file 确认。改后局部：\n{preview}"),
            "no_compress": True}


def get_user_input_urls(agent):
    return agent.user_input_urls

def dice(faces: int, count: int = 1):
    if count > 100:
        return "[骰子数量不能大于 100 个]"
    if faces > 1000000:
        return "[骰子面数不能大于 1000000]"
    rs = [random.randint(1, faces) for _ in range(count)]
    rs_str = ', '.join(map(str, rs))
    return f"{count}d{faces} → (总计{sum(rs)}) {rs_str}"

def name_session(name: str, agent=None):
    """为当前 AI 会话命名/重命名（会话名会显示在用户的会话列表中）。

    适合在对话主题明确时调用，例如讨论写小说的对话可命名为 "小说写作"。
    当前是共享会话时只改显示标题（群号码/目录不变，普通/群主同名规则见 share.py）；
    当前是默认会话时会把默认会话的内容整体提升为命名会话，默认会话复位为空；
    当前已有名字时直接重命名（历史与转存文件会一并移动）。
    用户手动命名过的会话不可修改（会返回错误）。
    """
    if agent is None:
        return "[错误：无法获取当前会话上下文]"
    name = (name or "").strip()
    # 共享会话：目录以群号码命名，改名只更新 meta 的 title 展示字段
    shared = getattr(agent, "shared", None)
    if shared is not None:
        if shared.rename(name):
            return f"[已将共享会话 {shared.code} 改名为 \"{shared.title}\"（只改显示标题，不影响群号码）]"
        return "[重命名失败：标题需为 1-20 字符且不含特殊符号，请换一个名字]"
    old_name = agent.ai_session
    name = name.replace(" ", "_")
    if not AISession.is_valid_name(name):
        return "[错误：会话名不合法。请控制在 20 字符以内，使用中英文/数字/_-（不以点开头、不含特殊符号），且不能叫 default 或以 history_ 开头]"
    session_obj = AISession(agent.user_id, old_name)
    if session_obj.is_locked():
        return "[错误：当前会话的名字由用户手动指定，AI 不可修改。请不要再重命名该会话]"
    # 旧目录要在 rename 之前捕获（rename 会就地改变 session_obj.ai_session）
    old_dir = session_obj.dir_path
    if session_obj.is_default:
        new_session = AISession.promote_default(agent.user_id, name)
    else:
        new_session = session_obj if session_obj.rename(name) else None
    if new_session is None:
        return f"[重命名失败：目标名 \"{name}\" 可能已被使用，请换一个名字]"
    # 会话目录可能整体移动，ref_map 里指向旧目录的路径同步更新
    new_dir = new_session.dir_path
    for ref, path in list(agent.ref_map.items()):
        p = Path(path)
        if old_dir in p.parents:
            agent.ref_map[ref] = str(new_dir / p.relative_to(old_dir))
    agent.ai_session = new_session.ai_session
    return f"[已为当前会话命名 \"{new_session.ai_session}\"（原 \"{old_name}\"）]"


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

async def inprocess_report(message: str, agent):
    from .constants import __plugin_name__
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
            agent.other_credits += IMAGE_GEN_CREDITS
        image_msg = await get_image_msg(response.data[0].url)
        return image_msg
    except Exception as e:
        logger.exception(f"图片生成失败: {e}")
        return f"[图片生成失败: {e}]"

def content_search(param, file_ref, search_method: Literal["re_search", "re_filter", "by_line"] = "re_search", agent=None):
    """按 search_method 搜索文件内容，所有模式的结果统一为「行号: 内容」（1 起算，可配合 edit_file 精确改写）。

    - re_search（默认）：param 作为正则在全文查找，返回每个匹配片段及其所在行号；
    - re_filter：param 作为正则分隔全文（re.split 语义），返回各匹配之间的间隙内容；
    - by_line：param 作为普通子串逐行匹配，返回包含该子串的整行。
    超过 100 条截断。
    """
    path = agent.resolve_ref(file_ref)
    text = decode_text(Path(path).read_bytes())
    cap = 100
    hits: list[str] = []

    if search_method == "by_line":
        hits = [f"{line_no}: {line[:8000] + '...' if len(line) > 8000 else line}"
                for line_no, line in enumerate(text.splitlines(), 1)
                if param in line]
    elif search_method in ("re_search", "re_filter"):
        try:
            pattern = re.compile(param)
        except re.error as ex:
            return {"result": f"[搜索失败：正则不合法（{ex}）；子串匹配请改用 by_line 模式]", "no_compress": True}

        def line_at(pos: int) -> int:
            return text.count("\n", 0, pos) + 1

        def flatten(base: int, segment: str) -> None:
            """把一段内容按行拆开，逐行带上各自的行号。

            segment 若从某行中间开始（上一个匹配吃掉了行首），其首个空尾巴行
            （匹配后剩余为空）是噪音，跳过；真实存在的空行照常返回。
            """
            at_line_start = base == 0 or text[base - 1] == "\n"
            for line in segment.splitlines():
                if not at_line_start and line == "":
                    base += 1  # 剩余为空的行尾巴，跳过
                    at_line_start = True
                    continue
                shown = line[:8000] + "..." if len(line) > 8000 else line
                hits.append(f"{line_at(base)}: {shown}")
                base += len(line) + 1  # +1 为换行符
                at_line_start = True

        if search_method == "re_search":
            for m in pattern.finditer(text):
                if m.group(0):
                    hits.append(f"{line_at(m.start())}: {m.group(0)}")
                if len(hits) >= cap:
                    break
        else:  # re_filter：与 re.split 语义一致，取匹配之间的间隙，逐行带行号
            last_end = 0
            for m in pattern.finditer(text):
                if m.end() > m.start():
                    flatten(last_end, text[last_end:m.start()])
                    last_end = m.end()
                if len(hits) >= cap:
                    break
            if len(hits) < cap:
                flatten(last_end, text[last_end:])
    else:
        return {"result": f"[无效的 search_method：{search_method}（可选 re_search / re_filter / by_line）]",
                "no_compress": True}

    if len(hits) >= cap:
        hits.append("…（命中过多，仅显示前 100 条，请缩小搜索范围）")
    if not hits:
        return {"result": f"[未找到匹配 \"{param}\" 的内容]", "no_compress": True}
    return {"result": "\n".join(hits), "no_compress": True}


def get_webs_partial(key, file_ref, search_str, search_method: Literal["re_search", "re_filter"] = "re_search", agent=None):
    path = agent.resolve_ref(file_ref)
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

async def view_document_file(ref: str, url: str, prompt: str, agent):
    return await view_item(ref, url, prompt, item_type="file", agent=agent)

async def view_video(ref: str, url: str, prompt: str, agent):
    path_or_url = url
    if ref:
        path_or_url = agent.resolve_ref(ref)
    dur = await get_video_duration(path_or_url)
    if not dur:
        return "[查看视频错误：无法解析视频文件时长]"
    if dur > 600:
        return "[查看视频错误：视频时长过长 (>10分钟)]"
    return await view_item(ref, url, prompt, item_type="video_url", agent=agent)

async def view_image(ref: str, url: str, prompt: str, agent):
    return await view_item(ref, url, prompt, item_type="image_url", agent=agent)

async def view_item(ref: str = "", url: str ="", prompt: str ="", item_type: str ="", agent=None):
    """调用 glm-5.3-flash 查看 url 里的内容，并按用户 prompt 回答。

    作为 AI 可调用 tool 使用：AI 传入 url 和 prompt，本函数使用 glm-5.3-flash
    查看该 url 的内容（图片/视频/文件等），并将模型解读结果返回给 AI。
    模型消耗的 tokens 会通过 agent 计入用户 credits。
    """
    if ref:
        url = get_local_file_url(agent.resolve_ref(ref))
    if not url:
        return "[分析 url 内容错误：ref 与 url 均无内容]"
    client = ZhipuAiClient(api_key=GLM_API_KEY)
    system_prompt = (
        "你是一个用于查看并解析指定 url 内容的模型。"
        "请根据用户给出的 prompt，仔细查看 url 里的内容并回答。"
        "如果内容是一张图片或视频，描述/分析其内容；如果是文件，提取并总结关键信息。"
        "输出应当准确、简洁、直接，不要编造图片或文本里不存在的内容。"
    )
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
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": item_type, item_type: {name: url}},
        ]},
    ]
    try:
        response = await asyncio.to_thread(
            client.chat.asyncCompletions.create,
            model="glm-5.3-flash",
            messages=messages,
            temperature=0.3,
        )
        task_id = response.id
        MAX_TRY_TIMES = 500
        try_times = 0
        while try_times < MAX_TRY_TIMES:
            try_times += 1
            result = await asyncio.to_thread(
                client.chat.asyncCompletions.retrieve_completion_result,
                id=task_id,
            )
            if result.task_status == "SUCCESS":
                break
            if result.task_status == "FAIL":
                raise RuntimeError("view_file 模型任务失败")
            await asyncio.sleep(0.5)
        # 计费 tokens 到 credits（跟随会话模型倍率折算）
        if agent is not None:
            agent.other_credits += result.usage.total_tokens - (result.usage.prompt_tokens_details.cached_tokens * 0.75)
        content = result.choices[0].message.content
        return content if content else "[没有识别到内容]"
    except Exception as ex:
        logger.exception(f"查看 url 内容失败: {ex}")
        return f"[查看文件失败: {ex}]"

GLM_API_BASE = "https://open.bigmodel.cn/api"

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


def check_file(ref: str, line_start=0, line_end=0, length=0, agent=None):
    """获取保存进用户 temp 的文本文件的内容。"""
    path = agent.resolve_ref(ref)
    if detect_file_type(path) != FileType.TEXT:
        return f"[该文件不是文本文件]"
    lines = []
    try:
        with open(path, "r", encoding="utf-8") as file:
            lines = file.readlines()
    except UnicodeDecodeError:
        return f"[文件无法以 utf-8 编码打开]"
    get_lines = lines[line_start:line_end] if line_end != 0 else lines[line_start:]
    out = "\n".join([f'{i}: {l}' for i, l in enumerate(get_lines)])
    out = out if length == 0 else out[:length]
    if len(out) > 20000:
        return out[:20000] + "\n[输出达到最大 20000 字，剩下请配置参数继续查看。]"
    return {"result": out, "no_compress": True}

def list_files(folder="temp", agent=None):
    """列出指定文件夹（temp / history）下的文件列表。"""
    if folder == "history":
        hist_path: Path = agent.get_history_path()
        usage = dir_usage(hist_path)
        files = sorted(
            [f for f in hist_path.iterdir() if f.is_file()],
            key=lambda f: f.name,
        )
        lines = [
            f"# history 占用：{usage['count']} 个文件 / {usage['size']:,} B（上限 {HISTORY_MAX_FILES} 个 / {HISTORY_MAX_SIZE:,} B ≈ {HISTORY_MAX_SIZE // 1024 // 1024} MiB）"
        ]
        for f in files:
            # history_<数字>.tmp → ref 取 stem；其他自定义文件 → ref 取文件名
            if f.name == f"{f.stem}.tmp" and f.stem.startswith("history_"):
                ref = f.stem
            else:
                ref = f.name
            agent.ref_map[ref] = str(hist_path / f.name)
            # fsize = 0
            if f.stat().st_size is not None:
                fsize = f"{(f.stat().st_size / 1024):,.3f} KiB"
            else:
                fsize = "unknown"
            lines.append(f"{ref}: {f.name} | size: {fsize}")
        return "\n".join(lines)
    reversed_ref_map = reverse_dict(agent.ref_map)
    files = [f"{reversed_ref_map.get(f.name, None)}: {f.name} | size: {(f.stat().st_size / 1024):,.3f} KiB" for f in agent.get_temp_path().iterdir() if f.is_file()]
    return "\n".join(files)


def _history_file(ref: str, agent, register: bool = False):
    """统一解析历史文件引用：校验 + 得到 (ref, path)。

    所有历史文件操作（定位 / 写入 / 追加 / 删除 / 重命名 / 转存）都应通过
    本函数获取引用与路径，以保证引用格式校验、会话文件夹与 ref_map 注册行为一致。
    register=True 时会把引用注册到 agent.ref_map（供 check_file 等后续使用）。
    非法引用（非 history_<数字>，防路径穿越）返回 None。
    """
    file_name = history_file_name(ref)
    if file_name is None:
        return None
    path = safe_join(agent.get_history_path(), file_name)
    if register:
        agent.ref_map[ref] = str(path)
    return ref, path


def find_history_file(ref: str, agent=None):
    """定位某个历史文件，返回其信息（是否存在、路径、大小、内容预览等）。"""
    res = _history_file(ref, agent)
    if res is None:
        return {"result": f"[无效的历史文件引用：{ref}]", "no_compress": True}
    _, path = res
    info = {"ref": ref, "path": str(path), "exists": path.exists()}
    if path.exists():
        info["size"] = path.stat().st_size
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            text = ""
        info["chars"] = len(text)
        info["preview"] = text[:200]
    return info

def write_to_temp(content: str, ref: str = "", mode: str = "w", agent=None):
    filename = agent.ref_map.get(ref, None)
    if filename is None and ref != "":
        return f"[无效的引用名：{ref}（创建新文件请不要输入 ref）]"
    if filename is None:
        res = text_to_file(content, agent.user_id, agent)
        agent.ref_map[res["ref"]] = res["file_name"]
    else:
        path = agent.resolve_ref(ref, False)
        modes = {
            "w": "w",
            "a": "a",
        }
        if modes.get(mode) is None:
            return f"[无效的写入模式：{mode}，仅支持 w（覆盖）或 a（追加）]"
        with open(path, modes[mode], encoding="utf-8") as file:
            file.write(content)
        return f"[成功写入已存在的文件 \"{ref}\"]"
    return f"[成功写入文件，可使用 \"check_file\" 工具传入 `file_ref` 预览。数据如下]：\n{res}"


def _check_history_quota(path: Path, incoming_size: int, agent) -> str | None:
    """检查写入 path（大小 incoming_size 字节）是否超出 history 资源上限；超限返回错误文案，否则 None。"""
    usage = dir_usage(agent.get_history_path())
    cur_size = path.stat().st_size if path.exists() else 0
    est_size = usage["size"] - cur_size + incoming_size
    if not path.exists() and usage["count"] >= HISTORY_MAX_FILES:
        return f"[history 已满（{usage['count']} 个文件 ≥ 上限 {HISTORY_MAX_FILES} 个，共 {usage['size']:,} B）。请先用 delete_history_file / clear_history_files 清理或覆盖已有文件]"
    if est_size > HISTORY_MAX_SIZE:
        return f"[history 将超限：当前 {usage['size']:,} B，本次预计 {est_size:,} B，超过上限 {HISTORY_MAX_SIZE:,} B（{HISTORY_MAX_SIZE // 1024 // 1024} MiB）。请先清理部分文件]"
    return None


def write_to_history(ref: str, content: str = "", mode: str = "w", agent=None):
    """写入/覆盖/追加某个历史文件。

    mode 与 with open() 的写入语义一致：
        "w" 覆盖或新建（默认）；"a" 追加或新建（追加时自动补一个换行分隔）。
    """
    if len(content) > 100000:
        return "[写入失败：写入内容过长 (>100000 字)]"
    res = _history_file(ref, agent)
    if res is None:
        return {"result": f"[无效的历史文件引用：{ref}]", "no_compress": True}
    _, path = res
    if mode not in ("w", "a"):
        return {"result": f"[无效的写入模式：{mode}，仅支持 w（覆盖）或 a（追加）]", "no_compress": True}
    # 单会话 history 文件夹资源上限检查
    quota_error = _check_history_quota(path, len(content.encode("utf-8")), agent)
    if quota_error:
        return {"result": quota_error, "no_compress": True}
    ######
    try:
        if mode == "a" and path.exists():
            with open(path, "a", encoding="utf-8") as f:
                f.write(content)
        else:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
        agent.ref_map[ref] = str(path)
        op = "追加" if mode == "a" else "覆盖写入"
        return {
            "result": f"已{op}历史文件 {ref}（共 {len(content)} 字）",
            "ref": ref,
            "path": str(path),
            "no_compress": True,
        }
    except Exception as ex:
        logger.exception(f"写入历史文件失败: {ex}")
        return {"result": f"[写入失败：{ex}]", "no_compress": True}


def delete_history_file(ref: str, agent=None):
    """删除某个历史文件（history_N）。"""
    res = _history_file(ref, agent)
    if res is None:
        return {"result": f"[无效的历史文件引用：{ref}]", "no_compress": True}
    _, path = res
    if not path.exists():
        return {"result": f"[历史文件 {ref} 不存在]", "no_compress": True}
    try:
        path.unlink()
        agent.ref_map.pop(ref, None)
        return {"result": f"已删除历史文件 {ref}", "no_compress": True}
    except Exception as ex:
        return {"result": f"[删除失败：{ex}]", "no_compress": True}


def _next_history_ref(agent) -> str:
    """扫描会话文件夹，返回下一个可用的 history_N 引用。"""
    hist_path = agent.get_history_path()
    used = set()
    for item in hist_path.iterdir():
        if item.is_file() and item.name.endswith(".tmp"):
            stem = item.stem
            if stem.startswith("history_"):
                try:
                    used.add(int(stem[len("history_"):]))
                except ValueError:
                    pass
    n = 1
    while n in used:
        n += 1
    return f"history_{n}"


def rename_history_file(ref: str, new_ref: str = "", agent=None):
    """重命名一个历史文件。new_ref 为空时自动分配下一个可用的 history_N。
    """
    res_old = _history_file(ref, agent)
    if res_old is None:
        return {"result": f"[无效的历史文件引用：{ref}]", "no_compress": True}
    _, old_path = res_old
    if not old_path.exists():
        return {"result": f"[历史文件 {ref} 不存在]", "no_compress": True}
    if not new_ref:
        new_ref = _next_history_ref(agent)
    res_new = _history_file(new_ref, agent)
    if res_new is None:
        return {"result": f"[无效的新引用名：{new_ref}]", "no_compress": True}
    if new_ref == ref:
        return {"result": "[新引用与旧引用相同，无需重命名]", "no_compress": True}
    _, new_path = res_new
    if new_path.exists():
        return {"result": f"[目标引用 {new_ref} 已存在，请先删除或改名]", "no_compress": True}
    try:
        old_path.rename(new_path)
        agent.ref_map.pop(ref, None)
        agent.ref_map[new_ref] = str(new_path)
        return {
            "result": f"已重命名历史文件 {ref} -> {new_ref}",
            "ref": new_ref,
            "path": str(new_path),
            "no_compress": True,
        }
    except Exception as ex:
        logger.exception(f"重命名历史文件失败: {ex}")
        return {"result": f"[重命名失败：{ex}]", "no_compress": True}


def save_to_history(ref, history_ref="", agent=None):
    """转存文件到 history 文件夹，生成引用。
    ref: 来源文件引用（temp 的 file_N/text_N/json_N 或已有历史引用）。
    文本文件按文本转存（走 write_to_history）；图片/PDF/压缩包等二进制按
    原始字节转存并保留原扩展名。
    history_ref: 可选，保存时自定义名（history_N 或安全自定义名如 笔记.md）；不填自动分配 history_N；已存在会报错。
    """
    try:
        src_path = agent.resolve_ref(ref)
    except KeyError:
        return {"result": f"[转存失败：没有找到引用 {ref}]", "no_compress": True}
    src_path = Path(src_path)
    if not src_path.exists():
        return {"result": f"[转存失败：引用 {ref} 指向的文件不存在]", "no_compress": True}
    data = src_path.read_bytes()
    if not data:
        return {"result": "[转存失败：没有内容可保存]", "no_compress": True}
    # 自定义名：统一校验 + 防重名
    if history_ref:
        res = _history_file(history_ref, agent)
        if res is None:
            return {"result": f"[无效的历史文件引用名：{history_ref}]（仅支持 history_N 或安全自定义名）", "no_compress": True}
        _, target = res
        if target.exists():
            return {"result": f"[历史文件 {history_ref} 已存在，请换名或先 delete_history_file]", "no_compress": True}
        ref_id = history_ref
    else:
        ref_id = _next_history_ref(agent)
    # 二进制文件：按原始字节转存，保留来源扩展名（文本文件仍走 write_to_history）
    if detect_file_type(src_path) != FileType.TEXT:
        if not history_ref:
            ref_id = ref_id + src_path.suffix.lower()  # 自动分配的 history_N 补上来源扩展名
        res = _history_file(ref_id, agent)
        if res is None:
            return {"result": f"[无效的历史文件引用名：{ref_id}]", "no_compress": True}
        _, target = res
        if target.exists():
            return {"result": f"[历史文件 {ref_id} 已存在，请换名或先 delete_history_file]", "no_compress": True}
        quota_error = _check_history_quota(target, len(data), agent)
        if quota_error:
            return {"result": quota_error, "no_compress": True}
        try:
            target.write_bytes(data)
        except Exception as ex:
            logger.exception(f"转存二进制文件失败: {ex}")
            return {"result": f"[转存失败：{ex}]", "no_compress": True}
        agent.ref_map[ref_id] = str(target)
        return {
            "result": f"已转存{detect_file_type(src_path).value}至 history，引用 {ref_id}（{len(data)} 字节）。可用 view_file / view_image / view_video 查看。",
            "ref": ref_id,
            "file_name": str(target),
            "size": len(data),
            "no_compress": True,
        }
    text = decode_text(data)
    result = write_to_history(ref_id, text, mode="w", agent=agent)
    if (result.get("result", "") or "").startswith("["):
        return result
    return {
        "result": f"已转存至 history，引用 {ref_id}，可通过 check_file 传入 \"{ref_id}\" 查看内容。",
        "ref": ref_id,
        "file_name": result.get("path", ""),
        "total_len": len(text),
        "preview": text[:200],
        "no_compress": True,
    }


def clear_history_files(agent=None):
    """清空 history 文件夹里的所有文件，并移除对应引用。"""
    hist_path = agent.get_history_path()
    removed = 0
    if hist_path.is_dir():
        for item in hist_path.iterdir():
            if item.is_file() or item.is_symlink():
                item.unlink()
                removed += 1
    agent.ref_map = {
        k: v for k, v in agent.ref_map.items()
        if not str(v).startswith("data/ai_historys/")
    }
    return {"result": f"已清空 history，共删除 {removed} 个文件", "no_compress": True}
