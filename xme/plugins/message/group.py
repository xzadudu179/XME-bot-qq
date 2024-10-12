from nonebot import Message
import nonebot
from nonebot.session import BaseSession
from ...xmetools import color_manage as c
import time
import random

bot = nonebot.get_bot()  # 在此之前必须已经 init

@bot.on_message('group')
async def _(session: BaseSession):
    # print(c.gradient_text("#dda3f8","#66afff" ,text=f"接收到了一条群聊消息, session: {session}"))
    # await time.sleep(random.randint(1, 10))
    print(session['raw_message'].strip())
    if f"[CQ:at,qq={session.self_id}]" == session['raw_message'].strip():
        await bot.api.send_group_msg(group_id=session['group_id'], message="owo! 如果想问我如何使用我的指令的话，使用 \"/help\" 来查看指令列表/文档哦~")