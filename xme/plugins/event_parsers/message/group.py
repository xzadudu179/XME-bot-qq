import nonebot
from nonebot.session import BaseSession
from ....xmetools import color_manage as c
from .handler import *

bot = nonebot.get_bot()  # 在此之前必须已经 init

@bot.on_message('group')
async def _(session: BaseSession):
    # print(c.gradient_text("#dda3f8","#66afff" ,text=f"接收到了一条群聊消息, session: {session}"))
    # await time.sleep(random.randint(1, 10))
    for handler in handlers:
        await handler(session, bot)