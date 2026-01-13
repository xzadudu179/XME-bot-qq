from nonebot import on_notice, RequestSession
import aiocqhttp
from nonebot import get_bot
from ....xmetools import colortools as c
from xme.xmetools.bottools import bot_call_action, get_group_name
import asyncio
import random
from xme.xmetools.randtools import random_percent
from nonebot.log import logger
random.seed()

@on_notice("notify")
async def _(session: RequestSession):
    # 判断验证信息是否符合要求
    if session.event.user_id == session.self_id: return
    logger.debug(session.event.user_id, session.event.sub_type)
    logger.debug(session.event.group_id)
    if session.event.sub_type == 'poke':
        bot = get_bot()
        try:
            operator = (await bot.api.get_group_member_info(group_id=session.event.group_id, user_id=session.event.user_id))
            operator = operator['card'] if operator['card'] else operator['nickname']
            target = (await bot.api.get_group_member_info(group_id=session.event.group_id, user_id=session.event['target_id']))
            target = target['card'] if target['card'] else target['nickname']
        except aiocqhttp.exceptions.ActionFailed:
            operator = (await bot.api.get_stranger_info(user_id=session.event.user_id))
            operator = operator['nickname']
            target = (await bot.api.get_stranger_info(user_id=session.event.self_id))
            target = target['nickname']
        logger.debug(session.event)
        print(c.gradient_text("#dda3f8","#66afff" ,text=f"[{(await get_group_name(session.event.group_id)) if session.event.group_id else '私聊'}] {operator} {session.event.get('action', '戳了戳')} {target} {session.event.get('suffix', '')}"))
    if session.event.sub_type == 'poke' and session.event['target_id'] == session.self_id:
        if random_percent(20):
            logger.debug("不戳")
            return
        logger.debug("戳回去")
        # 随机等待一段时间
        await asyncio.sleep(random.random() * 3 + 0.2)
        # Lagrange 的扩展 API
        if session.event.group_id:
            await bot_call_action(bot, action='group_poke', group_id=session.event.group_id, user_id=session.event.user_id)
        else:
            await bot_call_action(bot, action='friend_poke', user_id=session.event.user_id)