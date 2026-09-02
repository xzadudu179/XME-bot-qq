from nonebot import log
import os
import base64
from pathlib import Path
from datetime import datetime
import shutil
import json
from xme.xmetools.typetools import try_parse
from xme.xmetools import jsontools
from xme.xmetools.texttools import hash_text, regex_search

def _create_file_ref(dir_name, head: str, file_name: str, agent=None,
) -> tuple[Path, str]:
    path = Path(f"./data/temp/{dir_name}")
    path.mkdir(parents=True, exist_ok=True)

    used = set()
    ref_map = agent.REF_MAP if agent is not None else None

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
    agent.REF_MAP[ref] = file_name

    return path, ref


def text_to_file(text: str, dir_name, agent=None) -> dict:
    HEAD = "text_"

    file_id = hash_text(text)
    file_name = file_id + ".txt"

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
        "preview": text[:200],
    }


def dict_to_file(d: dict, dir_name, prefix="", agent=None,
) -> dict:
    HEAD = "json_"

    file_id = hash_text(str(d))
    file_name = prefix + file_id + ".json"

    path, ref = _create_file_ref(dir_name, HEAD, file_name, agent)

    with open(path / file_name, "w", encoding="utf-8") as file:
        file.write(json.dumps(d, ensure_ascii=False))

    return {
        "file_name": file_name,
        "ref": ref,
        "path": path,
    }


# def text_to_file(text: str, agent, dir_name) -> dict:
#     HEAD = "text_"
#     file_id = hash_text(text)
#     file_name = file_id + ".txt"
#     path = Path(f"./data/temp/{dir_name}")
#     # file_count = len([f for f in path.iterdir() if f.is_file()])
#     used = []
#     ref_map = agent.REF_MAP
#     if ref_map is not None:
#         for k in ref_map.keys():
#             num = try_parse(k.replace(HEAD, ""), int)
#             if num is None:
#                 continue
#             used.append(num)
#     used = set(used)
#     n = 1
#     while n in used:
#         n += 1
#     path.mkdir(parents=True, exist_ok=True)
#     with open(path / f"{file_name}", 'w', encoding='utf-8') as file:
#         file.write(text)
#     agent.REF_MAP[f"{HEAD}{n}"] = file_name
#     return {
#         "file_name": file_name,
#         "ref": f"{HEAD}{n}",
#         "total_len": len(text),
#         "total_line_count": text.replace("\r\n", "\n").replace("\r", "\n").count("\n"),
#         "preview": text[:200],
#     }

# def dict_to_file(d: dict, dir_name, agent, prefix = "") -> dict:
#     HEAD = "json_"
#     file_id = hash_text(str(d))
#     file_name = prefix + file_id + ".json"
#     path = Path(f"./data/temp/{dir_name}")
#     # path = f"./data/temp/{dir_name}/{file_name}"
#     path.mkdir(parents=True, exist_ok=True)
#     used = []
#     ref_map = agent.REF_MAP
#     if ref_map is not None:
#         for k in ref_map.keys():
#             num = try_parse(k.replace(HEAD, ""), int)
#             if num is None:
#                 continue
#             used.append(num)
#     used = set(used)
#     n = 1
#     while n in used:
#         n += 1
#     with open(path / file_name, 'w', encoding='utf-8') as file:
#         # file.write(text)
#         file.write(json.dumps(d,ensure_ascii=False))
#     agent.REF_MAP[f"{HEAD}{n}"] = file_name
#     return {
#         "file_name": file_name,
#         "ref": f"{HEAD}{n}",
#         "path": path
#     }

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