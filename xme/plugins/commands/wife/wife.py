from nonebot import on_command, CommandSession
from xme.xmetools import pair as p
from .wife_tools import *

wife_alias = ['今日老婆']
@on_command('wife', aliases=wife_alias, only_to_me=False, permission=lambda sender: sender.is_groupchat)
async def _(session: CommandSession):
    user_id = session.event.user_id
    group_id = str(session.event.group_id)
    wifeinfo = await group_init(group_id)
    pairs = wifeinfo.get(group_id, {}).get("members")
    pair = p.find_pair(pairs, user_id)
    if pair == "":
        message = f"[CQ:at,qq={user_id}] 你今日似乎没有老婆 ovo"
    else:
        pair_user = await session.bot.get_group_member_info(group_id=group_id, user_id=pair)
        name = f"[CQ:at,qq={pair_user['user_id']}]" if session.current_arg_text.strip() == "at" else pair_user['nickname']
        message = f"[CQ:at,qq={user_id}] 你今日的老婆是:\n[CQ:image,file=https://q1.qlogo.cn/g?b=qq&nk={pair_user['user_id']}&s=640]\n{name} ({pair_user['user_id']})"
    await session.send(message)