from xme.plugins.commands.xme_user import __plugin_name__
from nonebot import CommandSession
from xme.xmetools.plugintools import on_command
from xme.xmetools.msgtools import send_session_msg
from xme.xmetools.bottools import permission
from xme.xmetools.imgtools import image_msg
from xme.xmetools import randtools
import random
from .classes import user as u
from xme.plugins.commands.xme_user.classes.user import User, coin_name, coin_pronoun
from character import get_message
from xme.xmetools.imgtools import get_qq_avatar
from xme.xmetools.texttools import get_at_id

alias = ['个人信息', '个人资料', 'uinfo', 'info']
cmd_name = 'userinfo'
usage = {
    "name": cmd_name,
    "desc": get_message("plugins", __plugin_name__, cmd_name, 'desc'),
    "introduction": get_message("plugins", __plugin_name__, cmd_name, 'introduction', ),
    "usage": f'<at人>',
    "permissions": [""],
    "alias": alias
}

@on_command(cmd_name, aliases=alias, only_to_me=False, permission=lambda _: True)
@u.using_user(save_data=False)
# @permission(lambda sender:  sender.is_groupchat, permission_help=" & ".join(usage["permissions"]))
async def _(session: CommandSession, user: User):
    arg = session.current_arg
    print("arg", arg)
    at_id = 0
    if arg.startswith("[CQ:at,qq="):
        # at_id = int(arg.split("[CQ:at,qq=")[-1].split(",")[0])
        at_id = get_at_id(arg)
    if at_id != 0:
        user = u.User.load(at_id, False)
    else:
        at_id = session.event.user_id
    if not user:
        message = get_message("plugins", __plugin_name__, cmd_name, 'no_user')
        await send_session_msg(session, message, tips=True)
        return False
    target_user = (await session.bot.api.get_stranger_info(user_id=at_id))['nickname']
    try:
        avatar = await image_msg(await get_qq_avatar(at_id), max_size=64, to_jpeg=False)
    except:
        avatar = ""
    reaction = "\n" + get_message("bot_info", "name") + ": " + get_message("character", "info_reactions") if randtools.random_percent(min(100, max(0, user.xme_favorability))) else ""
    if user.id == 1795886524:
        reaction = "\n" + get_message("bot_info", "name") + ": " + random.choice([get_message("character", "info_reactions_179"), get_message("character", "info_reactions")])
    message = f'\n{avatar}[用户] {target_user}\n' + str(user) + reaction


    await send_session_msg(session, message, tips=True)
    return True