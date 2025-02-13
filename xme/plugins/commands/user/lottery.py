from xme.plugins.commands.user import __plugin_name__
from nonebot import on_command, CommandSession
from xme.xmetools.doc_tools import CommandDoc
from xme.xmetools.command_tools import send_session_msg
import random
from .classes import xme_user as u
from xme.plugins.commands.user.classes.xme_user import User, coin_name, coin_pronoun
from character import get_message
import traceback

alias = ['抽奖', 'lot']
TIMES_LIMIT = 5
MAX_COIN_COUNT = 50
cmd_name = 'lottery'
usage = {
    "name": cmd_name,
    "desc": get_message("plugins", __plugin_name__, cmd_name, 'desc'),
    "introduction": get_message("plugins", __plugin_name__, cmd_name, 'introduction', coin_name=coin_name, count_max=MAX_COIN_COUNT),
    "usage": f'({coin_name}数量)',
    "permissions": [],
    "alias": alias
}

@on_command(cmd_name, aliases=alias, only_to_me=False)
@u.using_user(save_data=True)
@u.limit(cmd_name, 1, get_message("plugins", __plugin_name__, cmd_name, 'limited', coin_name=coin_name), TIMES_LIMIT)
async def _(session: CommandSession, user: User):
    message = ""
    arg = session.current_arg_text.strip()
    if not arg:
        message = get_message("plugins", __plugin_name__, cmd_name, 'no_arg', coin_name=coin_name)
        await send_session_msg(session, message)
        return False
    try:
        arg = int(arg)
        if arg <= 0:
            message = get_message("plugins", __plugin_name__, cmd_name, 'invalid_arg', coin_name=coin_name)
            await send_session_msg(session, message)
            return False
    except ValueError as ex:
        print(ex)
        print(traceback.format_exc())
        message = get_message("plugins", __plugin_name__, cmd_name, 'invalid_arg', coin_name=coin_name)
        await send_session_msg(session, message)
        return False

    if arg > MAX_COIN_COUNT:
        message = get_message("plugins", __plugin_name__, cmd_name, 'too_many_coins',
            coin_name=coin_name,
            count=arg,
            coin_pronoun=coin_pronoun,
            count_max=MAX_COIN_COUNT
        )
        await send_session_msg(session, message)
        return False
    elif user.coins - arg < 0:
        message = get_message("plugins", __plugin_name__, cmd_name, 'not_enough_coins',
            coin_name=coin_name,
            count=arg,
            coin_pronoun=coin_pronoun,
            coins_left=user.coins,
        )
        await send_session_msg(session, message)
        return False
    user.coins -= arg
    result = random.randint(0, int(arg * 2))
    user.add_coins(result)
    result_content = (get_message("plugins", __plugin_name__, cmd_name, 'get_coin_result', coin_name=coin_name, get_count=result, coin_pronoun=coin_pronoun) if result > 0 else
                      get_message("plugins", __plugin_name__, cmd_name, 'no_coin_result', coin_name=coin_name, get_count=result, coin_pronoun=coin_pronoun))
    times_left = TIMES_LIMIT - u.get_limit_info(user, cmd_name)[1] - 1
    message = get_message("plugins", __plugin_name__, cmd_name, 'result',
        coin_name=coin_name,
        coin_pronoun=coin_pronoun,
        count=arg,
        result=result,
        coins_left=user.coins,
        result_content=result_content,
        times_left=times_left
    )
    await send_session_msg(session, message)
    return True