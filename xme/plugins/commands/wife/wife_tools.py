import nonebot
from nonebot.session import BaseSession
from xme.xmetools import listtools as lt
from xme.xmetools import timetools as d
from .wife_tools import *
import json

members = []

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
    # print(wifeinfo)
    info = wifeinfo.get(group_id, {})
    if info == {}:
        wifeinfo[group_id] = {
            "days": 0,
            "members": []
        }
    pairs = info.get("members", [])
    if pairs == [] or days > wifeinfo[group_id]['days']:
        wifeinfo[group_id]["days"] = days
        print("|||更新老婆数据|||")
        pairs = lt.create_pairs(members)
        wifeinfo[group_id]['members'] = pairs
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
    pairs = wifeinfo.get(group_id, {}).get("members", [])
    # print(pairs)
    pair = lt.find_pair(pairs, user_id)
    print(f"pair: {pair}")
    if pair == "":
        user = None
    else:
        pair_user = await session.bot.get_group_member_info(group_id=group_id, user_id=pair)
        user = pair_user
    return user