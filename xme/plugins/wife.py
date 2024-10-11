from nonebot import on_command, CommandSession
from ..xmetools import pair as p
import time

__plugin_name__ = 'wife'
__plugin_usage__ = r"""
今日老婆

wife [at] at参数用于at老婆
""".strip()

@on_command('wife', aliases=('今日老婆'), only_to_me=False, permission=lambda sender: sender.is_groupchat)
async def echo(session: CommandSession):
    user_id = session.event.user_id
    group_id = session.event.group_id
    members_full = await session.bot.get_group_member_list(group_id=group_id)
    members = [member['user_id'] for member in members_full]
    members = sorted(members)
    seed = int(time.time() // 86400)
    pairs = p.create_pairs(seed, members)
    pair = p.find_pair(pairs, user_id)
    if pair == "":
        message = f"[CQ:at,qq={user_id}] 你今日似乎没有老婆 ovo"
    else:
        pair_user = await session.bot.get_group_member_info(group_id=group_id, user_id=pair)
        # print(pair_user)
        name = f"[CQ:at,qq={pair_user['user_id']}]" if session.current_arg_text.strip() == "at" else pair_user['nickname']
        message = f"[CQ:at,qq={user_id}] 你今日的老婆是:\n[CQ:image,file=https://q1.qlogo.cn/g?b=qq&nk={pair_user['user_id']}&s=640]\n{name} ({pair_user['user_id']})"
    # print(message)
    await session.send(message)