__plugin_name__ = 'XME 宇宙'
from . import coinrank, lottery, sign, userinfo, sendcoin, galaxymap, inventory
from nonebot import on_command, CommandSession
from xme.xmetools.msgtools import send_session_msg
import config
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
    "usage": f'<指令名或别名>',
    "permissions": [],
    "alias": alias
}

commands = moduletools.get_module_funcs('cmd_name', 'usage', __name__)
commands[cmd_name] = usage
__plugin_usage__ = str(PluginDoc(
    name=__plugin_name__,
    desc=get_message("plugins", __plugin_name__, 'desc'),
    introduction=get_message("plugins", __plugin_name__, 'introduction'),
    contents=[f"{prop['name']} {prop['usage']}: {prop['desc']}" for prop in commands.values()],
    usages=[f"{prop['name']} {prop['usage']}" for prop in commands.values()],
    permissions=[prop['permissions'] for prop in commands.values()],
    alias_list=[prop['alias'] for prop in commands.values()],
    simple_output=True
)) + "\n########\n" + get_message("plugins", __plugin_name__, 'help_suffix', help_cmd=f"{config.COMMAND_START[0]}{cmd_name} {usage['usage']}")

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
    message = str(CommandDoc(
        **commands[arg]
    ))
    await send_session_msg(session, message, at=False)
    return True