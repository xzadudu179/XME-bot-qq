import nonebot
from nonebot.session import BaseSession
from ....xmetools import color_manage as c
import time
import random

bot = nonebot.get_bot()  # 在此之前必须已经 init

# @bot.on_message('private')
# async def _(session: BaseSession):
#     print(c.gradient_text("#dda3f8","#66afff" ,text=f"接收到了一条私聊消息, session: {session}"))
#     # await time.sleep(random.randint(1, 10))
#     await bot.send_private_msg(user_id=session['user_id'],message="喵？ owo")