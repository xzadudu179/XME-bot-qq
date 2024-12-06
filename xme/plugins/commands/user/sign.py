from xme.plugins.commands.user import __plugin_name__
from nonebot import on_command, CommandSession
from xme.xmetools.command_tools import send_msg
import random
from ....xmetools import xme_user as u
from xme.xmetools.xme_user import User, coin_name, coin_pronoun
from character import get_message

# coin_name = get_message("config", "coin_name")
# coin_pronoun =  get_message("config", "coin_pronoun")

alias = ['签到', 'check', 'checkin', 'register', 's']
cmd_name = 'sign'
usage = {
    "name": cmd_name,
    "desc": get_message(__plugin_name__, cmd_name, 'desc'),
    "introduction": get_message(__plugin_name__, cmd_name, 'introduction', coin_name=coin_name),
    "usage": f'',
    "permissions": [],
    "alias": alias
}

@on_command(cmd_name, aliases=alias, only_to_me=False)
@u.using_user(save_data=True)
@u.limit(cmd_name, 1, get_message(__plugin_name__, cmd_name, 'limited'))
async def _(session: CommandSession, user: User):
    message = ""
    # message = get_message(__plugin_name__, cmd_name, 'failed')
    print(user)
    append_coins = random.randint(0, 50)
    user.add_coins(append_coins)
    if append_coins == 0:
        message = get_message(__plugin_name__, cmd_name, 'login_no_coins',
            coin_name=coin_name,
            login_success=get_message(__plugin_name__, cmd_name, 'login_success')
        )
    else:
        message = get_message(__plugin_name__, cmd_name, 'success',
            login_success=get_message(__plugin_name__, cmd_name, 'login_success'),
            state=get_message(__plugin_name__, cmd_name, 'get_state'),
            coin_count=abs(append_coins),
            coin_name=coin_pronoun + coin_name,
            coin_total=user.coins
        )
    await send_msg(session, message)
    return True