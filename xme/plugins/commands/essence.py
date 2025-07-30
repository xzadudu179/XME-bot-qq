from nonebot import on_command, CommandSession
from xme.xmetools.doctools import CommandDoc
from ...xmetools import systools as st
from character import get_message
from xme.xmetools.imgtools import image_msg
from xme.xmetools.msgtools import send_session_msg
import random
from xme.xmetools.imgtools import get_qq_avatar
from xme.xmetools.bottools import bot_call_action

alias = ['ess']
__plugin_name__ = 'essence'
__plugin_usage__ = str(CommandDoc(
    name=__plugin_name__,
    desc=get_message("plugins", __plugin_name__, 'desc'),
    # desc='查看系统状态',
    introduction=get_message("plugins", __plugin_name__, 'introduction'),
    # introduction='查看运行该 XME-Bot 实例的设备的系统状态',
    usage=f'',
    permissions=["无"],
    alias=alias
))

@on_command(__plugin_name__, aliases=alias, only_to_me=False, permission=lambda _: True)
async def _(session: CommandSession):
    essences = await session.bot.api.call_action("get_essence_msg_list", group_id=session.event.group_id)
    print(essences, len(essences))
    essence = random.choice(essences)
    if len(essences) < 2:
        return await send_session_msg(session, get_message("plugins", __plugin_name__, 'no_essence'))
    await send_session_msg(session, get_message("plugins", __plugin_name__, 'result', avatar=image_msg(get_qq_avatar(essence["sender_id"], size=50)), sender=essence["sender_nick"] ,essence=essence["data"]["content"]))