from nonebot import on_request, RequestSession
from xme.xmetools.msgtools import send_to_superusers
from xme.xmetools.bottools import get_user_name, get_group_name

@on_request('group')
async def _(session: RequestSession):
    # logger.info('有新的请求事件：%s', session.event)
    if session.event.sub_type != "invite":
        return
    # await send_session_msg(session, "收到了群聊的请求 owo", message_type="private")
    group_member_count = (await session.bot.get_group_info(group_id=session.event.group_id))["member_count"]
    await send_to_superusers(session.bot, f"有新的群聊请求哦\n来自: {await get_user_name(session.event.user_id)} ({session.event.user_id})\n邀请加入: {await get_group_name(session.event.group_id)} ({session.event.group_id})\n群人数：{group_member_count}")