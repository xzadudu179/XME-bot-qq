# 注册账号 或签到
from xme.xmetools.date_tools import *
import json
import config
from nonebot import on_command, CommandSession

register_alias = ["xme.reg", "xme.r"]

@on_command('xme.register', aliases=register_alias, only_to_me=False)
async def _(session: CommandSession):
    message = "签到成功~"
    await session.send("注册成功~")