# import config
from xme.xmetools import json_tools
from xme.xmetools import random_tools
from xme.xmetools import dict_tools
import os
# 其实这就是 i18n
CHARACTER = 'Deon'

items = os.listdir("./characters/")

def get_character(default='XME', target='') -> dict:
    target = target if target != '' else CHARACTER
    try:
        chacs = json_tools.read_from_path(f"./characters/{target}.json")
    except:
        chacs = False
    result = chacs if chacs else False
    if target == 'XME' and not result:
        return {}
    # 如果没有查询到且角色不是 XME，切换为 XME 再查询
    return result if result else get_character(default=default, target='XME')


def get_item(*keys: str, character: str="", default="[NULL]", search_dict: dict | None=None):
    """得到角色字典对应键的值，如果找不到对应角色的值会返回 XME 的，还找不到则返回 default 值

    Args:
        *keys (str): 指定的键，会从左到右查找，类似于 dict[key0][key1][key2]...
        character (str, optional): 指定的角色名. Defaults to "".
        default (str, optional): 找不到值时返回的默认值. Defaults to "[NULL]".
        search_dict (dict | None, optional): 用于搜索的字典. Defaults to None.

    Returns:
        Any: 字典键对应的值
    """
    if not search_dict:
        if not character:
            search_dict = get_character()
        else:
            search_dict = get_character(target=character)
    try:
        result = dict_tools.get_value(*keys, search_dict=search_dict)
    except KeyError:
        if character != 'XME' and CHARACTER != 'XME':
            item = get_item(*keys, character='XME', default=default)
            return item
        result = default
    return result

def get_message(*keys: str, default: str="[NULL]", character: str="") -> str:
    """获取 bot 输出消息

    Args:
        *key (str): 消息键
        default (str, optional): 找不到值时返回的默认值. Defaults to "[NULL]".
        character (str, optional): 指定的角色名. Defaults to "".

    Returns:
        str: 消息字符串
    """
    try:
        result = get_item(*keys, character=character, default=default)
        if type(result) == list:
            result = random_tools.rand_str(*result)
        return str(result)
    except:
        return default