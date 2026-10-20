"""「{时间}[后]提醒我/叫我…」句式入口：群里要叫我（@ 或名字开头），私聊免称呼。

时间有两种格式（见 timetools.parse_leading_time）：相对时长（「5分钟后」）与自然
语句时间（「明天9点」「周三8点」）。命中的消息由本预处理接管——登记计时器、回一句
确认并吞掉消息。群聊里没叫漠月、指令消息、自身消息、指令会话/AI 会话运行中、
私聊陌生人消息一律放行（让路口径与 cmd_suggest 一致）。
"""
import aiocqhttp
from nonebot import NoneBot, message_preprocessor
from nonebot.command import has_running_session
from nonebot.log import logger
from nonebot.message import CanceledException
from nonebot.plugin import PluginManager

from xme.xmetools import cmdtools, timetools
from xme.xmetools.bottools import bot_name_prefixes, is_friend, strip_bot_name
from xme.xmetools.msgtools import send_event_msg
from xme.xmetools.texttools import strip_cq
from xme.xmetools.plugintools import record_plugin_call

from . import __plugin_name__
from .reminders import not_friend_hint, register_reminder


def _strip_bot_names(text: str) -> str:
    """去掉内容首尾出现的 bot 称呼。

    回复别人的消息时框架不会剥（消息以 reply 段开头），这里统一剥掉；
    同时兜住「5分钟后提醒我做饭 漠月」这类称呼落在内容里的写法。
    """
    for name in bot_name_prefixes():
        text = text.strip()
        while text and text.split()[-1] == name:
            text = text[:-len(name)].strip()
        while text.startswith(name):
            text = text[len(name):].strip()
    return text


@message_preprocessor
async def alarm_reminder(bot: NoneBot, event: aiocqhttp.Event, plugin_manager: PluginManager):
    """「{时间}[后]提醒我/叫我…」句式：群里要叫我，私聊免称呼；命中则登记计时器并吞掉消息。"""
    if event.user_id == event.self_id:
        # bot 自己的输出不参与
        return
    # 回复别人的消息时消息以 reply 段开头：框架不会自动剥昵称、也不会置 to_me，
    # 而且 str(event.message) 里带着 [CQ:reply,id=…] 前缀——这里统一自己处理
    raw_text = strip_cq(str(event.message)).strip()
    if not raw_text or cmdtools.is_command(raw_text):
        return
    # 去掉落在正文里（含开头）的 bot 称呼，再解析句式
    # （「漠月5分钟后提醒我做饭」→「5分钟后提醒我做饭」；「5分钟后提醒我做饭漠月」→ 内容「做饭」）
    text = _strip_bot_names(strip_bot_name(raw_text))
    called = text != raw_text          # 剥掉过称呼 = 叫了 bot
    if event.get("group_id") is not None and not (event.get("to_me") or called):
        # 群聊里没叫我：像在和群友说话，不接管
        return
    request = timetools.extract_reminder(text)
    if request is None:
        return
    if has_running_session(event):
        # 指令会话等待参数中（如游戏输入）：消息属于会话参数，让路
        return
    from xme.plugins.commands.ai_helper import aistop
    if aistop.has_running_turn(event.get("group_id"), event.user_id):
        # AI 会话运行中：消息由 aistop 全权接管，让路（口径同 cmd_suggest）
        return
    if event.get("group_id") is None and not await is_friend(bot, event.user_id):
        # 加好友之前的陌生人私聊：不接管（口径同 cmd_suggest）
        return
    ok, reply = await register_reminder(bot, event, event.user_id, request.time, request.action)
    if ok:
        reply += await not_friend_hint(bot, event.user_id)
    try:
        await send_event_msg(bot, event, reply)
    except Exception:
        # 发送失败不打断流程，消息照常吞掉
        logger.warning(f"计时器回复发送失败：{reply}")
    record_plugin_call(__plugin_name__, from_user_id=event.user_id,
                       call_group=event.get("group_id"), success=True, args=text)
    raise CanceledException(f"已处理定时请求：{reply}")
