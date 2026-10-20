from nonebot import get_bot, NoneBot
from nonebot import SenderRoles
from xme.xmetools.jsontools import get_json_value
from nonebot.typing import PermissionPolicy_T
from config import BOT_SETTINGS_PATH
from nonebot.session import BaseSession
from nonebot.command import CommandSession
from argparse import ArgumentParser
from nonebot.argparse import ParserExit
from character import get_message
import json
import os
import time
from traceback import format_exc
from xme.xmetools.debugtools import debug_msg
from nonebot.log import logger
from functools import wraps
from config import GROUPS_WHITELIST, MIN_GROUP_MEMBER_COUNT, NICKNAME, SUPERUSERS

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
    ignore_member_count_groups = get_json_value(BOT_SETTINGS_PATH, "ignore_member_count_groups", default=[])
    if group['group_id'] in ignore_member_count_groups:
        return True
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

_settings_cache: dict | None = None
_settings_mtime = -1.0


async def get_settings():
    """读取 bot 设置（_botsettings.json），按 mtime 缓存并容忍缺失键。

    该函数挂在消息预处理器上、每条消息都会调用，不能每次都同步读盘；
    文件损坏/缺失时返回空 dict（缺键用 .get 取默认值），不再向每条消息抛异常。
    """
    global _settings_cache, _settings_mtime
    try:
        mtime = os.path.getmtime(BOT_SETTINGS_PATH)
    except OSError:
        mtime = -1.0
    if _settings_cache is None or mtime != _settings_mtime:
        try:
            with open(BOT_SETTINGS_PATH, 'r', encoding='utf-8') as jsonfile:
                _settings_cache = json.load(jsonfile)
        except Exception:
            logger.warning(f"读取 {BOT_SETTINGS_PATH} 失败，本次按空设置处理")
            _settings_cache = {}
        _settings_mtime = mtime
    return _settings_cache

async def get_stranger_name(user_id, default=None):
    try:
        result = (await get_bot().api.get_stranger_info(user_id=user_id))['nickname']
    except Exception:
        return default
    return result

# 好友列表缓存时长（秒）：避免每条私聊都拉一次好友列表 API
FRIEND_CACHE_TTL = 300
_friend_cache: dict[int, tuple[float, set[int]]] = {}   # self_id → (过期时间, 好友 id 集)


async def is_friend(bot: NoneBot, user_id: int) -> bool:
    """用户是否为 bot 好友（带 TTL 缓存；SUPERUSERS 视为好友；列表拉取失败按好友处理）。

    口径与 private_messages 的好友校验一致：加好友之前的陌生人消息不该进上下文。
    """
    if user_id in SUPERUSERS:
        return True
    now = time.time()
    cached = _friend_cache.get(bot.self_id)
    if cached is None or cached[0] <= now:
        try:
            friends = await bot.get_friend_list()
        except Exception:
            logger.warning(f"拉取好友列表失败，本次按好友处理 user_id={user_id}")
            return True
        cached = (now + FRIEND_CACHE_TTL, {int(f.get("user_id") or 0) for f in friends})
        _friend_cache[bot.self_id] = cached
    return user_id in cached[1]


def bot_name_prefixes() -> list[str]:
    """bot 名字/昵称清单（角色名 + config.NICKNAME，即指令分发实际剥离的口径）。"""
    names = {get_message("bot_info", "name")}
    nickname = NICKNAME
    if not isinstance(nickname, list):
        nickname = [nickname]
    names.update(str(n) for n in nickname if n)
    return [n for n in names if n]


# strip_bot_name 要剪掉的开头字符：空白与常见的连接标点（「漠月，2小时后…」）
_NAME_TRIM_CHARS = " \t\n　，,。.、！？!?~～…:：;；\"'“”‘’"


def strip_bot_name(text: str) -> str:
    """去掉正文开头的 bot 名字/昵称与紧随其后的标点（「漠月，/s」→「/s」）。

    回复别人的消息时框架不会自动剥昵称（消息以 reply 段开头），所以调用方需要自己剥一下。
    """
    text = text.lstrip(_NAME_TRIM_CHARS)
    for name in bot_name_prefixes():
        while text.startswith(name):
            text = text[len(name):].lstrip(_NAME_TRIM_CHARS)
    return text

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
        debug_msg(f"action={action} kwargs={kwargs}")
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