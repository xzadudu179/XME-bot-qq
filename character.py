# import config
from xme.xmetools import jsontools
from xme.xmetools.randtools import str_choice
from xme.xmetools import dicttools
import config
import os
# 其实这就是 i18n
CHARACTER = 'Deon'

items = os.listdir("./characters/")

def get_character(default='XME', target='') -> dict:
    target = target if target != '' else CHARACTER
    try:
        chacs = jsontools.read_from_path(f"./characters/{target}.json")
    except:
        chacs = False
    result = chacs if chacs else False
    if target == 'XME' and not result:
        return {}
    # 如果没有查询到且角色不是 XME，切换为 XME 再查询
    return result if result else get_character(default=default, target='XME')

def get_character_item(*keys: str, character: str="", default="[NULL]", search_dict: dict | None=None):
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
        result = dicttools.get_value(*keys, search_dict=search_dict)
    except KeyError:
        if character != 'XME' and CHARACTER != 'XME':
            item = get_character_item(*keys, character='XME', default=default)
            return item
        result = default
    return result

def get_message(*keys: str, default: str="[bot 未输出任何消息 请私信 bot 并发送相关聊天记录/图片报告问题 xwx (遇到这件事请截图并且暴打九九)]", character: str="", **kwargs) -> str:
    """获取 bot 角色字典消息

    Args:
        *keys (str): 消息键
        default (str, optional): 找不到值时返回的默认值. Defaults to "[bot 未输出任何消息 请私信 bot 并发送相关聊天记录/图片报告问题 xwx (遇到这件事请截图并且暴打九九)]".
        character (str, optional): 指定的角色名. Defaults to "".
        **kwargs: 格式化参数

    Returns:
        str: 消息字符串
    """
    try:
        result = get_character_item(*keys, character=character, default=default)
    except:
        return default

    result = str_choice(result)
    # if len(kwargs) < 1:
    #     return str(result).format()
    # 格式化参数文本
    for k, v in kwargs.items():
        if type(v) == list:
            for i, item in enumerate(v):
                if type(item) == int:
                    v[i] = f"{item:,}"
        elif type(v) == int:
            v = f"{v:,}"
        kwargs[k] = v
    feedbacks = get_character_item("bot_info", "feedbacks")
    # print(feedbacks)
    try:
        return str(result).format(
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
            cmd_sep=config.COMMAND_START[0]
        )
    except KeyError as ex:
        print(f"keyerror: {ex}")
        return str(result)

