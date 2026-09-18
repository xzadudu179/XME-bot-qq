import json
import os
from nonebot.log import logger
from xme.xmetools import dicttools

def read_from_path(path) -> dict | list:
    try:
        with open(path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except Exception:
        return None


def save_to_path(path, data, ensure_ascii=False, indent: int | str | None=None):
    # 先写同目录临时文件再原子替换：写入中途崩溃/断电不会留下截断损坏的文件
    tmp_path = f"{path}.tmp"
    with open(tmp_path, 'w', encoding='utf-8') as file:
        file.write(json.dumps(data, ensure_ascii=ensure_ascii, indent=indent))
    os.replace(tmp_path, path)

def change_json(path: str, *keys, set_method=lambda v: v, delete=False):
    """修改 json 内容

    Args:
        path (str): json 路径
        set_method (function, optional): 设置修改方法. Defaults to lambdav:v.
    """
    c = read_from_path(path)
    if c is None:
        # 文件缺失/损坏时不落盘：用空结构覆盖会把损坏"洗白"，记日志留给人工处理
        logger.error(f"change_json 拒绝修改无法读取的 {path}（缺失或损坏）")
        return
    dicttools.set_value(*keys, search_dict=c, set_method=set_method, delete=delete)
    save_to_path(path, c)

def get_json_value(path: str, *keys, default=None):
    data = read_from_path(path)
    return dicttools.get_value(*keys, search_dict=data, default=default)

