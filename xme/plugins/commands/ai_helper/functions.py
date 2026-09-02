from pathlib import Path
import time
import traceback

from nonebot import MessageSegment

from nonebot.log import logger
from xme.xmetools.filetools import search_json, search_text
from xme.xmetools.dicttools import reverse_dict
from xme.xmetools.imgtools import get_url_image, image_to_base64, limit_size
from xme.xmetools.reqtools import fetch_data_post
from xme.xmetools.texttools import regex_filter, regex_filter_text
from xme.xmetools.timetools import TELIA_CLOCK
from zai import ZhipuAiClient
from keys import GLM_API_KEY, TAVILY_API_KEY
from typing import Literal
from tavily import AsyncTavilyClient
from xme.xmetools.msgtools import create_image_message, send_session_msg
from character import get_message
import asyncio

# AI 用到的函数名列表，需要与实际定义的函数名相符
__tools__ = [
    "get_telia_clock_state",
    "gen_image",
    "get_skill_md",
    "check_file",
    "list_temp_files",
    "save_to_history",
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
    "get_user_input_urls"
]

def get_user_input_urls(agent):
    return agent.user_input_urls

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
    file_name = agent.resolve_ref(file_ref)
    path = agent.get_temp_path() / file_name
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
    file_name = agent.resolve_ref(file_ref)
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
            agent.other_credits += result.usage.total_tokens
        content = result.choices[0].message.content
        return content if content else "[没有识别到内容]"
    except Exception as ex:
        logger.exception(f"查看 url 内容失败: {ex}")
        return f"[查看文件失败: {ex}]"

READER_API_URL = "https://open.bigmodel.cn/api/paas/v4/reader"


# 目前不计费
# 网页阅读接口不返回 token 用量，这里按返回内容长度估算 token 用于计费（约 4 字符 ≈ 1 token）
# CHARS_PER_TOKEN = 4
async def read_webpage(
    url: str,
    timeout: int = 20,
    return_format: str = "markdown",
    no_cache: bool = False,
    retain_images: bool = True,
):
    """读取并解析指定 url 的网页内容，返回网页正文（默认 markdown）。

    作为 AI 可调用 tool 使用：AI 传入 url 与可选参数，调用智谱「网页阅读」工具 API
    （POST /paas/v4/reader），返回网页解析后的主要内容。按返回内容长度估算 tokens
    计入用户 credits。
    """
    import uuid
    if timeout > 100:
        return f"[网页阅读：timeout 值不能大于 100 秒]"
    headers = {"Authorization": f"Bearer {GLM_API_KEY}"}
    params = {
        "url": url,
        "timeout": timeout,
        "return_format": return_format,
        "no_cache": no_cache,
        "retain_images": retain_images,
        "request_id": str(uuid.uuid4()),
    }
    try:
        result = await fetch_data_post(READER_API_URL, json=params, headers=headers)
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


def check_file(ref: str, line_start=0, line_end=0, agent=None):
    """获取保存进用户 temp 的文件的内容。"""
    file_name = agent.resolve_ref(ref)
    lines = []
    with open(f"{agent.get_temp_path(True)}/{file_name}", "r", encoding="utf-8") as file:
        lines = file.readlines()
    get_lines = lines[line_start:line_end] if line_end != 0 else lines[line_start:]
    return {"result": "\n".join(get_lines), "no_compress": True}


def list_temp_files(folder="temp", agent=None):
    """列出指定文件夹（temp / history）下的文件列表。"""
    if folder == "history":
        hist_path = agent.get_history_path()
        files = sorted(
            [f for f in hist_path.iterdir() if f.is_file()],
            key=lambda f: f.name,
        )
        lines = []
        for f in files:
            ref = f.stem if f.stem.startswith("history_") else None
            if ref is None:
                continue
            agent.ref_map[ref] = f"history/{f.name}"
            lines.append(f"{ref}: {f.name}")
        return "\n".join(lines)
    reversed_ref_map = reverse_dict(agent.ref_map)
    files = [f"{reversed_ref_map.get(f.name, None)}: {f.name}" for f in agent.get_temp_path().iterdir() if f.is_file()]
    return "\n".join(files)


def save_to_history(ref="", content="", agent=None):
    """转存内容/文件到 history 文件夹，返回 history 引用信息。

    若传入 ref，则读取 temp 中对应文件的内容转存；否则使用 content 文本。
    history 文件以 history_N.tmp 命名，其引用 history_N 可由文件名推导，
    因此跨会话也能稳定复用。
    """
    if ref:
        file_name = agent.ref_map.get(ref, None)
        if file_name is None:
            return {"result": f"[转存失败：没有找到引用 {ref}]", "no_compress": True}
        src_path = agent.get_temp_path() / file_name
        with open(src_path, "r", encoding="utf-8") as f:
            text = f.read()
    else:
        text = content or ""
    if not text:
        return {"result": "[转存失败：没有内容可保存]", "no_compress": True}
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
    ref_id = f"history_{n}"
    file_name = f"{ref_id}.tmp"
    agent.ref_map[ref_id] = f"history/{file_name}"
    with open(hist_path / file_name, "w", encoding="utf-8") as f:
        f.write(text)
    return {
        "result": f"已转存至 history，引用 {ref_id}，可通过 check_file 传入 \"{ref_id}\" 查看内容。",
        "ref": ref_id,
        "file_name": f"history/{file_name}",
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
        if not str(v).startswith("history/")
    }
    return {"result": f"已清空 history，共删除 {removed} 个文件", "no_compress": True}
