from xme.plugins.commands.xme_user import __plugin_name__
from nonebot import on_command, CommandSession
from xme.xmetools.msgtools import send_session_msg
from xme.xmetools import randtools
from .classes import user as u
from xme.plugins.commands.xme_user.classes.user import User, coin_name, coin_pronoun
from character import get_message
from xme.xmetools.cmdtools import use_args


alias = ['bio', 'intro', 'desc']
cmd_name = 'describe'
usage = {
    "name": cmd_name,
    "desc": get_message("plugins", __plugin_name__, cmd_name, 'desc'),
    "introduction": get_message("plugins", __plugin_name__, cmd_name, 'introduction', coin_name=coin_name),
    "usage": f'<个人资料文本>',
    "permissions": [],
    "alias": alias
}
@on_command(cmd_name, aliases=alias, only_to_me=False)
@u.using_user(save_data=True)
@use_args(arg_len=1)
async def _(session: CommandSession, user: User, arg_list: list):
    print(arg_list)
    if not arg_list[0]:
        if not user.desc:
            await send_session_msg(session, get_message("plugins", __plugin_name__, cmd_name, 'no_arg'))
            return False
        ans = await session.aget(prompt=get_message("plugins", __plugin_name__, cmd_name, 'ask_for_delete'))
        if ans == "y":
            await send_session_msg(session, get_message("plugins", __plugin_name__, cmd_name, 'deleted', desc=user.desc))
            user.desc = ""
            return True
        await send_session_msg(session, get_message("plugins", __plugin_name__, cmd_name, 'canceled_delete'))
        return False
    user.desc = arg_list[0]
    await send_session_msg(session, get_message("plugins", __plugin_name__, cmd_name, 'success'))
    return True