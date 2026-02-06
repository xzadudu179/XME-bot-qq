from nonebot import get_bot, NoneBot
from nonebot import SenderRoles
from nonebot.typing import PermissionPolicy_T
from nonebot.session import BaseSession
from nonebot.command import CommandSession
from argparse import ArgumentParser
from nonebot.argparse import ParserExit
from character import get_message
import json
from traceback import format_exc
from xme.xmetools.debugtools import debug_msg
from nonebot.log import logger
from functools import wraps
from config import GROUPS_WHITELIST, MIN_GROUP_MEMBER_COUNT

class XmeArgumentParser(ArgumentParser):
    def __init__(self, *args, **kwargs):
        self.session = kwargs.pop('session', None)
        self.exit_mssage = "参数不足或不正确，请使用 --help 参数查询使用帮助"
        super().__init__(*args, **kwargs)

    def _session_finish(self, message):
        if self.session and isinstance(self.session, CommandSession):
            self.session.finish(message)

    def _print_message(self, message, file=None):
        # do nothing
        pass

    def exit(self, status=0, message=None):
        raise ParserExit(status=status, message=message)


    def parse_args(self, args=None, namespace=None):
        try:
            return super().parse_args(args=args, namespace=namespace)
        except ParserExit as e:
            if e.status == 0:
                # --help
                self._session_finish(self.usage or self.format_help())
            else:
                self._session_finish(self.exit_mssage)

async def get_user_name(user_id, group_id=None, default=None):
    if group_id is not None:
        return await get_group_member_name(group_id=group_id, user_id=user_id, card=True, default=default)
    return await get_stranger_name(user_id=user_id, default=default)

def is_group_member_count_legal(group):
    if group['member_count'] >= MIN_GROUP_MEMBER_COUNT or group['group_id'] in GROUPS_WHITELIST:
        return True
    return False

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
    except Exception:
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
    except Exception:
        return default
    return result

async def bot_call_action(bot: NoneBot, action: str, error_action=None, **kwargs):
    """bot 调用方法

    Args:
        bot (NoneBot): bot 实例
        action (str): 方法名
        error_action (function, optional): 出现错误时调用的异步函数. Defaults to None.

    Returns:
        Any: 调用结束返回的值
    """
    try:
        # debug_msg("call action")
        return await bot.api.call_action(action=action, **kwargs)
    except Exception as ex:
        logger.error(f"bot 调用接口出现错误： {ex}")
        logger.exception(format_exc())
        if error_action is None:
            raise ex
        logger.error("error action")
        return error_action

async def get_group_name(group_id, default=None):
    try:
        result = (await get_bot().api.get_group_info(group_id=group_id))['group_name']
    except Exception:
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
            debug_msg("perm func", perm_func(sender))
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