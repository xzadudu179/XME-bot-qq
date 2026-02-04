cmd_name = 'inventory'
from xme.plugins.commands.xme_user import __plugin_name__  # noqa: E402
from nonebot import CommandSession # noqa: E402
from xme.xmetools.plugintools import on_command # noqa: E402
from xme.xmetools.msgtools import send_session_msg # noqa: E402
from ..classes import user as u # noqa: E402
from xme.plugins.commands.xme_user.classes.user import User # noqa: E402
from character import get_message # noqa: E402
from . import add_item, drop_item, use_item, check # noqa: E402

funcs = {
    add_item.arg_func_name: add_item.info,
    drop_item.arg_func_name: drop_item.info,
    use_item.arg_func_name: use_item.info,
    check.arg_func_name: check.info,
}

alias = ['inv', '物品栏']
usage = {
    "name": cmd_name,
    "desc": get_message("plugins", __plugin_name__, cmd_name, 'desc'),
    "introduction": get_message("plugins", __plugin_name__, cmd_name, 'introduction', ),
    "usage": '',
    "permissions": [],
    "alias": alias
}
@on_command(cmd_name, aliases=alias, only_to_me=False, permission=lambda _: True)
@u.using_user(save_data=True)
async def _(session: CommandSession, user: User):
    arg = session.current_arg_text.strip()
    args = arg.split(" ")
    for k, v in funcs.items():
        if args[0] != k:
            continue
        if not v['permissions'](user.id):
            await send_session_msg(session, get_message("plugins", __plugin_name__, cmd_name, 'no_permission'))
            return False
        return await v['func'](session, user, " ".join(args[1:]))
    await send_session_msg(session, get_message("plugins", __plugin_name__, cmd_name, 'inv_prefix') + '\n' + str(user.inventory))
    return True