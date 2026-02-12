from nonebot import on_request, RequestSession
from xme.xmetools import bottools
from xme.xmetools import colortools as c
from nonebot.log import logger

@on_request('friend')
async def _(session: RequestSession):
    # 判断验证信息是否符合要求
    name = await bottools.get_stranger_name(session.event.user_id)
    print(c.gradient_text("#dda3f8","#66afff" ,text=f"{name} 请求添加你为好友"))
    # if session.event.user_id in config.SUPERUSERS:
    print("同意")
    await bottools.bot_call_action(bot=session.bot, action="set_friend_add_request", flag=session.event.flag, approve=True)
    # await session.approve()
    return

@on_request
async def _(session: RequestSession):
    logger.info('有新的请求事件：%s', session.event)