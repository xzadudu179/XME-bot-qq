from nonebot import on_notice, RequestSession
from nonebot import get_bot
from ....xmetools import color_manage as c
import asyncio
import random

@on_notice("notify")
async def _(session: RequestSession):
    # 判断验证信息是否符合要求
    if session.event.user_id == session.self_id: return
    print(session.event.user_id, session.event.sub_type)
    print(session.event.group_id)
    if session.event.sub_type == 'poke':
        bot = get_bot()
        operator = (await bot.api.get_group_member_info(group_id=session.event.group_id, user_id=session.event.user_id))
        operator = operator['card'] if operator['card'] else operator['nickname']
        target = (await bot.api.get_group_member_info(group_id=session.event.group_id, user_id=session.event['target_id']))
        target = target['card'] if target['card'] else target['nickname']
        print(c.gradient_text("#dda3f8","#66afff" ,text=f"[{(await bot.api.get_group_info(group_id=session.event.group_id))['group_name']}] {operator} {session.event['action']} {target} {session.event['suffix']}"))
    if session.event.sub_type == 'poke' and session.event['target_id'] == session.self_id:
        print("戳回去")
        # 随机等待一段时间
        await asyncio.sleep(random.random() * 3 + 0.2)
        # Lagrange 的扩展 API
        if session.event.group_id:
            await session.bot.call_action(action='group_poke', group_id=session.event.group_id, user_id=session.event.user_id)
        else:
            await session.bot.call_action(action='friend_poke', user_id=session.event.user_id)