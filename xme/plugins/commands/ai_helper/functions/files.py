# some are made by Deepseek-v4-flash-vison-exp at Deepseek Harness
"""文件类工具：temp/history 的读写、搜索、改写、转存、发送与清理。"""
from pathlib import Path
import shutil
import re
import zipfile
from typing import Literal

from nonebot.log import logger
from xme.xmetools.dicttools import reverse_dict
from xme.xmetools.filetools import (
    decode_text, detect_file_type, search_json, history_file_name,
    is_safe_custom_name, safe_join, dir_usage, FileType, text_to_file, to_container_path,
)
from xme.xmetools.texttools import regex_filter
from xme.xmetools.bottools import bot_call_action
from ..constants import HISTORY_MAX_FILES, HISTORY_MAX_SIZE, MAX_ZIP_SIZE
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
    # 保持原文件的尾换行语义：原来有尾换行（或结果为空）才补 \n，改写本身不引入新换行
    new_text = "\n".join(new_lines) + ("\n" if new_lines and trailing_newline else "")
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
        folders = sorted([d for d in hist_path.iterdir() if d.is_dir()])
        if folders:
            lines.append("# 文件夹（move_history_file / zip_files 的 folder 参数可用这些名称）")
            for d in folders:
                d_usage = dir_usage(d)
                lines.append(f"{d.name}/ - {d_usage['count']} 个文件 / {d_usage['size']:,} B")
        return "\n".join(lines)
    reversed_ref_map = reverse_dict(agent.ref_map)
    files = [f"{reversed_ref_map.get(f.name, None)}: {f.name} | size: {(f.stat().st_size / 1024):,.3f} KiB" for f in agent.get_temp_path().iterdir() if f.is_file()]
    return "\n".join(files)


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


def zip_files(refs: list[str], name: str, folder: str = "", agent=None):
    """把多个引用文件打包为一个 zip 并转存到 history（自定义名，自动补 .zip 后缀）。

    - 压缩过程中压缩包超过 MAX_ZIP_SIZE 立即中止并删除半成品；
    - 引用之间存在重复文件名（zip 内路径冲突）时报错；
    - 目标名已存在/不安全时报错。成功返回 zip 的引用与详情。
    """
    if agent is None:
        return {"result": "[打包失败：无法获取会话上下文]", "no_compress": True}
    refs = [str(r).strip() for r in (refs or []) if str(r).strip()]
    if not refs:
        return {"result": "[打包失败：refs 不能为空]", "no_compress": True}
    # 解析全部引用
    items = []
    for ref in refs:
        try:
            p = Path(agent.resolve_ref(ref))
        except KeyError:
            return {"result": f"[打包失败：没有找到引用 {ref}]", "no_compress": True}
        if not p.is_file():
            return {"result": f"[打包失败：引用 {ref} 指向的文件不存在]", "no_compress": True}
        items.append((p.name, p, ref))
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
    part.rename(target)
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
    src.rename(target)
    # 旧引用随文件移动失效，登记含文件夹的新引用（后续工具按新引用定位）
    agent.ref_map.pop(ref, None)
    base_ref = ref.split("/")[-1]
    new_ref = "/".join([*parts, base_ref]) if parts else base_ref
    agent.ref_map[new_ref] = str(target)
    return {"result": (f"已把 {ref} 移动到 {'/'.join(parts) + '/' if parts else 'history 根目录'}，"
                       f"新引用为 {new_ref}（旧引用已失效）"),
            "ref": new_ref, "no_compress": True}
