import re

from nonebot import log
import os
import base64
import hashlib
from pathlib import Path
from datetime import datetime
import shutil
import json
from xme.xmetools.typetools import try_parse
from xme.xmetools import jsontools
from xme.xmetools.texttools import hash_text, regex_search
from enum import Enum
from keys import generate_file_token, DOMAIN

def _create_file_ref(dir_name, head: str, file_name: str, agent=None,
) -> tuple[Path, str]:
    path = Path(f"./data/temp/{dir_name}")
    path.mkdir(parents=True, exist_ok=True)

    used = set()
    ref_map = agent.ref_map if agent is not None else None

    if ref_map is not None:
        for k in ref_map:
            if not k.startswith(head):
                continue

            num = try_parse(k[len(head):], int)
            if num is not None:
                used.add(num)

    n = 1
    while n in used:
        n += 1

    ref = f"{head}{n}"
    agent.ref_map[ref] = file_name

    return path, ref

def get_file_size(path: str | Path):
    """得到文件路径下文件的大小（字节数）

    Args:
        path (str | Path): path

    Returns:
        int: 字节数
    """
    path = Path(path)
    return path.stat().st_size

class FileType(Enum):
    EMPTY = "空文件"
    IMAGE = "图片文件"
    PDF = "PDF文件"
    ARCHIVE = "压缩文件"
    BINARY = "二进制文件"
    TEXT = "文本文件"

def detect_file_type(path: str | Path) -> FileType:
    path = Path(path)
    with path.open("rb") as f:
        data = f.read(8192)

    if not data:
        return FileType.EMPTY

    # 常见文件 Magic Number
    signatures = {
        b"\x89PNG\r\n\x1a\n": FileType.IMAGE,
        b"\xff\xd8\xff": FileType.IMAGE,
        b"GIF87a": FileType.IMAGE,
        b"GIF89a": FileType.IMAGE,
        b"%PDF": FileType.PDF,
        b"PK\x03\x04": FileType.ARCHIVE,  # zip/docx/xlsx/pptx 等
        b"\x1f\x8b": FileType.ARCHIVE,    # gzip
        b"7z\xbc\xaf\x27\x1c": FileType.ARCHIVE,
    }

    for signature, file_type in signatures.items():
        if data.startswith(signature):
            return file_type

    # NUL 字节基本可以认为是二进制
    if b"\x00" in data:
        return FileType.BINARY
    # 控制字符比例
    control_count = sum(
        byte < 32 and byte not in (9, 10, 13)
        for byte in data
    )
    if control_count / len(data) > 0.01:
        return FileType.BINARY
    return FileType.TEXT

def get_local_file_url(path: str):
    """将本地文件变为限时 url 链接（TTL 30s）

    Args:
        path (str): 本地文件路径

    Raises:
        ValueError: 文件层级低于项目层级

    Returns:
        str: 链接
    """
    path = Path(path).absolute()
    root = Path(".").absolute()
    if not path.is_relative_to(root):
        ValueError(f"文件 {path} 层级不能低于项目层级 {root}")
    token = generate_file_token(path)
    # 有 30秒的过期时间
    url = f"http://{DOMAIN}/file/{token}"
    return url


def is_safe_ref(ref: str, prefixes: tuple[str, ...] = ("history_", "text_", "json_")) -> bool:
    """校验引用是否为 <白名单前缀><ASCII数字> 形式（防路径穿越）。

    例如 history_1 / text_3 / json_2 是安全的；"/../../x"、"history_1/../x"、
    "history_.."、unicode 数字等都不是。
    """
    if not isinstance(ref, str):
        return False
    for prefix in prefixes:
        if ref.startswith(prefix):
            rest = ref[len(prefix):]
            return rest.isascii() and rest.isdigit()
    return False


def is_safe_file_name(name: str) -> bool:
    """判断文件名是否安全：非空、非 . / ..、不含路径分隔符。"""
    if not isinstance(name, str) or not name or name in (".", ".."):
        return False
    if "/" in name or chr(92) in name:
        return False
    return True


def is_safe_custom_name(name: str) -> bool:
    """判断自定义文件名是否安全：非空、不以点开头、不含路径分隔符/.. /空格/特殊符号。

    允许 unicode 字母数字、下划线 _、连字符 -、点 .（作为扩展名分隔）。
    中文等 unicode 文字也允许（例如 "笔记.md"）。
    """
    if not isinstance(name, str) or not name:
        return False
    if len(name) > 100:
        return False
    if name in (".", "..") or name.startswith("."):
        return False
    if "/" in name or chr(92) in name or ".." in name:
        return False
    for ch in name:
        if ch.isalnum() or ch in ("_", "-", "."):
            continue
        return False
    return True


def safe_join(base, name: str):
    """把文件名安全地拼接到目录下；不安全（含分隔符/穿越）抛出 ValueError。"""
    if not is_safe_file_name(name):
        raise ValueError(f"不安全的文件引用：{name!r}")
    return Path(base) / name


def dir_usage(folder) -> dict:
    """统计文件夹内的文件数量与总大小（字节）。"""
    folder = Path(folder)
    count = 0
    size = 0
    if folder.is_dir():
        for item in folder.iterdir():
            if item.is_file():
                count += 1
                try:
                    size += item.stat().st_size
                except OSError:
                    pass
    return {"count": count, "size": size}


def history_file_name(ref: str) -> str | None:
    """把引用映射为安全的文件名；非法引用返回 None。

    - history_<数字>（旧约定）→ history_<数字>.tmp；
    - 自定义安全文件名（如 notes.md / 笔记）→ 原样作为文件名；
    - 其余（含路径、特殊符号、重复风险字符）→ None。
    """
    if is_safe_ref(ref, ("history_",)):
        return f"{ref}.tmp"
    if is_safe_custom_name(ref):
        return ref
    return None


def decode_text(data: bytes) -> str:
    """把字节解码为文本：utf-8 优先，其次 gb18030（中文常见），最后 latin-1 兜底（永不失败）。"""
    for encoding in ("utf-8", "gb18030"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("latin-1")


def bytes_to_file(data: bytes, dir_name, suffix: str = ".bin", agent=None) -> dict:
    """把字节内容写入用户 temp 文件夹并分配引用；按内容哈希命名。

    文件名 = 内容 sha256 前 16 位 + suffix；引用前缀为 file_。
    相同内容的文件已存在时抛 FileExistsError（异常值为已存在文件的文件名），
    与 text_to_file 的查重语义一致——是否复用由调用方决定，本函数不做复用。
    返回 {file_name, ref, size, path}。
    """
    file_id = hashlib.sha256(data).hexdigest()[:16]
    file_name = file_id + (suffix or ".bin")
    path = Path(f"./data/temp/{dir_name}/{file_name}")
    if path.is_file():
        raise FileExistsError(file_name)
    path, ref = _create_file_ref(dir_name, "file_", file_name, agent)
    with open(path / file_name, "wb") as file:
        file.write(data)
    return {
        "file_name": file_name,
        "ref": ref,
        "size": len(data),
        "path": str(path / file_name),
    }


def text_to_file(text: str, dir_name, agent=None) -> dict:
    HEAD = "text_"

    file_id = hash_text(text)
    file_name = file_id + ".txt"
    path = Path(f"./data/temp/{dir_name}/{file_name}")
    if path.is_file():
        raise FileExistsError(f"该文本所能够转换的文件({file_name})已经存在")
    path, ref = _create_file_ref(dir_name, HEAD, file_name, agent)

    with open(path / file_name, "w", encoding="utf-8") as file:
        file.write(text)

    return {
        "file_name": file_name,
        "ref": ref,
        "total_len": len(text),
        "total_line_count": (
            text.replace("\r\n", "\n")
                .replace("\r", "\n")
                .count("\n")
        ),
        "path": path,
        "preview": text[:200],
    }


def dict_to_file(d: dict, dir_name, prefix="", agent=None,
) -> dict:
    HEAD = "json_"

    file_id = hash_text(str(d))
    file_name = prefix + file_id + ".json"
    path = Path(f"./data/temp/{dir_name}/{file_name}")
    if path.is_file():
        raise FileExistsError(f"该字典所能够转换的文件({file_name})已经存在")
    path, ref = _create_file_ref(dir_name, HEAD, file_name, agent)
    text = json.dumps(d, ensure_ascii=False)
    with open(path / file_name, "w", encoding="utf-8") as file:
        file.write(text)

    return {
        "file_name": file_name,
        "ref": ref,
        "total_len": len(text),
        "path": path,
        "preview": text[:200],
    }

def cleanup_old_backups(
        backup_root: Path,
        keep: int = 100
    ):
    if not backup_root.exists():
        return
    backups = sorted(
        (p for p in backup_root.iterdir() if p.is_dir()),
        key=lambda p: p.name
    )
    excess = len(backups) - keep
    if excess <= 0:
        return
    for old in backups[:excess]:
        shutil.rmtree(old)

def backup_data_dir(
        data_dir: Path = Path("data"),
        backup_root: Path = Path(".backup"),
        max_backups: int = 500
    ) -> Path:
    """
    将 data 目录备份到 .backup/datas-YYYY-MM-DD_HH-MM-SS

    返回：备份目录路径
    """
    data_dir.mkdir(parents=True, exist_ok=True)
    backup_root.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_dir = backup_root / ("datas-" + timestamp)
    shutil.copytree(data_dir, backup_dir)
    cleanup_old_backups(backup_root, keep=max_backups)
    return backup_dir


def search_json(s, path, *key_names, d=None, search_func=None, **kwargs):
    if d is None:
        d: dict = jsontools.read_from_path(path)
    if not isinstance(d, dict):
        raise ValueError("不能直接在列表里调用 search_json")
    # 需要有 results
    item_list: list = d.get("results", None)
    if item_list is None or not isinstance(item_list, list):
        raise ValueError("传入字典没有 results 列表")
    if len(item_list) < 1:
        return []
    search_list = []
    for i in item_list:
        for k in key_names:
            # 空的忽略了
            if not isinstance(i, dict):
                i = ""
                break
        i = i.get(k, "")
        item = i
        if not isinstance(item, str):
            raise ValueError("不能选择非 str 类型的字段查询")
        search_list.append(item)
    if search_func is None:
        return [x[0] for x in regex_search(s, search_list)]
    else:
        # return search_func(s, search_list, threshold=0.7, **kwargs)
        return search_func(s, search_list, **kwargs)

def search_text(s, path, search_func=None, **kwargs):
    text = ""
    with open(path, "r", encoding="utf-8") as file:
        text = file.read()
    if search_func is None:
        pattern = re.compile(s)
        results = pattern.findall(text)
        return results
    else:
        # return search_func(s, search_list, threshold=0.7, **kwargs)
        return search_func(s, text, **kwargs)


def b64_encode_file(file_path):
    with open(file_path, "rb") as f:
        return base64.b64encode(f.read()).decode()

def delete_files_in_folder(folder_path):
    """删除文件夹内的所有文件

    Args:
        folder_path (str): 文件夹路径
    """
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        if not os.path.isfile(file_path):
            continue
        os.remove(file_path)
        log.logger.info(f"删除文件: {file_path}")

def has_file(path) -> bool:
    """判断是否有文件存在

    Args:
        path (str): 路径

    Returns:
        bool: 是否存在
    """
    if os.path.exists(path) and os.path.isfile(path):
        return True
    return False

def clear_temp(folder="./data/images/temp"):
    """
    清除缓存"""
    log.logger.info("正在删除缓存文件")
    files = [f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))]
    for f in files:
        log.logger.info(f"正在删除 \"{f}\"...")
        os.remove(folder + '/' + f)

def clear_temps(folders=["./data/images/temp", "./data/temp"]):
    for f in folders:
        clear_temp(f)