from nonebot import on_notice, NoticeSession
from aiocqhttp import MessageSegment
from character import get_message
from xme.xmetools.msgtools import send_session_msg
import asyncio
from xme.xmetools.debugtools import debug_msg
from xme.xmetools.bottools import is_group_member_count_legal
from nonebot.log import logger

increase_people = {}

# 将函数注册为群成员增加通知处理器
@on_notice('group_increase')
async def _(session: NoticeSession):
    global increase_people
    # 群人数过少直接退出
    group_info = await session.bot.api.get_group_info(group_id=session.event.group_id)
    if not is_group_member_count_legal(group_info):
        logger.info(f"退出群 {group_info} 因为人数过低")
        await session.bot.api.set_group_leave(group_id=group_info['group_id'])
        return
    # 发送欢迎消息
    # 如果是自己换一种欢迎方法
    if session.event.user_id == session.self_id:
        debug_msg("欢迎自己")
        return await send_session_msg(session, get_message("event_parsers", "welcome_self"), at=False)
    # 指定秒内加群的人会被一起计算
    group = session.event.group_id
    increase_people[group] = increase_people.get(group, [])
    if session.event.user_id != 1795886524:
        increase_people[group].append(str(MessageSegment.at(session.event.user_id)))
    else:
        return await send_session_msg(session, get_message("event_parsers", "welcome_99"), at=False)
    # debug_msg(increase_people)
    # debug_msg(get_message("event_parsers", "welcome", at=" ".join(increase_people[group])))
    people = increase_people[group]
    await asyncio.sleep(4)
    # debug_msg(increase_people)
    if len(people) == len(increase_people[group]):

        at = " ".join(increase_people[group])
        increase_people[group] = []
        debug_msg(get_message("event_parsers", "welcome", at=" ".join(str(s) for s in increase_people[group])))
        await send_session_msg(session, get_message("event_parsers", "welcome", at=at), False)
        # await send_session_msg(session, get_message("event_parsers", "welcome", at=''), False)
        return