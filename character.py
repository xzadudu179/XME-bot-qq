from xme.xmetools import jsontools
from xme.xmetools.texttools import replace_formatted
from xme.xmetools.randtools import str_choice
from xme.xmetools import dicttools
from nonebot.message import Message
from functools import lru_cache
import config
import os
# from xme.xmetools.debugtools import debug_msg
from decimal import Decimal
from nonebot.log import logger

CHARACTER = 'Deon'
DEFAULT_CHARACTER = 'Deon'

@lru_cache(maxsize=32)
def _read_character_file(char_name: str) -> dict:
    """读取角色文件并缓存"""
    if not char_name:
        return {}
    try:
        data = jsontools.read_from_path(f"./characters/{char_name}.json")
        return data if isinstance(data, dict) else {}
    except Exception as e:
        logger.debug(f"读取或解析角色文件 \"{char_name}.json\" 失败: {e}")
        return {}

def get_character(default=DEFAULT_CHARACTER, target='') -> dict:
    target = target or CHARACTER
    result = _read_character_file(target)
    if result:
        return result
    if target != default:
        result = _read_character_file(default)
        if result:
            return result
    return {}

def get_character_item(*keys: str, character: str="", default="[NULL]", search_dict: dict | None=None):
    """得到角色字典对应键的值，如果找不到对应角色的值会返回默认的，还找不到则返回 default 值

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
        result = dicttools.get_value(*keys, search_dict=search_dict)
    except KeyError:
        if character != DEFAULT_CHARACTER and CHARACTER != DEFAULT_CHARACTER:
            item = get_character_item(*keys, character=DEFAULT_CHARACTER, default=default)
            return item
        result = default
    return result

def get_message(*keys: str, default: str="[bot 未输出任何消息 请私信 bot 并发送相关聊天记录/图片报告问题 xwx (遇到这件事请截图并且暴打九九)]", character: str="", replace_cq_str=False, **kwargs) -> str:
    """获取 bot 角色字典消息

    Args:
        *keys (str): 消息键
        default (str, optional): 找不到值时返回的默认值. Defaults to "[bot 未输出任何消息 请私信 bot 并发送相关聊天记录/图片报告问题 xwx (遇到这件事请截图并且暴打九九)]".
        character (str, optional): 指定的角色名. Defaults to "".
        replace_cq_str (bool, optional): 是否替换 cq 码. Defaults to False.
        **kwargs: 格式化参数

    Returns:
        str: 消息字符串
    """
    try:
        result = get_character_item(*keys, character=character, default=default)
    except Exception:
        return f"[获取消息错误：无法获取键组为 {keys} 的消息，如用户使用出现该问题，请截图交给九镹（并暴打九镹（？））]"
    if result is None:
            return default
    result = str_choice(result)
    result = character_format(result, **kwargs)
    if replace_cq_str:
        result = result.replace("[", "&#91;").replace("]","&#93;")
    return result

def character_format(message, **kwargs):
    for k, v in kwargs.items():
        if isinstance(v, list):
            for i, item in enumerate(v):
                if isinstance(item, int) or isinstance(item, float) or isinstance(item, Decimal):
                    v[i] = f"{item:,}"
        elif isinstance(v, int) or isinstance(v, float) or isinstance(v, Decimal):
            v = f"{v:,}"
        kwargs[k] = v
    feedbacks = get_character_item("bot_info", "feedbacks")
    try:
        # print(str(result))
        return replace_formatted(
            str(message),
            **kwargs,
            neutral=str_choice(feedbacks['neutral']),
            negative_plus=str_choice(feedbacks['negative_plus']),
            negative=str_choice(feedbacks['negative']),
            positive=str_choice(feedbacks['positive']),
            positive_plus=str_choice(feedbacks['positive_plus']),
            excellent=str_choice(feedbacks['excellent']),
            happy=str_choice(feedbacks['happy']),
            bless=str_choice(feedbacks['bless']),
            disgust=str_choice(feedbacks['disgust']),
            sad=str_choice(feedbacks['sad']),
            shout=str_choice(feedbacks['shout']),
            positive_punc=str_choice(feedbacks['positive_punc']),
            coin_name=get_character_item("user", "coin_name"),
            coin_pronoun=get_character_item("user", "coin_pronoun"),
            bot_name=get_character_item("bot_info", "name"),
            cmd_sep=config.COMMAND_START[0]
        )
    except KeyError as ex:
        logger.warning(f"keyerror: {ex}")
        return str(message)
    except ValueError as ex:
        logger.warning(f"ValueError: {ex}")
        return str(message)