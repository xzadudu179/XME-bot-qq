from xme.plugins.commands.user import __plugin_name__
from nonebot import on_command, CommandSession
from xme.xmetools.command_tools import send_msg
from ....xmetools import xme_user as u
from xme.xmetools.xme_user import User, coin_name, coin_pronoun
from character import get_message


alias = ['个人信息', '个人资料', 'uinfo', 'info']
cmd_name = 'userinfo'
usage = {
    "name": cmd_name,
    "desc": get_message(__plugin_name__, cmd_name, 'desc'),
    "introduction": get_message(__plugin_name__, cmd_name, 'introduction', coin_name=coin_name),
    "usage": f'<at人>',
    "permissions": [],
    "alias": alias
}
@on_command(cmd_name, aliases=alias, only_to_me=False)
@u.using_user(save_data=False)
async def _(session: CommandSession, user: User):
    arg = session.current_arg.strip()
    at_id = 0
    if arg.startswith("[CQ:at,qq="):
        at_id = int(arg.split("[CQ:at,qq=")[-1].split(",")[0])
    if at_id != 0:
        user = u.User.load(at_id, False)
    else:
        at_id = session.event.user_id
    if not user:
        message = get_message(__plugin_name__, cmd_name, 'no_user')
        await send_msg(session, message)
        return False
    target_user = (await session.bot.api.get_stranger_info(user_id=at_id))['nickname']
    message = f'\n{target_user}\n' + str(user)
    await send_msg(session, message)
    return True