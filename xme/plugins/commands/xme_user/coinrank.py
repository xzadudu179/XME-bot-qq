from xme.plugins.commands.xme_user import __plugin_name__
from nonebot import on_command, CommandSession
from xme.xmetools.doctools import CommandDoc
from xme.xmetools.msgtools import send_session_msg
from xme.plugins.commands.xme_user.classes import user
from xme.xmetools import texttools
from xme.plugins.commands.xme_user.classes.user import User, coin_name, coin_pronoun
from character import get_message
import statistics


alias = ['rank', f'{coin_name}排行', 'ranking']
MAX_RANK_COUNT = 20
cmd_name = 'coinrank'
usage = {
    "name": cmd_name,
    "desc": get_message("plugins", __plugin_name__, cmd_name, 'desc', ),
    "introduction": get_message("plugins", __plugin_name__, cmd_name, 'introduction', ),
    "usage": f'<参数>',
    "permissions": [],
    "alias": alias
}
def rank_operation(func, rank_items):
    return func([item[1] for item in rank_items])

@on_command(cmd_name, aliases=alias, only_to_me=False)
async def _(session: CommandSession):
    sender = session.event.user_id
    message = get_message("plugins", __plugin_name__, cmd_name, 'rank_msg_prefix',  )
    arg = session.current_arg_text.strip().lower()
    spacing = False
    if arg:
        spacing = arg.split(" ")[-1] == 'spacing'
        arg = arg.split(" ")[0].replace('spacing', '')
    print(spacing)
    rank_count = 10
    rank_items = user.get_rank('coins')
    if arg and arg == 'avg':
        # 平均值消息
        rank_avg = rank_operation(lambda x: sum(x) / len(x), rank_items)
        message = get_message("plugins", __plugin_name__, cmd_name, 'rank_msg_avg',


            avg=int(rank_avg),
            median=int(rank_operation(lambda x: statistics.median(x), rank_items))
        )
        await send_session_msg(session, message)
        return True
    elif arg and arg == 'sum':
        # 总和消息
        rank_sum = rank_operation(lambda x: sum(x), rank_items)
        message = get_message("plugins", __plugin_name__, cmd_name, 'rank_msg_sum',


            sum=rank_sum
        )
        await send_session_msg(session, message)
        return True
    elif arg:
        try:
            rank_count = int(arg)
            if rank_count <= 0:
                await send_session_msg(session, get_message("plugins", __plugin_name__, cmd_name, 'count_too_small'))
                return False
            elif rank_count > MAX_RANK_COUNT:
                await send_session_msg(session, get_message("plugins", __plugin_name__, cmd_name, 'count_too_large', count_max=MAX_RANK_COUNT))
                return False
        except ValueError:
            await send_session_msg(session, get_message("plugins", __plugin_name__, cmd_name, 'invalid_arg'))
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
        message += '\n' + get_message("plugins", __plugin_name__, cmd_name, 'ranking_row',
            rank=i + 1,
            nickname=str(nickname),
            coins_count=v,


            spacing=" " * texttools.calc_spacing([f'{i + 1}. {name}: ' for name in u_names.values()], nickname, 2) if spacing else '\n\t'
        )
    # 关于发送者的金币数超过了多少人
    sender_coins_count, rank_ratio = user.get_user_rank(sender)
    message += '\n' + get_message("plugins", __plugin_name__, cmd_name, 'ranking_suffix',
        count=sender_coins_count,
        rank_ratio=f"{rank_ratio:.2f}",


    )
    await send_session_msg(session, message)
    return True
