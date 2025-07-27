from nonebot import get_bot, NoneBot
from nonebot import SenderRoles
from nonebot.typing import PermissionPolicy_T
from nonebot.session import BaseSession
from character import get_message
import json
from functools import wraps

async def get_group_member_name(group_id, user_id, card=False, default=None):
    """得到群员名

    Args:
        group_id (int): 群 id
        user_id (int): 用户 id
        card (bool, optional): 是否优先获取群名片. Defaults to False.

    Returns:
        str: 获取结果
    """
    try:
        result = await get_bot().api.get_group_member_info(group_id=group_id, user_id=user_id)
    except:
        return default
    if card:
        result = result['card'] if result['card'] else result['nickname']
    else:
        result = result['nickname']
    return result

async def get_settings():
    with open("./data/_botsettings.json", 'r', encoding='utf-8') as jsonfile:
        settings = json.load(jsonfile)
    return settings

async def get_stranger_name(user_id, default=None):
    try:
        result = (await get_bot().api.get_stranger_info(user_id=user_id))['nickname']
    except:
        return default
    return result

async def bot_call_action(bot: NoneBot, action: str, error_action=None, *error_action_args, **kwargs):
    """bot 调用方法

    Args:
        bot (NoneBot): bot 实例
        action (str): 方法名
        error_action (function, optional): 出现错误时调用的异步函数. Defaults to None.

    Returns:
        Any: 调用结束返回的值
    """
    try:
        return await bot.api.call_action(action=action, **kwargs)
    except Exception as ex:
        print(f"bot 调用接口出现错误： {ex}")
        if not error_action:
            raise ex
        return error_action(bot, *error_action_args)

async def get_group_name(group_id, default=None):
    try:
        result = (await get_bot().api.get_group_info(group_id=group_id))['group_name']
    except:
        return default
    return result


def permission(perm_func: PermissionPolicy_T, permission_help: str = "未知", no_perm_message: str = "", no_perm_result=None, silent=False):
    # no_perm_message = no_perm_message
    # global no_perm_message
    def decorator(func):
        @wraps(func)
        async def wrapper(session: BaseSession, *args, **kwargs):
            sender = await SenderRoles.create(session.bot, session.event)
            msg = no_perm_message
            if not msg:
                msg = get_message("config", "no_permission", permission=permission_help)
            print("perm func", perm_func(sender))
            if perm_func(sender):
                result = await func(session, *args, **kwargs)
            else:
                from xme.xmetools.msgtools import send_session_msg
                if not silent:
                    await send_session_msg(session, msg)
                result = no_perm_result
            return result
        return wrapper
    return decorator