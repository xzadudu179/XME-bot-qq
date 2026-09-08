# some are made by Deepseek-v4-flash-vison-exp at Deepseek Harness
"""文件类工具：temp/history 的读写、搜索、改写、转存、发送与清理。"""
from pathlib import Path
import asyncio
import contextlib
import gzip
import json
import os
import re
import shutil
import sys
import tarfile
import zipfile
from typing import Literal
from uuid import uuid4

from nonebot.log import logger
from xme.xmetools.dicttools import reverse_dict
from xme.xmetools.filetools import (
    decode_text, detect_file_type, search_json, history_file_name,
    is_safe_custom_name, safe_join, dir_usage, FileType, text_to_file, to_container_path,
)
from xme.xmetools.texttools import regex_filter
from xme.xmetools.bottools import bot_call_action
from ..constants import (
    HISTORY_MAX_FILES, HISTORY_MAX_SIZE, MAX_ZIP_SIZE,
    MAX_SYNTAX_CHECK_SIZE, SYNTAX_CHECK_TIMEOUT,
    SYNTAX_CHECK_AS_LIMIT, SYNTAX_CHECK_AS_LIMIT_NODE,
    MAX_EXTRACT_FILES, MAX_EXTRACT_TOTAL_SIZE,
)
from ._common import exception_detail

async def send_file(ref: str, new_name="", agent=None):
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
    send_path = path
    if new_name and new_name != path.name:
        # new_name 仅作为展示文件名：校验安全后复制到通用临时目录再上传，
        # 防止路径穿越/绝对路径借 copy2 写到任意位置（is_safe_custom_name 拒绝 / 与 ..）
        if not is_safe_custom_name(new_name):
            return {"result": f"[发送失败：文件名 {new_name} 不合法（仅允许中英文/数字/_-.，不含路径）]",
                    "no_compress": True}
        temp_dir = Path("./data/temp")
        temp_dir.mkdir(parents=True, exist_ok=True)
        send_path = safe_join(temp_dir, new_name)
        try:
            shutil.copy2(path, send_path)
        except Exception as ex:
            logger.exception(f"准备发送文件失败: {path} -> {send_path}")
            return {"result": f"[发送失败：{exception_detail(ex)}]", "no_compress": True}
    try:
        await bot_call_action(
            session.bot, "upload_private_file",
            user_id=session.event.user_id,
            file=str(to_container_path(send_path)),
            name=send_path.name
        )
    except Exception as ex:
        logger.exception(f"私聊发送文件失败: {send_path}")
        return {"result": f"[发送失败：{exception_detail(ex)}]",
                "no_compress": True}
    finally:
        if send_path is not path:
            send_path.unlink(missing_ok=True)  # 副本用完即删，不残留通用临时目录
    return {"result": f"已把文件 {send_path.name}（{path.stat().st_size} 字节）通过私聊发送给用户。",
            "file_name": send_path.name, "no_compress": True}


def edit_file(ref: str, old_string: str, new_string: str, replace_all: bool = False, agent=None):
    """按精确文本匹配改写文件（temp/history 通用）。

    old_string 必须与文件内容逐字符一致（含缩进与换行），取自最近一次读取：
    - 找不到匹配 = 文件可能在读取后已变化，提示重新读取；
    - 匹配到多处且未 replace_all = 拒绝，要求加长上下文或全量替换。
    new_string 为空串即删除该段；追加内容以文件结尾的唯一文本作锚点。
    """
    old_string = old_string or ""
    new_string = new_string or ""
    if not old_string:
        return {"result": "[改写失败：old_string 不能为空；追加内容请以文件结尾的唯一文本作锚点]",
                "no_compress": True}
    if old_string == new_string:
        return {"result": "[改写失败：old_string 与 new_string 相同，没有可改的内容]", "no_compress": True}
    if len(new_string) > 100000:
        return {"result": "[改写失败：新内容过长 (>100000 字)]", "no_compress": True}
    try:
        path = Path(agent.resolve_ref(ref))
    except KeyError:
        return {"result": f"[改写失败：没有找到引用 {ref}]", "no_compress": True}
    if not path.is_file():
        return {"result": f"[改写失败：引用 {ref} 指向的文件不存在]", "no_compress": True}
    if detect_file_type(path) != FileType.TEXT:
        return {"result": "[改写失败：该文件不是文本文件]", "no_compress": True}
    # 指纹校验：精确匹配只保证内容唯一，保证不了还是 AI 读到的那份——
    # 读取后文件被外部改动（哪怕 old_string 仍能唯一匹配）一律拒绝，防静默错改
    if agent.file_changed_since_read(path):
        return {"result": "[改写失败：文件在读取后已经发生变化，请用 content_search 重新读取后再改写]",
                "no_compress": True}
    raw = decode_text(path.read_bytes())
    match_count = raw.count(old_string)
    if match_count == 0:
        return {"result": "[改写失败：没有找到待替换内容——文件可能在你读取后已发生变化，"
                          "请用 content_search 重新读取后再改写]", "no_compress": True}
    if match_count > 1 and not replace_all:
        # 列出每处所在行号，AI 可直接据此选取有区分度的上下文，省一轮重查
        positions = []
        start = 0
        while True:
            idx = raw.find(old_string, start)
            if idx < 0:
                break
            positions.append(raw.count("\n", 0, idx) + 1)
            start = idx + len(old_string)
        shown = "、".join(f"第 {n} 行" for n in positions[:5])
        if len(positions) > 5:
            shown += f" 等 {len(positions)} 处"
        return {"result": f"[改写失败：old_string 匹配到 {match_count} 处（{shown}），"
                          f"请加长上下文使其唯一，或设置 replace_all=true 全部替换]",
                "no_compress": True}
    changed_at = raw.count("\n", 0, raw.index(old_string)) + 1
    new_text = raw.replace(old_string, new_string) if replace_all \
        else raw.replace(old_string, new_string, 1)
    # 若目标是 history 文件，写入前检查其资源上限
    try:
        if Path(path).is_relative_to(agent.get_history_path().resolve()):
            quota_error = _check_history_quota(path, len(new_text.encode("utf-8")), agent)
            if quota_error:
                return {"result": quota_error, "no_compress": True}
    except (AttributeError, ValueError):
        pass
    agent.save_file(path, new_text)  # 统一写入口：写后自动刷新指纹，连续编辑不被误拦
    new_lines = new_text.splitlines()
    preview_center = min(changed_at, max(1, len(new_lines)))
    preview = "\n".join(
        f"{i}: {line}" for i, line in
        enumerate(new_lines[max(0, preview_center - 2): preview_center + 3], max(1, preview_center - 1))
    )
    return {"result": (f"已改写 {ref} 第 {changed_at} 行附近（替换 {match_count} 处，现共 {len(new_lines)} 行），"
                       f"可再次用 content_search / check_file 确认。改后局部：\n{preview}"),
            "no_compress": True}

def content_search(param, file_ref, search_method: Literal["re_search", "re_filter", "by_line"] = "re_search", agent=None):
    """按 search_method 搜索文件内容，所有模式的结果统一为「行号: 内容」（1 起算，行号用于定位；
    改写用 edit_file 引用原文，不依赖行号）。

    - re_search（默认）：param 作为正则在全文查找，返回每个匹配片段及其所在行号；
    - re_filter：param 作为正则分隔全文（re.split 语义），返回各匹配之间的间隙内容；
    - by_line：param 作为普通子串逐行匹配，返回包含该子串的整行。
    超过 100 条截断。
    """
    path = agent.resolve_ref(file_ref)
    text = decode_text(Path(path).read_bytes())
    agent.note_file_state(path)
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
    agent.note_file_state(path)
    method = None
    search_methods = {
        # "re_search": regex_search,
        "re_search": None,
        "re_filter": regex_filter,
        # "fuzzy_match": None,
    }
    method = search_methods.get(search_method, None)

    return {"result": "\n".join([f"{i + 1}. {c}" for i, c in enumerate(search_json(search_str, path, key, search_func=method))]), "no_compress": True}

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
    agent.note_file_state(path)
    get_lines = lines[line_start:line_end] if line_end != 0 else lines[line_start:]
    out = "\n".join([f'{i}: {l}' for i, l in enumerate(get_lines)])
    out = out if length == 0 else out[:length]
    if len(out) > 50000:
        out = out[:50000] + "\n[输出达到最大 50000 字，剩下请配置参数继续查看。]"
    return {"result": out, "no_compress": True}

def list_files(folder="temp", agent=None):
    """列出指定文件夹下的文件列表。

    folder: "temp"（默认）；"history"（history 根目录）；或 "history/嵌套/路径"
    （history 下的任意子文件夹）。列表内每个文件的引用都会注册到 ref_map
    （history 子文件夹内的引用为 "路径/名称" 形式），可直接用于其他工具。
    """
    parts = [p for p in str(folder).strip().split("/") if p]
    if parts[0] != "history":
        reversed_ref_map = reverse_dict(agent.ref_map)
        return "\n".join(
            f"{reversed_ref_map.get(f.name, None)}: {f.name} | size: {(f.stat().st_size / 1024):,.3f} KiB"
            for f in agent.get_temp_path().iterdir() if f.is_file()
        )
    # history / history/嵌套路径：各段过 is_safe_custom_name 防穿越
    sub = parts[1:]
    if any(not is_safe_custom_name(p) for p in sub):
        return f"[无效的文件夹路径：{folder}]"
    base = agent.get_history_path()
    for seg in sub:
        base = safe_join(base, seg)
    if not base.is_dir():
        return f"[文件夹 {folder} 不存在]"
    usage = dir_usage(base)
    depth_prefix = "/".join(sub)
    lines = [f"# {folder} 占用：{usage['count']} 个文件 / {usage['size']:,} B（上限 {HISTORY_MAX_FILES} 个）"]
    for f in sorted([f for f in base.iterdir() if f.is_file()], key=lambda f: f.name):
        # history_<数字>.tmp → ref 取 stem；其他文件 → ref 为路径形（与文件系统层级一致）
        ref = f.stem if (f.name == f"{f.stem}.tmp" and f.stem.startswith("history_")) else f.name
        full_ref = "/".join([*sub, ref]) if sub else ref
        agent.ref_map[full_ref] = str(f)
        fsize = f"{(f.stat().st_size / 1024):,.3f} KiB"
        lines.append(f"{full_ref}: {f.name} | size: {fsize}")
    folders = sorted([d for d in base.iterdir() if d.is_dir()])
    if folders:
        lines.append("# 文件夹（list_files 的 folder 参数加此名称可进入，move_history_file / zip_files 的 folder 参数可用这些名称）")
        for d in folders:
            d_usage = dir_usage(d)
            lines.append(f"{('/'.join([*sub, d.name]))}/ - {d_usage['count']} 个文件 / {d_usage['size']:,} B")
    if len(lines) == 1:
        lines.append("（空文件夹）")
    return "\n".join(lines)


def _history_file(ref: str, agent, register: bool = False):
    """统一解析历史文件引用：校验 + 得到 (ref, path)。

    所有历史文件操作（定位 / 写入 / 追加 / 删除 / 重命名 / 转存）都应通过
    本函数获取引用与路径，以保证引用格式校验、会话文件夹与 ref_map 注册行为一致。
    register=True 时会把引用注册到 agent.ref_map（供 check_file 等后续使用）。
    ref 支持（history 为根目录，各段均过 is_safe_custom_name 防路径穿越，可嵌套多层文件夹）：
    - history_N → history_N.tmp；
    - 安全自定义文件名 → 根目录下同名文件；
    - "文件夹/.../文件名" → history 下嵌套文件夹内的文件。
    非法引用返回 None。
    """
    parts = ref.split("/")
    if any(not p or not is_safe_custom_name(p) for p in parts):
        return None
    path = agent.get_history_path()
    for folder in parts[:-1]:
        path = safe_join(path, folder)
    file_name = history_file_name(parts[-1])
    if file_name is None:
        return None
    path = safe_join(path, file_name)
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
        agent.save_file(path, content, mode=mode)
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
        return {"result": "[写入失败：写入内容过长 (>100000 字) 大文件请使用 download 下载到 temp 再转存到 history]", "no_compress": True}
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
        agent.save_file(path, content, mode=mode)
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
    """删除历史文件；ref 指向自定义文件夹（含嵌套）时删除整个文件夹。"""
    res = _history_file(ref, agent)
    if res is None:
        return {"result": f"[无效的历史文件引用：{ref}]", "no_compress": True}
    _, path = res
    if not path.exists():
        return {"result": f"[历史文件或文件夹 {ref} 不存在]", "no_compress": True}
    try:
        if path.is_dir():
            # 自定义文件夹：按深度倒序递归删除（文件走 delete_file 同步指纹，目录随后清空）
            deleted = 0
            for p in sorted(path.rglob("*"), key=lambda p: len(p.parts), reverse=True):
                if p.is_file():
                    agent.delete_file(p)
                    deleted += 1
                else:
                    p.rmdir()  # 深度序下此时必为空
            path.rmdir()
            # 该文件夹及其全部子路径的引用一并失效
            for k in [k for k in agent.ref_map if k == ref or k.startswith(ref + "/")]:
                agent.ref_map.pop(k, None)
            return {"result": f"已删除文件夹 {ref}（含 {deleted} 个文件）", "no_compress": True}
        agent.delete_file(path)
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
        agent.rename_file(old_path, new_path)
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


def save_to_history(ref, history_ref="", path="", agent=None):
    """转存文件到 history（可选嵌套文件夹），生成路径形引用。
    ref: 来源文件引用（temp 的 file_N/text_N/json_N 或已有历史引用）。
    文本文件按文本转存（走 write_to_history）；图片/PDF/压缩包等二进制按
    原始字节转存并保留原扩展名。
    history_ref: 可选，保存时自定义名（history_N 或安全自定义名如 笔记.md）；不填自动分配 history_N；已存在会报错。
    path: 可选，history 下的嵌套文件夹路径（如 "项目/资料"，必须已存在，
    先用 create_history_folder 创建）；填写后返回的引用为 "路径/名称" 形式。
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
    # 目标文件夹：嵌套路径各段校验 + 必须已存在（不自动创建）
    parts = [p for p in (path or "").strip().split("/") if p]
    if any(not is_safe_custom_name(p) for p in parts):
        return {"result": f"[转存失败：文件夹路径 {path} 不合法（仅允许中英文/数字/_-. 的段）]", "no_compress": True}
    folder_dir = agent.get_history_path()
    for part in parts:
        folder_dir = safe_join(folder_dir, part)
    if parts and not folder_dir.is_dir():
        return {"result": f"[转存失败：文件夹 {'/'.join(parts)} 不存在（请先用 create_history_folder 创建）]", "no_compress": True}
    # 自定义名：统一校验 + 防重名（引用为 路径/名称 形式，便于直接被其他工具解析）
    if history_ref:
        if "/" in history_ref:
            return {"result": f"[无效的历史文件引用名：{history_ref}]（名称不含 /，路径请用 path 参数）", "no_compress": True}
        ref_id = "/".join([*parts, history_ref]) if parts else history_ref
        res = _history_file(ref_id, agent)
        if res is None:
            return {"result": f"[无效的历史文件引用名：{history_ref}]（仅支持 history_N 或安全自定义名）", "no_compress": True}
        _, target = res
        if target.exists():
            return {"result": f"[历史文件 {ref_id} 已存在，请换名或先 delete_history_file]", "no_compress": True}
    else:
        base = _next_history_ref(agent)
        ref_id = "/".join([*parts, base]) if parts else base
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
            agent.save_file(target, data, binary=True)
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
    """清空 history 文件夹里的所有文件（含子文件夹），并移除对应引用。"""
    hist_path = agent.get_history_path()
    removed = 0
    if hist_path.is_dir():
        for item in hist_path.iterdir():
            if item.is_dir():
                removed += sum(1 for f in item.rglob("*") if f.is_file())
                shutil.rmtree(item)
            elif item.is_file() or item.is_symlink():
                item.unlink()
                removed += 1
    agent.ref_map = {
        k: v for k, v in agent.ref_map.items()
        if not str(v).startswith("data/ai_historys/")
    }
    return {"result": f"已清空 history（含文件夹），共删除 {removed} 个文件", "no_compress": True}


def zip_files(refs_or_folders: list[str], name: str, folder: str = "", agent=None):
    """把多个引用文件打包为一个 zip 并转存到 history（自定义名，自动补 .zip 后缀）。

    - 压缩过程中压缩包超过 MAX_ZIP_SIZE 立即中止并删除半成品；
    - 引用之间存在重复文件名（zip 内路径冲突）时报错；
    - 目标名已存在/不安全时报错。成功返回 zip 的引用与详情。
    """
    if agent is None:
        return {"result": "[打包失败：无法获取会话上下文]", "no_compress": True}
    refs_or_folders = [str(r).strip() for r in (refs_or_folders or []) if str(r).strip()]
    if not refs_or_folders:
        return {"result": "[打包失败：refs 不能为空]", "no_compress": True}
    # 解析全部引用；文件夹引用递归展开为 (zip内路径, 磁盘路径, 来源引用)，保留目录结构
    items: list[tuple[str, Path, str]] = []
    for ref in refs_or_folders:
        try:
            p = Path(agent.resolve_ref(ref))
        except KeyError:
            return {"result": f"[打包失败：没有找到引用 {ref}]", "no_compress": True}
        if p.is_file():
            items.append((p.name, p, ref))
        elif p.is_dir():
            files = sorted(f for f in p.rglob("*") if f.is_file())
            if not files:
                return {"result": f"[打包失败：引用 {ref} 指向的文件夹是空的]", "no_compress": True}
            for f in files:
                items.append((f"{p.name}/{f.relative_to(p).as_posix()}", f, ref))
        else:
            return {"result": f"[打包失败：引用 {ref} 指向的文件不存在]", "no_compress": True}
    # zip 内重名检查（同一文件传两次、或不同目录同名文件都算冲突）
    seen: dict[str, str] = {}
    for arcname, _, ref in items:
        if arcname in seen:
            return {"result": f"[打包失败：存在重复的文件名 \"{arcname}\"（引用 {seen[arcname]} 与 {ref}），", "no_compress": True}
        seen[arcname] = ref
    # 目标名：安全校验 + 自动补 .zip
    name = (name or "").strip()
    if not name:
        return {"result": "[打包失败：需要填写 zip 文件名]", "no_compress": True}
    if not name.lower().endswith(".zip"):
        name += ".zip"
    parts = [p for p in (folder or "").strip().split("/") if p]
    if any(not is_safe_custom_name(p) for p in parts):
        return {"result": f"[打包失败：文件夹名 {folder} 不合法（仅允许中英文/数字/_-. 的段）]", "no_compress": True}
    folder_dir = agent.get_history_path()
    for part in parts:
        folder_dir = safe_join(folder_dir, part)
    if parts and not folder_dir.is_dir():
        return {"result": f"[打包失败：文件夹 {'/'.join(parts)} 不存在（请先用 create_history_folder 创建）]", "no_compress": True}
    target = safe_join(folder_dir, name)
    if target.exists():
        return {"result": f"[打包失败：历史文件 {name} 已存在，请换名]", "no_compress": True}
    # 流式压缩：每写入一个文件检查一次压缩包体积，超限立即中止
    part = target.with_name(target.name + ".part")
    part.parent.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(part, "w", zipfile.ZIP_DEFLATED) as zf:
            for arcname, p, ref in items:
                zf.write(p, arcname=arcname)
                if part.stat().st_size > MAX_ZIP_SIZE:
                    raise ValueError(
                        f"压缩包超过 {MAX_ZIP_SIZE // 1048576}MiB 上限（添加 {arcname} 后已达 "
                        f"{part.stat().st_size / 1048576:.1f}MiB）")
    except ValueError as ex:
        part.unlink(missing_ok=True)
        return {"result": f"[打包失败：{ex}]", "no_compress": True}
    except Exception as ex:
        part.unlink(missing_ok=True)
        logger.exception(f"打包 zip 失败: {ex}")
        return {"result": f"[打包失败：{ex}]", "no_compress": True}
    # history 资源配额检查后落位
    zip_size = part.stat().st_size
    quota_error = _check_history_quota(target, zip_size, agent)
    if quota_error:
        part.unlink(missing_ok=True)
        return {"result": quota_error, "no_compress": True}
    target.parent.mkdir(parents=True, exist_ok=True)
    agent.rename_file(part, target)  # 统一入口：改名并同步指纹（产出的 zip 也是 AI 的文件）
    ref = "/".join([*parts, name]) if parts else name
    agent.ref_map[ref] = str(target)
    file_list = "、".join(arcname for arcname, _, _ in items)
    location = f"history 的 {'/'.join(parts)}/ 文件夹" if parts else "history 根目录"
    return {
        "result": (f"已打包 {len(items)} 个文件为 {name}（{zip_size / 1048576:.2f} MiB）并转存至 {location}，"
                   f"引用 {ref}。包含：{file_list}。可用 send_file 发送或 view_document_file 查看。"),
        "ref": ref,
        "file_name": name,
        "size": zip_size,
        "files": list(seen.keys()),
        "no_compress": True,
    }


def _sanitize_archive_entry(entry_name: str) -> str | None:
    """清洗压缩包内条目名为安全相对路径（防 zip-slip）；不合法返回 None。

    反斜杠归一为 /；拒绝 ..、.、空段、NUL 字节；深度 ≤ 8；单段长度 ≤ 100 字符。
    """
    name = entry_name.replace("\\", "/")
    if "\x00" in name:
        return None
    parts = [p for p in name.split("/") if p not in ("", ".")]
    if not parts or any(p == ".." for p in parts) or len(parts) > 8:
        return None
    if any(len(p) > 100 for p in parts):
        return None
    return "/".join(parts)


def _default_extract_name(archive_name: str) -> str:
    """由压缩包文件名推导输出文件夹名：非法字符清洗为 _，清洗后为空用 extracted。"""
    stem = archive_name
    for suffix in (".tar.gz", ".tgz", ".tar.bz2", ".tar", ".zip", ".gz"):
        if stem.lower().endswith(suffix):
            stem = stem[: -len(suffix)]
            break
    cleaned = re.sub(r"[^\w\u4e00-\u9fff.\-]", "_", stem).strip("._-") or "extracted"
    return cleaned[:100]


def extract_archive(ref: str, folder: str = "", name: str = "",
                    password: str = "", agent=None):
    """解压压缩包到 history 的独立文件夹，返回解出的文件引用列表。

    格式：zip / tar / tar.gz / tgz / tar.bz2 / gzip 单文件；7z、rar 暂不支持。
    password 仅对 zip 生效（标准库仅支持传统 ZipCrypto 加密，AES 加密的 zip 不支持）。
    解压前预检条目数与总大小（防压缩炸弹），条目名清洗防 zip-slip；
    每个解出文件经 agent.save_file 落盘（history 守卫 + 指纹自动登记）并登记引用。
    """
    try:
        path = Path(agent.resolve_ref(ref))
    except KeyError:
        return {"result": f"[解压失败：没有找到引用 {ref}]", "no_compress": True}
    if not path.is_file():
        return {"result": f"[解压失败：引用 {ref} 指向的文件不存在]", "no_compress": True}
    suffix = path.suffix.lower()
    full_lower = path.name.lower()
    if suffix in (".7z", ".rar"):
        return {"result": f"[解压失败：暂不支持 {suffix} 格式，请先转成 zip]", "no_compress": True}
    kind = None
    if suffix == ".zip":
        kind = "zip"
    elif full_lower.endswith((".tar.gz", ".tgz", ".tar.bz2")) or suffix == ".tar":
        kind = "tar"
    elif suffix == ".gz":
        kind = "gzip"
    if kind is None:
        return {"result": f"[解压失败：不支持的格式 {suffix or '(无扩展名)'}"
                          f"（支持 zip / tar / tar.gz / tgz / tar.bz2 / gz）]", "no_compress": True}

    # 输出位置：history/<folder>/<name>/
    parts = [p for p in (folder or "").strip().split("/") if p]
    if any(not is_safe_custom_name(p) for p in parts):
        return {"result": f"[解压失败：文件夹名 {folder} 不合法（仅允许中英文/数字/_-. 的段）]",
                "no_compress": True}
    folder_dir = agent.get_history_path()
    for part in parts:
        folder_dir = safe_join(folder_dir, part)
    if parts and not folder_dir.is_dir():
        return {"result": f"[解压失败：文件夹 {'/'.join(parts)} 不存在（请先用 create_history_folder 创建）]",
                "no_compress": True}
    out_name = (name or "").strip() or _default_extract_name(path.name)
    if not is_safe_custom_name(out_name):
        return {"result": f"[解压失败：输出文件夹名 {out_name} 不合法（仅允许中英文/数字/_-. 的段）]",
                "no_compress": True}
    target_dir = safe_join(folder_dir, out_name)
    if target_dir.exists():
        return {"result": f"[解压失败：输出文件夹 {out_name} 已存在，请换名或先删除]", "no_compress": True}

    pwd = password.encode("utf-8") if password else None
    created: list[Path] = []  # 已写入文件（失败回滚用）
    refs: list[str] = []
    out_ref_base = "/".join([*parts, out_name]) if parts else out_name

    def _register(target: Path, rel: str) -> None:
        ref_id = f"{out_ref_base}/{rel}"
        agent.ref_map[ref_id] = str(target)
        refs.append(ref_id)

    def _rollback() -> None:
        for f in reversed(created):
            try:
                agent.delete_file(f)
            except OSError:
                pass
        # 自底向上清掉解压产生的空目录
        for root, dirs, _files in sorted(os.walk(target_dir), reverse=True):
            try:
                Path(root).rmdir()
            except OSError:
                pass  # 非空（含仍存在的 history 上层）时跳过

    def _fail(msg: str) -> dict:
        _rollback()
        return {"result": msg, "no_compress": True}

    # ---- 枚举条目 + 炸弹预检 ----
    try:
        if kind == "zip":
            zf = zipfile.ZipFile(path)
            infos = [i for i in zf.infolist()
                     if not i.is_dir() and (i.external_attr >> 16) & 0o170000 != 0o120000]
            entries = []
            for info in infos:
                rel = _sanitize_archive_entry(info.filename)
                if rel is None:
                    continue
                entries.append((info, rel))
        elif kind == "tar":
            tf = tarfile.open(path)
            entries = []
            for m in tf.getmembers():
                if not m.isreg():
                    continue
                rel = _sanitize_archive_entry(m.name)
                if rel is not None:
                    entries.append((m, rel))
        else:
            entries = None  # gzip 单文件在解压阶段单独处理
    except zipfile.BadZipFile as ex:
        return _fail(f"[解压失败：损坏的 zip 文件（{ex}）]")
    except tarfile.TarError as ex:
        return _fail(f"[解压失败：损坏的 tar 文件（{ex}）]")

    if entries is not None:
        if len(entries) > MAX_EXTRACT_FILES:
            return _fail(f"[解压失败：压缩包含 {len(entries)} 个文件，超过单次解压上限 {MAX_EXTRACT_FILES} 个]")
        total = sum((i.file_size for i, _ in entries) if kind == "zip"
                    else (m.size for m, _ in entries))
        if total > MAX_EXTRACT_TOTAL_SIZE:
            return _fail(f"[解压失败：解压总大小 {total / 1048576:.1f} MiB 超过单次上限 "
                         f"{MAX_EXTRACT_TOTAL_SIZE // 1048576} MiB（疑似压缩炸弹）]")
        quota_error = _check_history_quota(target_dir, total, agent)
        if quota_error:
            return {"result": quota_error, "no_compress": True}

    # ---- 解压 ----
    target_dir.mkdir(parents=True, exist_ok=False)
    try:
        if kind == "zip":
            for info, rel in entries:
                target = target_dir.joinpath(*rel.split("/"))
                target.parent.mkdir(parents=True, exist_ok=True)
                agent.save_file(target, zf.read(info, pwd=pwd), binary=True)
                created.append(target)
                _register(target, rel)
        elif kind == "tar":
            for member, rel in entries:
                target = target_dir.joinpath(*rel.split("/"))
                target.parent.mkdir(parents=True, exist_ok=True)
                agent.save_file(target, tf.extractfile(member).read(), binary=True)
                created.append(target)
                _register(target, rel)
        else:  # gzip 单文件
            with gzip.open(path, "rb") as f:
                data = f.read(MAX_EXTRACT_TOTAL_SIZE + 1)
            if len(data) > MAX_EXTRACT_TOTAL_SIZE:
                return _fail(f"[解压失败：解压总大小超过单次上限 {MAX_EXTRACT_TOTAL_SIZE // 1048576} MiB"
                             f"（疑似压缩炸弹）]")
            rel = _sanitize_archive_entry(path.stem) or "extracted"
            target = target_dir / rel
            agent.save_file(target, data, binary=True)
            created.append(target)
            _register(target, rel)
    except RuntimeError as ex:
        # 加密 zip：缺密码 / 密码错误 / AES 加密（标准库不支持）都从这里出来
        detail = str(ex)
        if "password" in detail.lower() or "decrypt" in detail.lower():
            return _fail(f"[解压失败：该 zip 已加密——{detail}。"
                         f"请传 password（标准库仅支持传统 ZipCrypto 加密，AES 加密请先转格式）]")
        logger.exception(f"解压失败: {ex}")
        return _fail(f"[解压失败：{exception_detail(ex)}]")
    except NotImplementedError as ex:
        return _fail(f"[解压失败：该 zip 使用的压缩/加密方式标准库不支持（{ex}），请转成常规 zip]")
    except (OSError, zipfile.BadZipFile, tarfile.TarError) as ex:
        logger.exception(f"解压失败: {ex}")
        return _fail(f"[解压失败：{exception_detail(ex)}]")

    size_note = f"共 {len(refs)} 个文件"
    preview = "、".join(refs[:10]) + ("…" if len(refs) > 10 else "")
    location = f"history 的 {'/'.join(parts)}/ 文件夹" if parts else "history 根目录"
    return {"result": (f"已解压到 {location} 的 {out_name}/ 文件夹（{size_note}），"
                       f"引用：{preview}。可用 check_file / content_search 查看内容。"),
            "ref": out_ref_base, "no_compress": True}



def create_history_folder(name: str, agent=None):
    """在 history 下创建一个新文件夹（history 即根目录；支持 a/b 嵌套路径）。

    各段均过 is_safe_custom_name 防路径穿越；嵌套路径只创建最后一级，
    父目录必须已存在（不自动创建中间层，请逐级创建）。
    """
    parts = [p for p in (name or "").strip().split("/") if p]
    if not parts or any(not is_safe_custom_name(p) for p in parts):
        return {"result": f"[创建失败：文件夹名 {name} 不合法（仅允许中英文/数字/_-. 的段，不含路径穿越）]", "no_compress": True}
    path = agent.get_history_path()
    for folder in parts[:-1]:
        path = safe_join(path, folder)
        if not path.is_dir():
            return {"result": f"[创建失败：父文件夹 {folder} 不存在（嵌套路径请逐级创建）]", "no_compress": True}
    path = safe_join(path, parts[-1])
    if path.exists():
        return {"result": f"[创建失败：文件夹 {'/'.join(parts)} 已存在]", "no_compress": True}
    path.mkdir(parents=True)
    return {"result": f"已在 history 创建文件夹 {'/'.join(parts)}/。可用 move_history_file 移入文件，"
                      f"或 zip_files 打包时用 folder 参数放入该文件夹。",
            "no_compress": True}


def move_history_file(ref: str, folder: str = "", agent=None):
    """把 history 里的文件移动到指定文件夹（支持嵌套路径；folder 为空移回根目录）。

    目标文件夹必须已存在（不自动创建，请先用 create_history_folder 逐级创建）。
    移动后旧引用失效，新引用为 "文件夹/.../原引用名"。
    """
    res = _history_file(ref, agent)
    if res is None:
        return {"result": f"[移动失败：无效的历史文件引用 {ref}]", "no_compress": True}
    _, src = res
    if not src.exists():
        return {"result": f"[移动失败：历史文件 {ref} 不存在]", "no_compress": True}
    parts = [p for p in (folder or "").strip().split("/") if p]
    if any(not is_safe_custom_name(p) for p in parts):
        return {"result": f"[移动失败：文件夹名 {folder} 不合法（仅允许中英文/数字/_-. 的段）]", "no_compress": True}
    folder_dir = agent.get_history_path()
    for part in parts:
        folder_dir = safe_join(folder_dir, part)
    if parts and not folder_dir.is_dir():
        return {"result": f"[移动失败：文件夹 {'/'.join(parts)} 不存在（请先用 create_history_folder 创建）]", "no_compress": True}
    target = safe_join(folder_dir, src.name)
    if target.exists():
        return {"result": f"[移动失败：目标位置已存在同名文件 {src.name}]", "no_compress": True}
    agent.rename_file(src, target)  # 统一入口：移动并同步指纹
    # 旧引用随文件移动失效，登记含文件夹的新引用（后续工具按新引用定位）
    agent.ref_map.pop(ref, None)
    base_ref = ref.split("/")[-1]
    new_ref = "/".join([*parts, base_ref]) if parts else base_ref
    agent.ref_map[new_ref] = str(target)
    return {"result": (f"已把 {ref} 移动到 {'/'.join(parts) + '/' if parts else 'history 根目录'}，"
                       f"新引用为 {new_ref}（旧引用已失效）"),
            "ref": new_ref, "no_compress": True}


# ---- syntax_check：纯语法检测（绝不执行被检代码）----

# 子进程内执行的解析脚本：从 stdin 读文本（与父进程的 decode_text 结果一致），
# 输出一行 JSON 结果。启动后先自设 rlimit（替代 preexec_fn——官方不推荐在
# 多线程进程中使用 fork 后回调，此写法保护等效且无死锁风险），再读入解析；
# 深嵌套/超大输入的 RecursionError、MemoryError 在此消化。
# argv: [语言, CPU 超时秒, 地址空间上限字节]
_SYNTAX_CHECK_SCRIPT = r'''
import ast, json, resource, sys
sys.stdin.reconfigure(encoding="utf-8", errors="replace")
cpu, as_limit = int(sys.argv[2]), int(sys.argv[3])
resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu))
resource.setrlimit(resource.RLIMIT_AS, (as_limit, as_limit))
text = sys.stdin.read()
lang = sys.argv[1]
try:
    if lang == "json":
        json.loads(text)
    else:
        ast.parse(text)
except json.JSONDecodeError as ex:
    lines = text.splitlines()
    src = lines[ex.lineno - 1][:200] if 0 < ex.lineno <= len(lines) else ""
    print(json.dumps({"ok": False, "line": ex.lineno, "col": ex.colno, "msg": ex.msg, "text": src}))
except SyntaxError as ex:
    print(json.dumps({"ok": False, "line": ex.lineno, "col": ex.offset, "msg": ex.msg,
                      "text": (ex.text or "").rstrip()[:200]}))
except (RecursionError, MemoryError, ValueError):
    print(json.dumps({"ok": False, "error": "文件过大或嵌套过深，解析器无法处理"}))
else:
    print(json.dumps({"ok": True, "lines": len(text.splitlines())}))
'''

# node 启动包装脚本：子进程内先自设 rlimit 再 execvp node（同上替代 preexec_fn），
# stdin/stderr 等文件描述符原样继承。argv: [node 可执行名, CPU 超时秒, 地址空间上限字节, ...node 参数]
_SYNTAX_NODE_LAUNCHER = (
    "import os, resource, sys\n"
    "cpu, as_limit = int(sys.argv[2]), int(sys.argv[3])\n"
    "resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu))\n"
    "resource.setrlimit(resource.RLIMIT_AS, (as_limit, as_limit))\n"
    "os.execvp(sys.argv[1], [sys.argv[1]] + sys.argv[4:])\n"
)

# 语法检测语言注册表（单点维护）：扩展名推断表、支持语言白名单均从此派生，
# 新增语言只需在此登记。runner：
# - "script"：_SYNTAX_CHECK_SCRIPT 内置解析器（stdin 传文本）
# - "node"  ：node --check 子进程（stdin + --input-type）
# 注：tools.json 的 schema 描述是唯一需手动同步的点
_SYNTAX_LANGUAGES: dict[str, dict] = {
    "python":     {"exts": (".py", ".pyw"), "runner": "script"},
    "json":       {"exts": (".json",), "runner": "script"},
    "javascript": {"exts": (".js", ".mjs", ".cjs"), "runner": "node"},
}
_SYNTAX_LANG_BY_EXT = {ext: lang for lang, cfg in _SYNTAX_LANGUAGES.items() for ext in cfg["exts"]}

# ESM 嗅探：行首 import/export 语句（import( 动态导入在 CommonJS 里也合法，排除）。
# 只决定 node --check 的解析模式，判错也不影响安全性。
_ESM_SNIFF_RE = re.compile(r"(?:^|\n)[ \t]*(?:export\b|import\b[ \t]*(?!\())")


def _looks_like_esm(text: str) -> bool:
    """按行首 import/export 语句判断文本是否为 ESM 模块。"""
    return _ESM_SNIFF_RE.search(text) is not None


async def _communicate_or_kill(proc: asyncio.subprocess.Process, input_bytes: bytes | None, timeout: float):
    """等待子进程完成；超时则 kill 并返回 None。

    进程在超时瞬间恰好已退出并被收尸时 kill 会抛 ProcessLookupError，
    忽略之（否则超时文案会变成异常冒泡）。
    """
    try:
        return await asyncio.wait_for(proc.communicate(input_bytes), timeout)
    except asyncio.TimeoutError:
        with contextlib.suppress(ProcessLookupError):
            proc.kill()
        return None


async def _node_version() -> tuple[int, ...] | None:
    """探测 node 版本号（每次现探、不缓存：运行中升级 node 也能生效）；失败返回 None。"""
    proc = await asyncio.create_subprocess_exec(
        "node", "--version",
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
    out = await _communicate_or_kill(proc, None, 5)
    if out is None:
        return None
    m = re.match(rb"v(\d+)\.(\d+)", out[0].strip())
    return (int(m.group(1)), int(m.group(2))) if m else None


async def _syntax_check_parse(text: str, lang: str) -> dict:
    """python/json 检测：固定解析脚本在隔离子进程里跑（脚本自设 rlimit），文本经 stdin 传入。"""
    proc = await asyncio.create_subprocess_exec(
        sys.executable, "-c", _SYNTAX_CHECK_SCRIPT, lang,
        str(SYNTAX_CHECK_TIMEOUT), str(SYNTAX_CHECK_AS_LIMIT),
        stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL)
    out = await _communicate_or_kill(proc, text.encode("utf-8"), SYNTAX_CHECK_TIMEOUT)
    if out is None:
        return {"ok": False, "error": "解析超时"}
    if proc.returncode != 0:
        return {"ok": False, "error": f"解析进程异常退出（码 {proc.returncode}）"}
    try:
        return json.loads(out[0].decode("utf-8", "replace"))
    except json.JSONDecodeError:
        return {"ok": False, "error": "解析进程输出异常"}


async def _syntax_check_node(text: str, source_ext: str) -> dict:
    """javascript 检测：node --check 只做语法解析不执行代码；未装 node 时降级提示。

    node ≥ 12 统一经 stdin + --input-type 检测（ESM/CommonJS 均可，文本与
    python/json 路径同源、不落盘）；更老版本（如 Ubuntu 20.04 自带 v10）不支持
    --input-type，退回临时文件真 .js 后缀按 CommonJS 检测，ESM 给出明确的
    版本过低提示。模块类型按扩展名（.mjs/.cjs）优先，其余靠 import/export 嗅探。
    """
    if shutil.which("node") is None:
        return {"ok": False, "error": "服务器未安装 node，无法检查 javascript"}
    try:
        version = await _node_version()
    except FileNotFoundError:
        return {"ok": False, "error": "服务器未安装 node，无法检查 javascript"}
    if version is None:
        return {"ok": False, "error": "无法获取 node 版本，无法检查 javascript"}
    if source_ext == ".mjs":
        is_esm = True
    elif source_ext == ".cjs":
        is_esm = False
    else:
        is_esm = _looks_like_esm(text)
    if version < (12,) and is_esm:
        return {"ok": False,
                "error": f"node 版本过低（v{'.'.join(map(str, version))}），无法检查 ESM 语法"}
    rlimit_args = ("node", str(SYNTAX_CHECK_TIMEOUT), str(SYNTAX_CHECK_AS_LIMIT_NODE))
    temp_path = None
    try:
        if version >= (12,):
            argv = (sys.executable, "-c", _SYNTAX_NODE_LAUNCHER, *rlimit_args,
                    "--input-type", "module" if is_esm else "commonjs", "--check", "-")
            input_bytes = text.encode("utf-8")
        else:
            # 旧版 node：临时文件真后缀按 CommonJS 检测（uuid 名，用完即删）
            temp_dir = Path("./data/temp")
            temp_dir.mkdir(parents=True, exist_ok=True)
            temp_path = temp_dir / f"syntax-{uuid4().hex}.js"
            temp_path.write_text(text, encoding="utf-8")
            argv = (sys.executable, "-c", _SYNTAX_NODE_LAUNCHER, *rlimit_args,
                    "--check", str(temp_path))
            input_bytes = None
        proc = await asyncio.create_subprocess_exec(
            *argv, stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE)
        out = await _communicate_or_kill(proc, input_bytes, SYNTAX_CHECK_TIMEOUT)
        if out is None:
            return {"ok": False, "error": "解析超时"}
        if proc.returncode == 0:
            return {"ok": True, "lines": len(text.splitlines())}
        err = out[1].decode("utf-8", "replace")
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
    # node 报错首行形如 "路径:行号"或"[stdin]:行号"，其后依次是出错行原文、^ 指示、SyntaxError 描述
    m = re.search(r":(\d+)\r?\n(.*)", err, re.S)
    if m:
        rest = [x for x in m.group(2).splitlines() if x.strip()]
        src = rest[0][:200] if rest else ""
        msg = next((x.strip() for x in rest[1:] if "Error" in x), rest[-1] if rest else "语法错误")
        return {"ok": False, "line": int(m.group(1)), "col": 0, "msg": msg, "text": src}
    return {"ok": False, "error": err.strip()[:300] or "未知语法错误"}


def _syntax_result(lang: str, data: dict) -> dict:
    """把子进程结果格式化为工具返回；错误带 行号/列/出错行/^ 指示，闭环到 edit_file。"""
    if data.get("ok"):
        return {"result": f"语法检查通过（{lang}，共 {data.get('lines', '?')} 行）",
                "language": lang, "no_compress": True}
    if "error" in data:
        return {"result": f"[语法检查失败：{lang} 解析器异常（{data['error']}）]", "no_compress": True}
    line_no = data.get("line") or "?"
    col = data.get("col")
    src = (data.get("text") or "").rstrip()
    msg = data.get("msg") or "语法错误"
    at = f"第 {line_no} 行" + (f"第 {col} 列" if isinstance(col, int) and col > 0 else "")
    body = src
    if src and isinstance(col, int) and col > 0:
        body = f"{src}\n{' ' * (col - 1)}^"
    return {"result": (f"语法错误（{lang}）{at}：{msg}"
                       + (f"\n{body}" if body else "")
                       + "\n每次报告第一个错误，可用 edit_file 修正后再次检查。"),
            "no_compress": True}


async def syntax_check(ref: str = "", code: str = "", language: str = "", agent=None):
    """对代码做纯语法检测（绝不执行被检代码），返回首个语法错误的行/列标注。

    ref（temp/history 文件）与 code（内联代码文本）二选一；
    language 不填时按扩展名推断（.py/.json/.js/.mjs/.cjs），内联代码默认 python。
    检测在隔离子进程内进行（子进程自设 CPU/内存 rlimit + 墙钟超时 kill）：
    python/json 用标准库解析器；javascript 用 node --check（仅解析不执行），
    node ≥ 12 自动识别 ESM/CommonJS，旧版 node 仅支持 CommonJS（ESM 返回
    版本过低提示）；未安装 node 时返回降级提示。
    """
    if bool(ref) == bool(code):
        return {"result": "[语法检查失败：ref 与 code 二选一]", "no_compress": True}
    if len(code.encode("utf-8")) > MAX_SYNTAX_CHECK_SIZE:
        return {"result": f"[语法检查失败：代码过长（>{MAX_SYNTAX_CHECK_SIZE // 1024 // 1024} MiB）]",
                "no_compress": True}
    if code:
        text = code
        source_ext = ""
    else:
        try:
            path = Path(agent.resolve_ref(ref))
        except KeyError:
            return {"result": f"[语法检查失败：没有找到引用 {ref}]", "no_compress": True}
        if not path.is_file():
            return {"result": f"[语法检查失败：引用 {ref} 指向的文件不存在]", "no_compress": True}
        if path.stat().st_size > MAX_SYNTAX_CHECK_SIZE:
            return {"result": f"[语法检查失败：文件过大（>{MAX_SYNTAX_CHECK_SIZE // 1024 // 1024} MiB）]",
                    "no_compress": True}
        if detect_file_type(path) != FileType.TEXT:
            return {"result": "[语法检查失败：该文件不是文本文件]", "no_compress": True}
        text = decode_text(path.read_bytes())
        source_ext = path.suffix.lower()
    lang = (language or "").strip().lower()
    if not lang:
        lang = _SYNTAX_LANG_BY_EXT.get(source_ext, "") or ("python" if code else "")
    if not lang:
        return {"result": "[语法检查失败：无法从扩展名判断语言，请用 language 参数指定"
                          f"（{' / '.join(_SYNTAX_LANGUAGES)}）]", "no_compress": True}
    if lang not in _SYNTAX_LANGUAGES:
        return {"result": f"[语法检查失败：不支持的语言 {lang}（可选 {' / '.join(_SYNTAX_LANGUAGES)}）]",
                "no_compress": True}
    if _SYNTAX_LANGUAGES[lang]["runner"] == "node":
        return _syntax_result(lang, await _syntax_check_node(text, source_ext))
    return _syntax_result(lang, await _syntax_check_parse(text, lang))
