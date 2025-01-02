from xme.plugins.commands.user import __plugin_name__
from nonebot import on_command, CommandSession
from xme.xmetools.doc_tools import CommandDoc
from xme.xmetools.command_tools import send_cmd_msg
from xme.plugins.commands.user.classes import xme_user
from xme.xmetools import text_tools
from xme.plugins.commands.user.classes.xme_user import User, coin_name, coin_pronoun
from character import get_message
import statistics


alias = ['rank', f'{coin_name}排行', 'ranking']
MAX_RANK_COUNT = 20
cmd_name = 'coinrank'
usage = {
    "name": cmd_name,
    "desc": get_message(__plugin_name__, cmd_name, 'desc', coin_name=coin_name),
    "introduction": get_message(__plugin_name__, cmd_name, 'introduction', coin_name=coin_name),
    "usage": f'<参数>',
    "permissions": [],
    "alias": alias
}
def rank_operation(func, rank_items):
    return func([item[1] for item in rank_items])

@on_command(cmd_name, aliases=alias, only_to_me=False)
async def _(session: CommandSession):
    sender = session.event.user_id
    message = get_message(__plugin_name__, cmd_name, 'rank_msg_prefix', coin_name=coin_name, coin_pronoun=coin_pronoun)
    arg = session.current_arg_text.strip().lower()
    spacing = False
    if arg:
        spacing = arg.split(" ")[-1] == 'spacing'
        arg = arg.split(" ")[0].replace('spacing', '')
    print(spacing)
    rank_count = 10
    rank_items = xme_user.get_rank('coins')
    if arg and arg == 'avg':
        # 平均值消息
        rank_avg = rank_operation(lambda x: sum(x) / len(x), rank_items)
        message = get_message(__plugin_name__, cmd_name, 'rank_msg_avg',
            coin_name=coin_name,
            coin_pronoun=coin_pronoun,
            avg=int(rank_avg),
            median=int(rank_operation(lambda x: statistics.median(x), rank_items))
        )
        await send_cmd_msg(session, message)
        return True
    elif arg and arg == 'sum':
        # 总和消息
        rank_sum = rank_operation(lambda x: sum(x), rank_items)
        message = get_message(__plugin_name__, cmd_name, 'rank_msg_sum',
            coin_name=coin_name,
            coin_pronoun=coin_pronoun,
            sum=rank_sum
        )
        await send_cmd_msg(session, message)
        return True
    elif arg:
        try:
            rank_count = int(arg)
            if rank_count <= 0:
                await send_cmd_msg(session, get_message(__plugin_name__, cmd_name, 'count_too_small'))
                return False
            elif rank_count > MAX_RANK_COUNT:
                await send_cmd_msg(session, get_message(__plugin_name__, cmd_name, 'count_too_large', count_max=MAX_RANK_COUNT))
                return False
        except ValueError:
            await send_cmd_msg(session, get_message(__plugin_name__, cmd_name, 'invalid_arg'))
            return False
    # rank_items = rank.items()[:10]
    print(rank_items)
    rank_items_short = rank_items[:rank_count]
    print("查询中")
    u_names = {k: v for k, v in [(id, (await session.bot.api.get_stranger_info(user_id=id))['nickname']) for id, _ in rank_items_short]}
    # print(u_names)
    for i, (id, v) in enumerate(rank_items_short):
        # u_name = (await session.bot.api.get_stranger_info(user_id=id))['nickname']
        nickname = u_names[id]
        message += '\n' + get_message(__plugin_name__, cmd_name, 'ranking_row',
            rank=i + 1,
            nickname=str(nickname),
            coins_count=v,
            coin_pronoun=coin_pronoun,
            coin_name=coin_name,
            spacing=" " * text_tools.calc_spacing([f'{i + 1}. {name}: ' for name in u_names.values()], nickname, 2) if spacing else '\n\t'
        )
    # 关于发送者的金币数超过了多少人
    sender_coins_count, rank_ratio = xme_user.get_user_rank(sender)
    message += '\n' + get_message(__plugin_name__, cmd_name, 'ranking_suffix',
        count=sender_coins_count,
        rank_ratio=f"{rank_ratio:.2f}",
        coin_pronoun=coin_pronoun,
        coin_name=coin_name
    )
    await send_cmd_msg(session, message)
    return True
