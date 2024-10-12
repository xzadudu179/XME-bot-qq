from nonebot import on_command, CommandSession
import nonebot
from nonebot.session import BaseSession
from ..xmetools import pair as p
from ..xmetools import date_tools as d
import json
import time

__plugin_name__ = 'wife'
__plugin_usage__ = r"""
今日老婆

wife [at] at参数用于at老婆
cancanneedwife [at用户] 看看被at人的老婆
""".strip()

members = []


@on_command('wife', aliases=('今日老婆'), only_to_me=False, permission=lambda sender: sender.is_groupchat)
async def _(session: CommandSession):
    user_id = session.event.user_id
    group_id = str(session.event.group_id)
    wifeinfo = await group_init(group_id)
    pairs = wifeinfo["groups"].get(group_id, [])
    pair = p.find_pair(pairs, user_id)
    if pair == "":
        message = f"[CQ:at,qq={user_id}] 你今日似乎没有老婆 ovo"
    else:
        pair_user = await session.bot.get_group_member_info(group_id=group_id, user_id=pair)
        name = f"[CQ:at,qq={pair_user['user_id']}]" if session.current_arg_text.strip() == "at" else pair_user['nickname']
        message = f"[CQ:at,qq={user_id}] 你今日的老婆是:\n[CQ:image,file=https://q1.qlogo.cn/g?b=qq&nk={pair_user['user_id']}&s=640]\n{name} ({pair_user['user_id']})"
    await session.send(message)


@on_command('cancanneedwife', aliases=('看看老婆', 'peekwife', 'kkndwife', 'kkndlp', 'kklp'), only_to_me=False, permission=lambda sender: sender.is_groupchat)
async def _(session: CommandSession):
    user_id = session.event.user_id
    group_id = str(session.event.group_id)
    wifeinfo = await group_init(group_id)
    arg = session.current_arg.strip()
    at_id = 0
    if arg.startswith("[CQ:at,qq="):
        at_id = int(arg.split("[CQ:at,qq=")[-1].split("]")[0])
    # 如果是对 xme 说
    elif session.ctx['to_me']:
        at_id = session.self_id
    else:
        await session.send("请 at 你要看的人哦")
        return
    wife = await search_wife(wifeinfo, group_id, at_id, session)
    print(at_id, session.self_id)
    at_name = "我"
    try:
        if at_id != session.self_id:
            at = await session.bot.get_group_member_info(group_id=group_id, user_id=at_id)
            at_name = f"{at['nickname']} ({at_id}) "
        message = f"{at_name}今天并没有老婆ovo"
        if wife:
            # print(pair_user)
            name = wife['nickname']
            message = f"[CQ:at,qq={user_id}] {at_name}今日的老婆是:\n[CQ:image,file=https://q1.qlogo.cn/g?b=qq&nk={wife['user_id']}&s=640]\n{name} ({wife['user_id']})"
    except:
        message = "呜呜，无法获取到你 at 的群员信息"
    await session.send(message)


async def group_init(group_id: str) -> dict:
    """初始化且更新群组老婆信息

    Args:
        group_id (str): 群号

    Returns:
        dict: 群组老婆信息
    """
    global members
    members_full = await nonebot.get_bot().get_group_member_list(group_id=group_id)
    members = [member['user_id'] for member in members_full]
    return wife_update(group_id, members)


def wife_update(group_id: str, members) -> dict:
    """更新老婆数据并且返回wifeinfo

    Args:
        group_id (str): 群号
        members: 群员数据
    Returns:
        群员老婆数据
    """
    days = d.curr_days()
    wifeinfo: dict = {}
    with open("./data/wife.json", 'r', encoding='utf-8') as file:
        wifeinfo = json.load(file)
    pairs = wifeinfo["groups"].get(group_id, [])
    wifeinfo["days"] = days
    if pairs == [] or days > wifeinfo['days']:
        pairs = p.create_pairs(members)
        wifeinfo["groups"][group_id] = pairs
    with open("./data/wife.json", 'w', encoding='utf-8') as file:
        file.write(json.dumps(wifeinfo))
    return wifeinfo


async def search_wife(wifeinfo: dict, group_id: str, user_id: int, session: BaseSession):
    """查找老婆

    Args:
        wifeinfo (dict): 老婆信息字典
        group_id (str): 群号
        user_id (int): qq号
        session (BaseSession): bot session

    Returns:
        用户信息
    """
    pairs = wifeinfo["groups"].get(group_id, [])
    pair = p.find_pair(pairs, user_id)
    if pair == "":
        user = None
    else:
        pair_user = await session.bot.get_group_member_info(group_id=group_id, user_id=pair)
        user = pair_user
    return user