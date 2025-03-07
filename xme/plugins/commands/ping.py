from nonebot import on_command, CommandSession
import time
from xme.xmetools.doctools import CommandDoc
from character import get_message
from xme.xmetools.msgtools import send_session_msg

alias = ['echotime', '延迟', '测延迟']
__plugin_name__ = 'ping'
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
    start = time.time()
    await send_session_msg(session, get_message("plugins", __plugin_name__, 'ping_message'), at=False)
    end = time.time()
    ping = end - start
    await send_session_msg(session, get_message("plugins", __plugin_name__, 'ping', ping=f"{ping:.3f}"))