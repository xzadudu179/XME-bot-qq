from anyio import sleep
# from itsdangerous import base64_encode
import random
from nonebot import on_command, CommandSession
from xme.xmetools.date_tools import curr_days
# from xme.plugins.commands.jrrp.luck_algorithm import get_luck
from xme.xmetools.doc_gen import CommandDoc

alias = ["今日人品" , "luck"]
__plugin_name__ = 'jrrp'

__plugin_usage__= str(CommandDoc(
    name=__plugin_name__,
    desc='今日人品',
    introduction='返回你今天的人品值（？） [by 千枫]',
    usage=f'jrrp',
    permissions=[],
    alias=alias
))

@on_command(__plugin_name__, aliases=alias, only_to_me=False)
async def jrrp(session: CommandSession):
    qq = session.event.user_id
    # key = base64_encode("嘿嘿嘿...179....嘿嘿嘿")
    # result = get_luck(qq, key)
    random.seed(int(str(curr_days()) + str(qq)))
    result = random.randint(0, 100)
    content = f"[CQ:at,qq={qq}] 你的今日人品为"
    if result < 10:
        await session.send(content + f"....{result}？uwu")
    elif result >= 90:
        await session.send(content + f"{result}！owo！")
    else:
        await session.send(content + f"{result} ovo")
