cmd_name = 'game'
from nonebot import on_command, CommandSession
from xme.xmetools.doctools import CommandDoc, shell_like_usage
from nonebot.argparse import ArgumentParser
from character import get_message
from xme.plugins.commands.xme_user.classes.user import coin_name, coin_pronoun
from xme.plugins.commands.xme_user.classes import user
import xme.xmetools.texttools as t
from xme.xmetools.msgtools import send_session_msg
from . import game_commands as games

# introduction = "各种小游戏"
alias = ["游戏", "小游戏", "play", "玩", 'gm']
desc = get_message("plugins", cmd_name, 'desc')

arg_usage = shell_like_usage("OPTIONS", [
    {
        "name": "help",
        "abbr": "h",
        "desc": get_message("plugins", cmd_name, 'option_help_desc'),
        # "desc": "查看帮助"
    },
    {
        "name": "args",
        "abbr": "a",
        "desc": get_message("plugins", cmd_name, 'option_args_desc'),
        # "desc": "指定小游戏的参数"
    },
    {
        "name": "info",
        "abbr": "i",
        "desc": get_message("plugins", cmd_name, 'option_info_desc')
        # "desc": "查看你输入的小游戏的帮助而不是游玩"
    }
])

game_list_str = "\n".join([f"- {k}\t{v['meta']['desc']}" for k, v in games.games.items()])

docs = str(CommandDoc(
    name=cmd_name,
    desc=desc,
    introduction=get_message("plugins", cmd_name, 'introduction', games=game_list_str),
    # introduction=f'游玩一个小游戏，游戏参数格式为：参数名=参数值（以逗号分隔）\n以下是目前有的所有游戏：\n{game_list_str}',
    usage=f'(小游戏名) [OPTIONS]\n{arg_usage}',
    permissions=[],
    alias=alias
))

def get_game_help(game_name) -> str | bool:
    result = games.games.get(game_name, False)
    if not result:
        return False
    args_str = "\n".join(f"{k}\t {v}" for k, v in result['meta']['args'].items())
    return get_message("plugins", cmd_name, 'game_help', name=result['meta']['name'], introduction=result['meta']['introduction'], args=args_str).strip()
#     return f"""
# 游戏名称：{result['meta']['name']}
# 介绍：{result['meta']['introduction']}
# 参数列表：
# {args_str}
# """.strip()

@on_command(cmd_name, aliases=alias, only_to_me=False, permission=lambda x: True, shell_like=True)
@user.using_user(True)
async def _(session: CommandSession, user: user.User):
    parser = ArgumentParser(session=session, usage=docs)
    parser.add_argument('-a', '--args', nargs='+')
    parser.add_argument('-i', '--info', action='store_true')
    parser.add_argument('text', nargs='+')
    args = parser.parse_args(session.argv)
    text = ' '.join(args.text).strip()
    game_args = {}
    if args.args:
        try:
            game_args = {i.split("=")[0].strip(): i.split("=")[1].strip() for i in t.replace_chinese_punctuation(''.join(args.args)).split(",")}
        except:
            return await send_session_msg(session, get_message("plugins", cmd_name, 'invalid_args'))
    print(game_args)
    if args.info:
        info = get_game_help(text)
        if not info:
            return await send_session_msg(session, get_message("plugins", cmd_name, 'help_not_found'))
        return await send_session_msg(session, info)

    game_to_play = games.games.get(text, False)
    print(text)
    if not game_to_play:
        await send_session_msg(session, get_message("plugins", cmd_name, 'game_not_found', text=text))
        return
    # 玩游戏
    cost = game_to_play['meta'].get('cost', 0)
    if not user.spend_coins(cost):
        return await send_session_msg(session, get_message("plugins", cmd_name, 'not_enough_coins', cost=cost,  ))
    # 游戏以后会返回东西
    game_return = await game_to_play['func'](session, user, game_args)
    print(game_return)
    if game_return['message']:
        await send_session_msg(session, game_return['message'])
    if game_return['state'] in ['EXITED', 'ERROR']:
        return False
    award = game_return['data'].get('award', 'NO_AWARD')
    limited = game_return['data'].get('limited', False)
    times_left = game_return['data'].get('times_left', False)
    messages = []
    if award and award != "NO_AWARD" and not limited:
        user.add_coins(award)
        messages.append(game_to_play['meta']['award_message'].format(
            award=award,
            coins_left=user.coins,
        ))
    elif award == 0:
        messages.append(game_to_play['meta']['no_award_message'].format())
    if times_left != False and not limited:
        messages.append(game_to_play['meta']['times_left_message'].format(times_left=times_left))
    elif limited or times_left <= 0:
        messages.append(game_to_play['meta']['limited_message'])
    message = '\n'.join(messages)
    print(messages)
    if message:
        await send_session_msg(session, message)
    return True