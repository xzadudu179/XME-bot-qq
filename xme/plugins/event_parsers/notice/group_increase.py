from nonebot import on_notice, NoticeSession
from character import get_message
from xme.xmetools.command_tools import send_msg

# 将函数注册为群成员增加通知处理器
@on_notice('group_increase')
async def _(session: NoticeSession):
    # 发送欢迎消息
    # 如果是自己换一种欢迎方法
    if session.event.user_id == session.self_id:
        return await send_msg(session, get_message("event_parsers", "welcome_self"))
    await send_msg(session, get_message("event_parsers", "welcome", at=f"[CQ:at,qq={session.event.user_id}]"), False)