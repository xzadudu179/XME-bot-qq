from xme.plugins.commands.xme_user import __plugin_name__
from nonebot import on_command, CommandSession
from xme.xmetools.msgtools import send_session_msg
import math
from xme.xmetools import timetools
# from xme.xmetools.texttools import dec_to_chinese
from xme.xmetools import randtools
from nonebot.permission import SenderRoles
import random
random.seed()
from .classes import user as u
from xme.plugins.commands.xme_user.classes.user import User, coin_name, coin_pronoun
from character import get_message

alias = ['签到', 'register', 's']
cmd_name = 'sign'
usage = {
    "name": cmd_name,
    "desc": get_message("plugins", __plugin_name__, cmd_name, 'desc'),
    "introduction": get_message("plugins", __plugin_name__, cmd_name, 'introduction', ),
    "usage": f'',
    "permissions": [],
    "alias": alias
}

@on_command(cmd_name, aliases=alias, only_to_me=False, permission=lambda _: True)
@u.using_user(save_data=False)
@u.limit(cmd_name, 1, get_message("plugins", __plugin_name__, cmd_name, 'limited'))
async def _(session: CommandSession, user: User):
    FIRST_AWARD = 10
    message = ""
    # message = get_message("plugins", __plugin_name__, cmd_name, 'failed')
    print(user)
    append_coins = random.randint(0, 50)
    user.add_coins(append_coins)
    users = User.get_users()
    signed_users_count = 0
    reaction = "\n" + get_message("character", "time_period_reactions",timetools.get_time_period()) if randtools.random_percent(min(100, max(0, user.xme_favorability + 20))) else ""
    for u in users.values():
        counters = u.get('counters', {})
        if timetools.get_valuetime(counters.get(cmd_name, {}).get('time', 0), timetools.TimeUnit.DAY) == timetools.get_valuetime(timetools.timenow(), timetools.TimeUnit.DAY):
            signed_users_count += 1
    if append_coins == 0:
        message = get_message("plugins", __plugin_name__, cmd_name, 'login_no_coins',

            time_period=timetools.get_time_period()
        )
    else:
        message = get_message("plugins", __plugin_name__, cmd_name, 'success',
            login_success=get_message("plugins", __plugin_name__, cmd_name, 'login_success', time_period=timetools.get_time_period()),
            state=get_message("plugins", __plugin_name__, cmd_name, 'get_state'),
            coin_count=abs(append_coins),
            coin_pron_name=coin_pronoun + coin_name,
            coin_total=user.coins,
        )
    if signed_users_count == 0:
        user.add_coins(FIRST_AWARD)
        sign_message = get_message("plugins", __plugin_name__, cmd_name, 'first_sign', first_award=FIRST_AWARD,  )
    else:
        sign_message = get_message("plugins", __plugin_name__, cmd_name,'sign_rank', count=signed_users_count + 1)
    message += "\n" + sign_message + reaction
    # 防止发送消息时间过长导致出现多个第一名签到的情况
    user.save()
    print("保存用户数据")
    return message