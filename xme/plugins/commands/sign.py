from nonebot import on_command, CommandSession
from xme.xmetools.doc_gen import CommandDoc
from xme.xmetools.command_tools import send_msg
import random
from ...xmetools import xme_user as u
from xme.xmetools.xme_user import User
from xme.xmetools import time_tools
from character import get_message

coin_name = get_message("config", "coin_name")
coin_pronoun =  get_message("config", "coin_pronoun")

alias = ['签到', 'check', 'checkin', 'register', 's']
__plugin_name__ = 'sign'
__plugin_usage__ = str(CommandDoc(
    name=__plugin_name__,
    desc=get_message(__plugin_name__, 'desc'),
    introduction=get_message(__plugin_name__, 'introduction').format(coin_name=coin_name),
    usage=f'',
    permissions=[],
    alias=alias
))
@on_command(__plugin_name__, aliases=alias, only_to_me=False)
@u.using_user(save_data=True)
async def _(session: CommandSession, user: User):

    message = get_message(__plugin_name__, 'failed')
    print(user)
    if u.is_limit(user, __plugin_name__, 1, time_tools.TimeUnit.DAY, floor_float=True):
        return await send_msg(session, message)
    append_coins = random.randint(0, 50)
    user.coins += append_coins
    if append_coins == 0:
        message = get_message(__plugin_name__, 'login_no_coins')
    else:
        message = get_message(__plugin_name__, 'success').format(
            login_success=get_message(__plugin_name__, 'login_success'),
            state=get_message(__plugin_name__, 'get_state'),
            coin_count=abs(append_coins),
            coin_name=coin_pronoun + coin_name,
            coin_total=user.coins
        )
    await send_msg(session, message)