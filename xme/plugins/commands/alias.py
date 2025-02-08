from xme.xmetools.doc_tools import CommandDoc
from xme.xmetools.command_tools import get_alias_by_cmd, get_cmd_by_alias
from xme.xmetools.command_tools import send_session_msg
from nonebot import on_command, CommandSession
from character import get_message

alias = ["别名", "al"]
__plugin_name__ = 'alias'

__plugin_usage__ = str(CommandDoc(
    name=__plugin_name__,
    desc=get_message(__plugin_name__, 'desc'),
    introduction=get_message(__plugin_name__, 'introduction'),
    usage=f'<指令名或别名>',
    permissions=["无"],
    alias=alias
))

@on_command(__plugin_name__, aliases=alias, only_to_me=False, permission=lambda _: True)
async def _(session: CommandSession):
    arg = session.current_arg_text.strip()
    if not arg:
        return await send_session_msg(session, get_message(__plugin_name__, 'no_arg'))
    cmd = get_cmd_by_alias(arg, False)
    if not cmd and arg:
        cmd = arg
    else:
        cmd = cmd.name[0]
    aliases = get_alias_by_cmd(cmd)
    print(cmd, aliases)
    if not aliases:
        return await send_session_msg(session, get_message(__plugin_name__, 'no_alias', command=cmd))
    message = get_message(__plugin_name__, 'result_prefix', command=cmd) + "\n"
    for i, alias in enumerate(aliases):
        message += get_message(__plugin_name__, 'alias_line', i=i + 1, alias=alias) + "\n"
    return await send_session_msg(session, message)