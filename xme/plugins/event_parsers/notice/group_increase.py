from nonebot import on_notice, NoticeSession
from character import get_message
from xme.xmetools.command_tools import send_session_msg
import asyncio

increase_people = []

# 将函数注册为群成员增加通知处理器
@on_notice('group_increase')
async def _(session: NoticeSession):
    global increase_people
    # 发送欢迎消息
    # 如果是自己换一种欢迎方法
    if session.event.user_id == session.self_id:
        return await send_session_msg(session, get_message("event_parsers", "welcome_self"), at=False)
    # 1.5 秒内加群的人会被一起计算
    increase_people.append(f"[CQ:at,qq={session.event.user_id}]")
    # print(increase_people)
    people = increase_people.copy()
    await asyncio.sleep(1.5)
    # print(increase_people)
    if len(people) == len(increase_people):
        await send_session_msg(session, get_message("event_parsers", "welcome", at=" ".join(increase_people)), False)
        increase_people = []
        return