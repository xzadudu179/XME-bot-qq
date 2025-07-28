from nonebot import on_command, CommandSession
from xme.xmetools.doctools import CommandDoc
from ...xmetools import systools as st
from character import get_message
from xme.xmetools import typetools
from xme.xmetools.msgtools import send_session_msg
from xme.xmetools.numtools import divs

alias = ['divides']
__plugin_name__ = 'divs'
__plugin_usage__ = str(CommandDoc(
    name=__plugin_name__,
    desc=get_message("plugins", __plugin_name__, 'desc'),
    introduction=get_message("plugins", __plugin_name__, 'introduction'),
    usage=f'(数字)',
    permissions=[],
    alias=alias
))

@on_command(__plugin_name__, aliases=alias, only_to_me=False)
async def _(session: CommandSession):
    args = session.current_arg.strip()
    if not args:
        return await send_session_msg(session, get_message("plugins", __plugin_name__, "no_arg"), tips=True)
    if len(args) > 15:
        return await send_session_msg(session, get_message("plugins", __plugin_name__, "too_long"), tips=True)
    original_num = typetools.try_parse(args, int)
    if original_num is None:
        return await send_session_msg(session, get_message("plugins", __plugin_name__, 'invalid_num'), tips=True)
    num = abs(original_num)
    if num < 2:
        return await send_session_msg(session, get_message("plugins", __plugin_name__, 'less_than_2'), tips=True)
    return await send_session_msg(session, get_message("plugins", __plugin_name__, 'prefix', num=original_num) + "\n" + (("\n".join([f"{i + 1}. {item}" for i, item in enumerate(x) if item != "..."]) + ("\n..." if x[-1] == "..." else "")) if len(x:=divs(num)) >= 1 else get_message("plugins", __plugin_name__, 'nothing')), tips=True)