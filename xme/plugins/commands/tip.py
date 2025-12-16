from nonebot import on_command, CommandSession
from xme.xmetools.doctools import CommandDoc
from xme.xmetools.msgtools import send_session_msg
from character import get_message

alias = ['提示']
__plugin_name__ = 'tip'
__plugin_usage__ = str(CommandDoc(
    name=__plugin_name__,
    desc=get_message("plugins", __plugin_name__, "desc"),
    introduction=get_message("plugins", __plugin_name__, "introduction"),
    usage=f'<提示数>',
    permissions=["无"],
    alias=alias
))



@on_command(__plugin_name__, aliases=alias, only_to_me=False, permission=lambda _: True)
async def _(session: CommandSession):
    tip = get_message("bot_info", "tips")
    await send_session_msg(session, f"tip: {tip}", tips=False)
