from nonebot import on_command, CommandSession
from xme.xmetools.doc_tools import CommandDoc
from ...xmetools import cur_system as st
from character import get_message
from xme.xmetools import type_tools
from xme.xmetools.command_tools import send_session_msg
from xme.xmetools.num_tools import divs

alias = ['divides']
__plugin_name__ = 'divs'
__plugin_usage__ = str(CommandDoc(
    name=__plugin_name__,
    desc=get_message(__plugin_name__, 'desc'),
    introduction=get_message(__plugin_name__, 'introduction'),
    usage=f'(数字)',
    permissions=[],
    alias=alias
))

@on_command(__plugin_name__, aliases=alias, only_to_me=False)
async def _(session: CommandSession):
    args = session.current_arg.strip()
    if not args:
        return await send_session_msg(session, get_message(__plugin_name__, "no_arg"))
    num = type_tools.to_type(args, int)
    if num is None:
        return await send_session_msg(session, get_message(__plugin_name__, 'invalid_num'))
    return await send_session_msg(session, get_message(__plugin_name__, 'prefix', num=num) + "\n" + (("\n".join([f"{i + 1}. {item}" for i, item in enumerate(x) if item != "..."]) + ("\n..." if x[-1] == "..." else "")) if len(x:=divs(num)) >= 1 else get_message(__plugin_name__, 'nothing')))