"""AI 会话的「发起窗口」登记与守卫：只有发起会话的那个聊天才能与会话交互。

一个用户的 AI 会话开在哪个聊天（下称窗口），只有该窗口里的消息才允许并入或中断它：
群聊按群号比对，私聊两侧都算「私聊窗口」。跨窗口的操作一律不进上下文，由本模块
统一给出提示——普通会话提示会话仍在运行，共享会话给出定位信息，让用户回到那边继续。

本模块同时是「运行中会话」的唯一登记表（原先散在 __init__ 的 curr_sessions 已迁入），
并对外提供两种复用方式：
- 直接调用 same_chat / place_name / other_window_reply 做判定与文案；
- 用 only_own_window 装饰器给处理器加上窗口守卫（与 message_preprocessor 同风格的叠加用法）。
"""
from dataclasses import dataclass
from functools import wraps

from character import get_message

from .constants import __plugin_name__


@dataclass
class RunningTurn:
    """一个用户正在运行中的 AI 会话（含它开在哪个窗口）。

    ready 为 False 表示 talk() 刚登记、上下文尚未就绪（此时任何 /ai 都只回提示）；
    insert_key 为空表示该会话未开启插入模式。
    """
    user_id: int
    group_id: int | None = None      # 发起窗口：群号，私聊为 None
    shared: bool = False             # 是否共享会话
    display: str = ""                # 展示名（共享会话为群号码，普通会话为会话名）
    insert_key: str = ""             # 插入队列键（未开启插入模式时为空）
    insert_enabled: bool = False
    ready: bool = False


_turns: dict[int, RunningTurn] = {}


def mark_running(user_id: int) -> None:
    """登记「该用户有一个 AI 会话正在启动」，避免启动期间被重复发起。"""
    _turns[int(user_id)] = RunningTurn(user_id=int(user_id))


def register(user_id: int, *, group_id, shared: bool, display: str,
             insert_key: str = "", insert_enabled: bool = False) -> None:
    """补全运行中会话的窗口与插入信息（talk() 建好 AIHelper 后调用）。

    无论是否开启插入模式都要登记：窗口判定依赖这里的 group_id。
    """
    _turns[int(user_id)] = RunningTurn(
        user_id=int(user_id), group_id=group_id, shared=bool(shared),
        display=display or "", insert_key=insert_key or "",
        insert_enabled=bool(insert_enabled), ready=True)


def clear(user_id: int) -> RunningTurn | None:
    """注销运行中会话（talk() 结束时调用），返回被注销的会话信息供收尾使用。"""
    return _turns.pop(int(user_id), None)


def get(user_id: int) -> RunningTurn | None:
    """取该用户运行中的会话；没有则返回 None。"""
    return _turns.get(int(user_id))


def same_chat(started_group_id, group_id) -> bool:
    """两个聊天是否为同一个窗口：群聊按群号相等，私聊两侧都无群号。"""
    return started_group_id == group_id


async def place_name(group_id) -> str:
    """窗口的可读名称：群聊为「群「群名」」（取不到群名时回落「群 群号」），私聊为「私聊窗口」。"""
    if group_id is None:
        return "私聊窗口"
    from xme.xmetools.bottools import get_group_name
    name = await get_group_name(group_id)
    return f"群「{name}」" if name else f"群 {group_id}"


async def other_window_reply(*, shared: bool, group_id) -> str:
    """跨窗口操作的统一提示：共享会话给定位信息，普通会话提示会话仍在运行。"""
    if shared:
        return get_message("plugins", __plugin_name__, "session_other_chat",
                           place=await place_name(group_id))
    return get_message("plugins", __plugin_name__, "ai_session_on")


def _locate(args):
    """从处理器入参里找出 (session, event, bot)：兼容 session 式与 (bot, event, ...) 式。"""
    session = event = bot = None
    for arg in args:
        if event is None and hasattr(arg, "user_id") and hasattr(arg, "group_id"):
            event = arg
        elif session is None and hasattr(arg, "event"):
            session = arg
        elif bot is None and hasattr(arg, "call_action"):
            bot = arg
    if session is not None and event is None:
        event = getattr(session, "event", None)
    return session, event, bot


def only_own_window(reply=None):
    """装饰器：仅当消息属于该用户 AI 会话的发起窗口时才执行被装饰的处理器。

    与 message_preprocessor 同风格的叠加用法，供任何「只在会话窗口内生效」的
    功能复用，不必各自比对群号：

        @on_command("xxx")
        @only_own_window()
        async def handler(session, ...):
            ...

    当前消息来自别的窗口时不执行处理器，改为发送提示并返回 False；reply 可传
    async callable(session, turn, event) 自定义文案（缺省用 other_window_reply）。
    该用户没有运行中的会话、或拿不到事件对象时不做限制，正常执行处理器。
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            session, event, bot = _locate(args)
            if event is None:
                return await func(*args, **kwargs)
            turn = get(getattr(event, "user_id", 0) or 0)
            if turn is None or same_chat(turn.group_id, getattr(event, "group_id", None)):
                return await func(*args, **kwargs)
            text = await (reply(session, turn, event) if reply is not None
                          else other_window_reply(shared=turn.shared, group_id=turn.group_id))
            if session is not None:
                from xme.xmetools.msgtools import send_session_msg
                await send_session_msg(session, text)
            elif bot is not None:
                from xme.xmetools.msgtools import send_event_msg
                await send_event_msg(bot, event, text)
            return False
        return wrapper
    return decorator
