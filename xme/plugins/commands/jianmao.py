from nonebot import on_command, CommandSession
from xme.xmetools.doctools import CommandDoc
import os
from character import get_message
from xme.xmetools.msgtools import send_session_msg
from xme.xmetools.imgtools import image_msg
import random
from xme.xmetools.timetools import curr_days
random.seed()

alias = ['鉴毛', 'jianmao', 'jrjm']
__plugin_name__ = '今日鉴毛'
__plugin_usage__ = str(CommandDoc(
    name=__plugin_name__,
    desc=get_message("plugins", __plugin_name__, 'desc'),
    introduction=get_message("plugins", __plugin_name__, 'introduction'),
    usage=f'',
    permissions=["无"],
    alias=alias
))

@on_command(__plugin_name__, aliases=alias, only_to_me=False, permission=lambda _: True)
async def _(session: CommandSession):
    JIANMAO_PATH = rf"./static/img/jianmao"
    images = os.listdir(JIANMAO_PATH)
    img = random.choice(images)
    path = JIANMAO_PATH + "/" + img
    return await send_session_msg(session, await image_msg(path))