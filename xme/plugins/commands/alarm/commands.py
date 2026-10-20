"""`/alarm` 指令入口：设置（时间+名字）/ list 查看 / cancel 取消（薄层）。"""
from nonebot import CommandSession

from xme.xmetools import timetools
from xme.xmetools.msgtools import send_session_msg
from xme.xmetools.plugintools import on_command

from . import __plugin_name__, alias
from .reminders import (cancel_reminder, list_reminders, not_friend_hint, register_reminder,
                        toggle_pause_reminder)

# 管理子命令（英文不区分大小写，中文按原样匹配）
_LIST_WORDS = ("list", "ls", "列表", "查看")
_CANCEL_WORDS = ("cancel", "rm", "del", "取消", "删除")
# 暂停/继续共用一个指令名：同一个词来回切换（跑着的暂停、暂停的继续）
_PAUSE_WORDS = ("pause", "暂停", "p")


@on_command(__plugin_name__, aliases=alias, only_to_me=False, permission=lambda _: True)
async def _(session: CommandSession):
    """`.alarm 时间 名字` 设置；`list` 查看；`cancel/del 编号` 取消；`pause 编号` 暂停/继续循环计时器。"""
    arg_text = session.current_arg_text.strip()
    head = arg_text.split(" ")[0].lower()
    if head in _LIST_WORDS or not arg_text:
        return await send_session_msg(session, list_reminders(session.event.user_id), tips=True)
    if head in _CANCEL_WORDS:
        _, _, target = arg_text.partition(" ")
        _, reply = cancel_reminder(session.event.user_id, target)
        return await send_session_msg(session, reply, tips=True)
    if head in _PAUSE_WORDS:
        _, _, target = arg_text.partition(" ")
        _, reply = toggle_pause_reminder(session.event.user_id, target)
        return await send_session_msg(session, reply, tips=True)
    parsed = timetools.parse_leading_time(arg_text)
    name = arg_text[parsed.consumed:].strip()
    ok, reply = await register_reminder(session.bot, session.event, session.event.user_id, parsed, name)
    if ok:
        reply += await not_friend_hint(session.bot, session.event.user_id)
    return await send_session_msg(session, reply, tips=True)
