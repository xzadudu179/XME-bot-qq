# some are made by Deepseek-v4-flash-vison-exp at Deepseek Harness
from pathlib import Path
import random
import time
import traceback
import functools

from nonebot import MessageSegment

from nonebot.log import logger
from xme.xmetools.filetools import search_json, search_text, history_file_name, safe_join, dir_usage, text_to_file
from .session import AISession
from xme.xmetools.dicttools import reverse_dict
from xme.xmetools.imgtools import get_url_image, image_to_base64, limit_size
from xme.xmetools.reqtools import glm_api_request
from xme.xmetools.texttools import regex_filter, regex_filter_text
from xme.xmetools.timetools import TELIA_CLOCK
from zai import ZhipuAiClient
from keys import GLM_API_KEY, TAVILY_API_KEY
from typing import Literal
from tavily import AsyncTavilyClient
from xme.xmetools.msgtools import create_image_message, send_session_msg
from character import get_message
import asyncio
from .constants import HISTORY_MAX_FILES, HISTORY_MAX_SIZE

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
    "view_file",
    "view_image",
    "view_video",
    "read_webpage",
    "web_search",
    "content_search",
    "get_webs_partial",
    "get_user_input_urls",
    "name_session",
    "dice"
]

# 低优先级 TODO: 给 AI 一个受限 python 沙箱（需要能防住卡死、rm -rf /*、等等攻击内容的完全受控制 python 沙箱，沙箱可以单独封装至 xmetools，并给 AI 提供一个工具，若能保证完全安全，以后还能给用户使用（但是要加很多限制，比如性能方面的各种还有防注入和突破限制。

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
            agent.other_credits += 80000
        image_msg = await get_image_msg(response.data[0].url)
        return image_msg
    except Exception as e:
        logger.exception(f"图片生成失败: {e}")
        return f"[图片生成失败: {e}]"

def content_search(param, file_ref, search_method: Literal["re_search", "re_filter"] = "re_search", agent=None):
    path = agent.resolve_ref(file_ref)
    method = None
    search_methods = {
        # "re_search": regex_search,
        "re_search": None,
        "re_filter": regex_filter_text,
        # "fuzzy_match": None,
    }
    method = search_methods.get(search_method, None)
    return {"result": "\n".join([f"{i + 1}. {c}" for i, c in enumerate(search_text(param, path, search_func=method))]), "no_compress": True}


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

async def view_file(url: str, prompt: str, agent):
    return await view_item(url, prompt, item_type="file", agent=agent)

async def view_video(url: str, prompt: str, agent):
    return await view_item(url, prompt, item_type="video_url", agent=agent)

async def view_image(url: str, prompt: str, agent):
    return await view_item(url, prompt, item_type="image_url", agent=agent)

async def view_item(url: str, prompt: str, item_type: str, agent=None):
    """调用 glm-5.3-flash 查看 url 里的内容，并按用户 prompt 回答。

    作为 AI 可调用 tool 使用：AI 传入 url 和 prompt，本函数使用 glm-5.3-flash
    查看该 url 的内容（图片/视频/文件等），并将模型解读结果返回给 AI。
    模型消耗的 tokens 会通过 agent 计入用户 credits。
    """
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
    """获取保存进用户 temp 的文件的内容。"""
    path = agent.resolve_ref(ref)
    lines = []
    with open(path, "r", encoding="utf-8") as file:
        lines = file.readlines()
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
            f"# history 占用：{usage['count']} 个文件 / {usage['size']:,} B（上限 {HISTORY_MAX_FILES} 个 / {HISTORY_MAX_SIZE:,} B ≈ {HISTORY_MAX_SIZE // 1024 // 1024} MB）"
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
        return f"[无效的引用名：{ref}]"
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
    usage = dir_usage(agent.get_history_path())
    cur_size = path.stat().st_size if path.exists() else 0
    est_size = usage["size"] - cur_size + len(content.encode("utf-8"))
    if not path.exists() and usage["count"] >= HISTORY_MAX_FILES:
        return {"result": f"[history 已满（{usage['count']} 个文件 ≥ 上限 {HISTORY_MAX_FILES} 个，共 {usage['size']:,} B）。请先用 delete_history_file / clear_history_files 清理或覆盖已有文件]", "no_compress": True}
    if est_size > HISTORY_MAX_SIZE:
        return {"result": f"[history 将超限：当前 {usage['size']:,} B，本次预计 {est_size:,} B，超过上限 {HISTORY_MAX_SIZE:,} B（{HISTORY_MAX_SIZE // 1024 // 1024} MB）。请先清理部分文件]", "no_compress": True}
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
    ref: 来源文件引用（temp 的 text_N/json_N 或已有历史引用）
    history_ref: 可选，保存时自定义名（history_N 或安全自定义名如 笔记.md）；不填自动分配 history_N；已存在会报错。
    """
    try:
        src_path = agent.resolve_ref(ref)
    except KeyError:
        return {"result": f"[转存失败：没有找到引用 {ref}]", "no_compress": True}
    with open(src_path, "r", encoding="utf-8") as f:
        text = f.read()
    if not text:
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
