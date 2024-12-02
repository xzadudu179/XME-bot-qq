cmd_name = 'game'
from nonebot import on_command, CommandSession
from xme.xmetools.doc_gen import CommandDoc, shell_like_usage
from nonebot.argparse import ArgumentParser
from character import get_message
import xme.xmetools.text_tools as t
from xme.xmetools.command_tools import send_msg
from . import game_commands as games

# introduction = "各种小游戏"
alias = ["游戏", "小游戏", "play", "玩"]
desc = get_message(cmd_name, 'desc')

arg_usage = shell_like_usage("OPTIONS", [
    {
        "name": "help",
        "abbr": "h",
        "desc": get_message(cmd_name, 'option_help_desc'),
        # "desc": "查看帮助"
    },
    {
        "name": "args",
        "abbr": "a",
        "desc": get_message(cmd_name, 'option_args_desc'),
        # "desc": "指定小游戏的参数"
    },
    {
        "name": "info",
        "abbr": "i",
        "desc": get_message(cmd_name, 'option_info_desc')
        # "desc": "查看你输入的小游戏的帮助而不是游玩"
    }
])

game_list_str = "\n".join([f"- {k}\t{v['meta']['desc']}" for k, v in games.games.items()])

docs = str(CommandDoc(
    name=cmd_name,
    desc=desc,
    introduction=get_message(cmd_name, 'introduction').format(games=game_list_str),
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
    return get_message(cmd_name, 'game_help').format(name=result['meta']['name'], introduction=result['meta']['introduction'], args=args_str).strip()
#     return f"""
# 游戏名称：{result['meta']['name']}
# 介绍：{result['meta']['introduction']}
# 参数列表：
# {args_str}
# """.strip()

@on_command(cmd_name, aliases=alias, only_to_me=False, permission=lambda x: x.is_groupchat, shell_like=True)
async def _(session: CommandSession):
    parser = ArgumentParser(session=session, usage=docs)
    parser.add_argument('-a', '--args', nargs='+')
    parser.add_argument('-i', '--info', action='store_true')
    parser.add_argument('text', nargs='+')
    args = parser.parse_args(session.argv)
    text = ' '.join(args.text).strip()
    game_args = {}
    if args.args:
        game_args = {i.split("=")[0].strip(): i.split("=")[1].strip() for i in t.replace_chinese_punctuation(''.join(args.args)).split(",")}
    print(game_args)
    if args.info:
        info = get_game_help(text)
        if not info:
            return await send_msg(session, get_message(cmd_name, 'help_not_found'))
        return await send_msg(session, info)

    game_to_play = games.games.get(text, False)
    if not game_to_play:
        await send_msg(session, get_message(cmd_name, 'game_not_found').format(game_text=text))
        return
    # 玩游戏
    # 游戏以后会返回东西
    game_return = await game_to_play['func'](session, game_args)
    if game_return['message']:
        await send_msg(session, game_return['message'])
    print("游戏执行结束")