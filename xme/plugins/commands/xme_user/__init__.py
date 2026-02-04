__plugin_name__ = 'XME 宇宙'
# 反射需要依靠 import 访问子 module
from . import coinrank, lottery, sign, userinfo, takecoin, sendcoin, inventory, describe, get_achievements  # noqa: F401
from nonebot import CommandSession
from xme.xmetools.plugintools import on_command
from xme.xmetools.msgtools import send_session_msg
# import config
from xme.xmetools.cmdtools import get_cmd_by_alias
from character import get_message
from xme.xmetools.doctools import PluginDoc, CommandDoc
from xme.xmetools import moduletools

cmd_name = "userhelp"
alias = ['uhelp', '用户帮助', 'uh']
usage = {
    "name": cmd_name,
    "desc": get_message("plugins", __plugin_name__, cmd_name, 'desc'),
    "introduction": get_message("plugins", __plugin_name__, cmd_name, 'introduction'),
    "usage": '<指令名或别名>',
    "permissions": [],
    "alias": alias
}

commands = moduletools.get_module_funcs('cmd_name', 'usage', __name__)
commands[cmd_name] = usage
__plugin_usage__ = PluginDoc(
    name=__plugin_name__,
    desc=get_message("plugins", __plugin_name__, 'desc'),
    introduction=get_message("plugins", __plugin_name__, 'introduction'),
    contents=[f"{prop['name']} {prop['usage']}: {prop['desc']}" for prop in commands.values()],
    usages=[f"{prop['name']} {prop['usage']}" for prop in commands.values()],
    permissions=[prop['permissions'] for prop in commands.values()],
    alias_list=[prop['alias'] for prop in commands.values()],
    simple_output=True
)
# print(__plugin_usage__)

@on_command(cmd_name, aliases=alias, only_to_me=False)
async def _(session: CommandSession):
    message = __plugin_usage__.split("/////OUTER/////")[0]
    arg = session.current_arg.strip()
    if arg:
        arg = x.name[0] if (x := get_cmd_by_alias(arg, False)) else arg
    else:
        await send_session_msg(session, message)
        return False
    if arg not in commands.keys():
        await send_session_msg(session, get_message("plugins", __plugin_name__, cmd_name,'no_cmd', cmd=arg))
        return False
    message = get_userhelp(arg)
    # message = CommandDoc(
    #     **commands[arg]
    # ))
    await send_session_msg(session, message, at=False)
    return True

def get_userhelp(cmd_name: str):
    message = str(CommandDoc(
        **commands[cmd_name]
    ))
    return message