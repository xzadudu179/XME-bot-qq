from nonebot import on_command, CommandSession
from xme.xmetools.doctools import CommandDoc
from xme.xmetools.msgtools import send_session_msg
from character import get_message

alias = ['whoareuy']
__plugin_name__ = 'whoru'
__plugin_usage__ = CommandDoc(
    name=__plugin_name__,
    desc=get_message("plugins", __plugin_name__, 'desc'),
    introduction=get_message("plugins", __plugin_name__, 'introduction'),
    usage=f'',
    permissions=["无"],
    alias=alias
)

@on_command(__plugin_name__, aliases=alias, only_to_me=False, permission=lambda _: True)
async def _(session: CommandSession):
    chac_name = get_message("bot_info", "name")
    author = get_message("bot_info", "author")
    await send_session_msg(session, get_message("plugins", __plugin_name__, "whoami", chac_name=chac_name, author=author))