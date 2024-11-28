from nonebot import on_command, CommandSession
from xme.xmetools.doc_gen import CommandDoc
from xme.xmetools.command_tools import send_msg
import random
from ...xmetools import xme_user as u
from xme.xmetools.xme_user import User
from character import get_message

coin_name = get_message("config", "coin_name")
coin_pronoun =  get_message("config", "coin_pronoun")

alias = ['抽奖', 'lot']
times_limit = 5
__plugin_name__ = 'lottery'
__plugin_usage__ = str(CommandDoc(
    name=__plugin_name__,
    desc=get_message(__plugin_name__, 'desc'),
    introduction=get_message(__plugin_name__, 'introduction').format(coin_name=coin_name),
    usage=f'({coin_name}数量)',
    permissions=[],
    alias=alias
))
@on_command(__plugin_name__, aliases=alias, only_to_me=False)
@u.using_user(save_data=True)
@u.limit(__plugin_name__, 1, get_message(__plugin_name__, 'limited').format(coin_name=coin_name), times_limit)
async def _(session: CommandSession, user: User):
    message = ""
    arg = session.current_arg_text.strip()
    if not arg:
        message = get_message(__plugin_name__, 'no_arg').format(coin_name=coin_name)
        await send_msg(session, message)
        return False
    try:
        arg = int(arg)
        if arg <= 0:
            message = get_message(__plugin_name__, 'invalid_arg').format(coin_name=coin_name)
            await send_msg(session, message)
            return False
    except ValueError:
        message = get_message(__plugin_name__, 'invalid_arg').format(coin_name=coin_name)
        await send_msg(session, message)
        return False

    if user.coins - arg < 0:
        message = get_message(__plugin_name__, 'not_enough_coins').format(
            coin_name=coin_name,
            count=arg,
            coin_pronoun=coin_pronoun,
            coins_left=user.coins,
        )
        await send_msg(session, message)
        return False
    user.coins -= arg
    result = random.randint(0, int(arg * 1.79))
    user.coins += result
    result_content = (get_message(__plugin_name__, 'get_coin_result') if result > 0 else get_message(__plugin_name__, 'no_coin_result')).format(
        coin_name=coin_name,
        get_count=result,
        coin_pronoun=coin_pronoun
    )
    times_left = times_limit - u.get_limit_info(user, __plugin_name__)[1] - 1
    message = get_message(__plugin_name__, 'result').format(
        coin_name=coin_name,
        coin_pronoun=coin_pronoun,
        count=arg,
        result=result,
        coins_left=user.coins,
        result_content=result_content,
        times_left=times_left
    )
    await send_msg(session, message)
    return True