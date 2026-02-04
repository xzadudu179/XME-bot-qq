from nonebot import CommandSession
from xme.xmetools.plugintools import on_command
from xme.xmetools.doctools import CommandDoc
from character import get_message
from xme.xmetools.msgtools import send_session_msg

alias = ['字数', 'len', 'cou', 'length']
__plugin_name__ = 'count'
__plugin_usage__ = CommandDoc(
    name=__plugin_name__,
    desc=get_message("plugins", __plugin_name__, 'desc'),
    introduction=get_message("plugins", __plugin_name__, 'introduction'),
    usage='(输入的文字)',
    permissions=["无"],
    alias=alias
)

@on_command(__plugin_name__, aliases=alias, only_to_me=False, permission=lambda _: True)
async def _(session: CommandSession):
    input_str = session.current_arg_text.strip()
    if not input_str:
        return await send_session_msg(session, get_message("plugins", __plugin_name__, 'no_str'), tips=True)
    return await send_session_msg(session, get_message("plugins", __plugin_name__, 'result', length=len(input_str)), tips=True)

