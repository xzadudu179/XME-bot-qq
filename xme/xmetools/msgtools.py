from nonebot import MessageSegment, Message, NoneBot
from aiocqhttp import Event, ApiError, ActionFailed
import config
# import config
from xme.xmetools.texttools import get_msg_len
from xme.xmetools.randtools import random_percent
from xme.xmetools.debugtools import debugging
from xme.xmetools.bottools import get_user_name
from xme.xmetools.cmdtools import send_cmd, get_cmd_by_alias
from xme.xmetools.debugtools import debug_msg
from nonebot.log import logger
from nonebot.session import BaseSession
from nonebot.command import CommandSession
from PIL import Image
import asyncio
import traceback
from xme.xmetools.imgtools import gif_to_base64, get_url_image, limit_size, image_to_base64
from character import get_message

async def gif_msg(input_path, scale=1):
    img = Image.open(input_path)

    frames = []
    for frame in range(img.n_frames):
        img.seek(frame)  # 选中当前帧
        resized_frame = img.resize(
            (img.width * scale, img.height * scale), Image.Resampling.NEAREST
        )  # 放大2倍
        frames.append(resized_frame.convert("RGBA"))  # 确保格式一致
    b64 = gif_to_base64(img, frames)
    debug_msg("gif b64 success")
    try:
        # 将消息发送的同步方法放到后台线程执行
        result = await asyncio.to_thread(create_image_message, b64)
        return result
    except Exception as e:
        logger.error(f"发生错误: {e}")
        logger.exception(traceback.format_exc())
        return MessageSegment.text("[图片加载失败]")


async def image_msg(path_or_image, max_size=0, to_jpeg=True, summary=get_message("config", "image_summary")):
    """获得可以直接发送的图片消息

    Args:
        path_or_image (str): 图片路径或图片
        max_size (int): 图片最大大小，超过会被重新缩放. Defaults to 0.
        to_jpeg (bool): 是否转换为 Jpeg 格式
        summary (str): 图片消息预览

    Returns:
        MessageSegment: 消息段
    """
    is_image = False
    if not isinstance(path_or_image, str):
        is_image = True
    debug_msg(is_image)
    try:
        image = path_or_image if is_image else Image.open(path_or_image)
    except Exception:
        image = await get_url_image(path_or_image)
    # image.resize((image.width * scale, image.height * scale), Image.Resampling.NEAREST)
    if max_size > 0:
        debug_msg("重新缩放")
        image = limit_size(image, max_size)
    debug_msg(image)
    b64 = image_to_base64(image, to_jpeg)
    debug_msg("b64 success")
    # return MessageSegment.image('base64://' + b64, cache=True, timeout=10)
    try:
        # 将消息发送的同步方法放到后台线程执行
        result = await asyncio.to_thread(create_image_message, b64, summary=summary)
        return result
    except Exception as e:
        logger.error(f"发生错误: {e}")
        logger.exception(traceback.format_exc())
        return MessageSegment.text("[图片加载失败]")

def create_image_message(b64: str, summary: str="[漠月的图片~]"):
    """同步发送图片消息"""
    try:
        # return MessageSegment.image(f'base64://{b64}', cache=True, timeout=10)
        return MessageSegment(type_="image", data={
            'file': f"base64://{b64}",
            'cache': 1,
            'timeout': 10,
            'summary': summary,
        })
    except Exception as e:
        logger.error(f"发送图片时出错: {e}")
        logger.exception(traceback.format_exc())
        raise e

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
        card = message_dict["sender"].get("card", "")
        nickname = message_dict["sender"]["card"] if card else message_dict["sender"]["nickname"]
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
    try:
        from xme.xmetools.bottools import bot_call_action
        if event.group_id is not None:
            res_id = await bot_call_action(bot, "send_group_forward_msg", messages=Message(messages), group_id=event.group_id)
        else:
            res_id = await bot_call_action(bot, "send_private_forward_msg", messages=Message(messages), user_id=event.user_id)
        return await bot.send(event, message=Message(MessageSegment.forward(res_id)))
    except ApiError:
        return

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

async def send_event_msg(bot: NoneBot, event: Event, message, at=True, reply=False, debug=False, **kwargs):
    event.message_id
    if debug and not debugging():
        return
    debug_prefix = "" if not debug else "[DEBUG] "
    await bot.send(event, debug_prefix + (f"[CQ:at,qq={event.user_id}] " if at and event.user_id else "") + message, **kwargs)

async def msg_preprocesser(session, message, send_time=-1):
    funcs = {
    }
    if send_time >= 0:
        message += "\n" + get_message("config", "message_time", secs=send_time)
    for func in funcs:
        result = await func(message, session)
        if result and isinstance(result, str):
            message = result
    return message

async def aget_session_msg(session: CommandSession, prompt=None, at=True, linebreak=True, tips=False, tips_percent: float | int = 50, debug=False, can_use_command=False, command_func=None, func_kwargs: dict= {}, check_prohibited_words=False, **kwargs):
    """异步获取会话回复消息，并设置 prompt

    Args:
        session (CommandSession): 指令会话
        prompt (MessageSegment | str): Prompt 消息
        at (bool, optional): 是否 at 用户. Defaults to True.
        linebreak (bool, optional): 是否在结尾换行. Defaults to True.
        tips (bool, optional): 是否使用 Tips. Defaults to False.
        tips_percent (float | int, optional): Tips 出现的概率. Defaults to 50.
        debug (bool, optional): 是否仅在 Debug 环境启用. Defaults to False.
        can_use_command (bool, optional): 用户的回复是否可以使用指令. Defaults to False.
        command_func (function, optional): 若用户回复为指令且可以使用指令，指令所使用的函数。默认会传入 reply 参数. Defaults to None.
        func_kwargs (dict, optional): 指令使用函数的参数. Defaults to {}.

    Returns:
        Any: 用户回复
    """
    debug_prefix = "" if not debug else "[DEBUG] "
    if debug and not debugging():
        return
    has_tips = random_percent(tips_percent) and tips
    msg = str(prompt)
    if msg and msg[-1] in ["\n", "\r"]:
        msg = msg[:-1]
    is_nline_start = True if msg and msg[0] == "\n" else False
    reply = await session.aget(
        prompt="" if prompt is None else (debug_prefix +
        (
            "\n" if
                is_nline_start and
                at and
                linebreak and
                session.event.group_id is not None
            else ""
        ) +
        msg +
        (
            "" if not has_tips
            else
                "\n-------------------\ntip：" +
            get_message("bot_info", "tips")
        )), at_sender=at, **kwargs)
    if can_use_command and get_cmd_by_alias(reply):
        if command_func:
            return await command_func(reply, **func_kwargs)
        await send_cmd(reply, session)
        return "CMD_END"
    return reply

async def send_session_msg(session: BaseSession, message: Message, at=True, linebreak=True, tips=False, tips_percent: float | int = 50, debug=False, check_prohibited_words=False, **kwargs):
    message_result = Message(message)
    list_msg = message_result
    message_result = await msg_preprocesser(session, message)
    if not message_result or message_result == "":
        logger.warning(f"bot 要发送的消息 {message} 已被阻止/没东西")
        await session.send("[ERROR] BOT 即将发送的消息已被阻止/为空")
        return
    debug_prefix = "" if not debug else "[DEBUG] "
    if debug and not debugging():
        return
    has_tips = random_percent(tips_percent) and tips
    msg = str(message_result)
    if msg[-1] in ["\n", "\r"]:
        msg = msg[:-1]
    msg_dict = {
        "sender": await session.bot.api.get_group_member_info(group_id=session.event.group_id, user_id=session.self_id) if session.event.group_id else await session.bot.api.get_stranger_info(user_id=session.self_id)
    }
    send_msg = debug_prefix + ("\n" if msg[0] != "\n" and at and linebreak and session.event.group_id is not None else "") + msg + ("" if not has_tips else "\n-------------------\ntip：" + get_message("bot_info", "tips"))
    # 太长的消息用聊天记录发送
    try:
        if get_msg_len(list_msg) > 1200 and session.event.group_id is not None:
            # if at:
            #     await session.send("", at_sender=at, **kwargs)
            return await send_forward_msg(
                session.bot,
                session.event,
                [
                    change_group_message_content(
                        msg_dict, send_msg.strip(),
                        user_id=session.event.user_id,
                        nickname=await get_user_name(
                            session.event.user_id,
                            group_id=session.event.group_id,
                            default="user"
                        )
                    )
                ]
            )
    except ApiError:
        return
    await session.send(send_msg, at_sender=at, **kwargs)

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
        try:
            await bot.send_group_msg(group_id=g, message=message)
        except ActionFailed:
            continue