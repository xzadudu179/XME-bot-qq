from nonebot import CommandSession
from nonebot.message import Message
from xme.xmetools.plugintools import on_command
from xme.xmetools.doctools import CommandDoc
from xme.xmetools.msgtools import send_session_msg, get_message
from xme.xmetools.bottools import permission
from xme.xmetools.typetools import try_parse
import traceback

alias = ['exec']
permissions = ["是 SUPERUSER"]
__plugin_name__ = 'execute'
__plugin_usage__ = CommandDoc(
    name=__plugin_name__,
    desc="执行代码",
    introduction="执行 python 代码 (debug)",
    usage='(代码内容)',
    permissions=permissions,
    alias=alias
)

@on_command(__plugin_name__, aliases=alias, only_to_me=False)
@permission(lambda sender: sender.is_superuser, permission_help=" & ".join(permissions))
async def _(session: CommandSession):
    NL = '\n'
    msg = '\n    '.join(session.current_arg_text.replace('\r', '\n').split('\n'))
    code = f"""
async def __exec():
    {'return ' + msg if msg.count(NL) <= 0 and not 'return' in msg else msg}
"""
    namespace = {
        "session": session,
    }
    try:
        exec(code, namespace)
        result = await namespace["__exec"]()
    except Exception as ex:
        return await send_session_msg(session, get_message("plugins", __plugin_name__, "execute_error", ex=ex, trace=traceback.format_exc()))
    if not result:
        return
    try:
        msg = Message(result)
    except:
        msg = try_parse(result, str, f"ERR:类型{type(result)}转换字符串失败")
    await send_session_msg(session, msg)