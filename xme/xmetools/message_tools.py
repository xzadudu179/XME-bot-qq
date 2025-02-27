from nonebot import MessageSegment, Message, NoneBot
from xme.xmetools.bot_control import bot_call_action
from aiocqhttp import Event
import config
import config
from xme.xmetools import color_manage as c
from nonebot.session import BaseSession
from character import get_message

def change_group_message_content(message_dict, new_content, user_id=None, nickname=None) -> MessageSegment:
    """修改群消息内容

    Args:
        message_dict (_type_): 消息字典
        new_content (_type_): 新内容
        user_id (int, optional): 消息用户 id. Defaults to None.
        nickname (int, optional): 消息用户名. Defaults to None.

    Returns:
        MessageSegment: 消息节点
    """
    if not user_id:
        user_id = message_dict["sender"]["user_id"]
    if not nickname:
        nickname = message_dict["sender"]["card"] if message_dict["sender"]["card"] else message_dict["sender"]["nickname"]
    message = MessageSegment.node_custom(user_id=user_id, nickname=nickname, content=new_content)
    return message

async def send_to_superusers(bot: NoneBot, message):
    for u in config.SUPERUSERS:
        await bot.send_private_msg(user_id=u, message=message)

async def send_forward_msg(bot: NoneBot, event: Event, messages: list[MessageSegment]):
    """发送合并转发消息

    Args:
        bot (NoneBot): bot
        event (Event): 消息事件
        messages (list[MessageSegment]): 消息列表
    """
    res_id = await bot_call_action(bot, "send_forward_msg", messages=Message(messages), group_id=event.group_id)
    return await bot.send(event, message=Message(MessageSegment.forward(res_id)))

def get_pure_text_message(message: dict) -> str:
    """获取纯文本消息

    Args:
        message (dict): 消息字典

    Returns:
        str: 纯文本消息
    """
    message_segs = message['message']
    msgs = []
    for msg in message_segs:
        if msg['type'] != "text":
            msgs.append(f"&#91;{msg['type']}&#93;")
        msgs.append(msg['data'].get('text', ""))
    return "".join(msgs)

async def send_event_msg(bot: NoneBot, event: Event, message, at=True, reply=False, **kwargs):
    event.message_id
    await bot.send(event, (f"[CQ:at,qq={event.user_id}] " if at and event.user_id else "") + message, **kwargs)

async def msg_preprocesser(session, message, send_time=-1):
    funcs = {
    }
    if send_time >= 0:
        message += "\n" + get_message("config", "message_time", secs=send_time)
    for func in funcs:
        result = await func(message, session)
        if result and type(result) == str:
            message = result
    return message

async def send_session_msg(session: BaseSession, message, at=True, **kwargs):
    message_result = message
    message_result = await msg_preprocesser(session, message)
    if not message_result and message_result != "":
        print(f"bot 要发送的消息 {message} 已被阻止/没东西")
        return
    await session.send(str(message_result), at_sender=at, **kwargs)

async def send_to_groups(bot: NoneBot, message, groups: list | tuple | None = None):
    """在 bot 所在所有群发消息

    Args:
        bot (NoneBot): bot
        message (Message_T): 消息内容
        groups (list | tuple | None)
    """
    if groups is None:
        groups = await bot.get_group_list()
    for group in groups:
        if isinstance(group, dict):
            g = group['group_id']
        else:
            g = group
        await bot.send_group_msg(group_id=g, message=message)