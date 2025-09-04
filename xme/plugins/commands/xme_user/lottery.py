from xme.plugins.commands.xme_user import __plugin_name__
from nonebot import on_command, CommandSession
from xme.xmetools.doctools import CommandDoc
from xme.xmetools.texttools import remove_punctuation
from xme.xmetools.msgtools import send_session_msg
from xme.xmetools.jsontools import save_to_path, read_from_path
import random
random.seed()
from .classes import user as u
from xme.plugins.commands.xme_user.classes.user import User, coin_name, coin_pronoun
from character import get_message
import traceback

alias = ['抽奖', 'lot']
TIMES_LIMIT = 5
MAX_COIN_COUNT = 50
cmd_name = 'lottery'
usage = {
    "name": cmd_name,
    "desc": get_message("plugins", __plugin_name__, cmd_name, 'desc'),
    "introduction": get_message("plugins", __plugin_name__, cmd_name, 'introduction',  count_max=MAX_COIN_COUNT),
    "usage": f'({coin_name}数量/梭哈) <连续抽取次数>',
    "permissions": [],
    "alias": alias
}

@on_command(cmd_name, aliases=alias, only_to_me=False, permission=lambda _: True)
@u.using_user(save_data=True)
@u.limit(cmd_name, 1, get_message("plugins", __plugin_name__, cmd_name, 'limited', ), TIMES_LIMIT)
async def _(session: CommandSession, user: User):
    message = ""
    arg = remove_punctuation(session.current_arg_text.strip())
    if not arg:
        message = get_message("plugins", __plugin_name__, cmd_name, 'no_arg', )
        await send_session_msg(session, message, tips=True)
        return False
    all_in = False
    times_left_now = TIMES_LIMIT - u.get_limit_info(user, cmd_name)[1]
    count = 1
    arg_list = arg.split(" ")
    if arg.lower() in ["土块", "all", "梭哈", "allin"]:
        all_in = True
        count = times_left_now
        arg = MAX_COIN_COUNT
        for c in range(count):
            if user.coins < MAX_COIN_COUNT:
                count = 1
                break
            if c * MAX_COIN_COUNT < user.coins:
                continue
            count = c
            break
        count = min(times_left_now, count)
        while user.coins - count * arg < 0:
            arg -= 1
        print("count is", count)
    if len(arg_list) > 1 and not all_in:
        arg = arg_list[0]
        if arg_list[1].isdigit() and int(arg_list[1]) > 0:
            count = int(arg_list[1])
        else:
            message = get_message("plugins", __plugin_name__, cmd_name, 'invalid_count')
            await send_session_msg(session, message, tips=True)
            return False
    elif all_in and arg < 1:
        message = get_message("plugins", __plugin_name__, cmd_name, 'all_in_no_coins')
        await send_session_msg(session, message, tips=True)
        return False
    if times_left_now - count < 0:
        await send_session_msg(session, get_message("plugins", __plugin_name__, cmd_name, 'count_limited', times_left=times_left_now, times=count), tips=True)
        return False
    if not all_in:
        try:
            arg = int(arg)
            if arg <= 0:
                message = get_message("plugins", __plugin_name__, cmd_name, 'invalid_arg', )
                await send_session_msg(session, message, tips=True)
                return False
        except ValueError as ex:
            print(ex)
            print(traceback.format_exc())
            message = get_message("plugins", __plugin_name__, cmd_name, 'invalid_arg', )
            await send_session_msg(session, message, tips=True)
            return False

    calc_count = arg * count
    if arg > MAX_COIN_COUNT:
        message = get_message("plugins", __plugin_name__, cmd_name, 'too_many_coins',

            count=arg,

            count_max=MAX_COIN_COUNT
        )
        await send_session_msg(session, message, tips=True)
        return False
    elif user.coins - calc_count < 0:
        message = get_message("plugins", __plugin_name__, cmd_name, 'not_enough_coins',
            count=calc_count,
            coins_left=user.coins,
        )
        await send_session_msg(session, message, tips=True)
        return False
    vars = read_from_path("data/bot_vars.json")
    user.coins -= calc_count
    vars["lottery_get_coins"] += calc_count
    result = 0
    for _ in range(count):
        random.seed()
        result += random.randint(0, int(arg * (random.random() * 1.035 * 4)))
    vars["lottery_lose_coins"] += result
    save_to_path("data/bot_vars.json", vars)
    user.add_coins(result)
    result_content = (get_message("plugins", __plugin_name__, cmd_name, 'get_coin_result',  get_count=result, prefix="一共" if count > 1 else "") if result > 0 else
                      get_message("plugins", __plugin_name__, cmd_name, 'no_coin_result',  get_count=result, ))
    u.limit_count_tick(user, cmd_name, count - 1)
    times_left = TIMES_LIMIT - u.get_limit_info(user, cmd_name)[1] - 1
    message = get_message("plugins", __plugin_name__, cmd_name, 'result',
        count=arg,
        times=f"{count} 次" if count > 1 else "",
        result=result,
        coins_left=user.coins,
        result_content=result_content,
        times_left=times_left
    )

    await send_session_msg(session, message, tips=True)
    if result >= calc_count * 5 and calc_count >= 100:
        await user.achieve_achievement(session, "土块")
    return True