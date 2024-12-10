from nonebot import on_command, CommandSession
from xme.xmetools.doc_gen import CommandDoc
from xme.xmetools.command_tools import send_msg
from character import get_message

alias = ['你是谁', 'who', 'chac']
__plugin_name__ = 'whoru'
__plugin_usage__ = str(CommandDoc(
    name=__plugin_name__,
    desc=get_message(__plugin_name__, 'desc'),
    introduction=get_message(__plugin_name__, 'introduction'),
    usage=f'',
    permissions=[],
    alias=alias
))

@on_command(__plugin_name__, aliases=alias, only_to_me=False)
async def _(session: CommandSession):
    chac_name = get_message("bot_info", "name")
    author = get_message("bot_info", "author")
    await send_msg(session, get_message(__plugin_name__, "whoami", chac_name=chac_name, author=author))