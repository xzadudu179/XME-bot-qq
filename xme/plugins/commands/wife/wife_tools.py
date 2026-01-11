import nonebot
from nonebot.session import BaseSession
from xme.xmetools import listtools as lt
from xme.xmetools import timetools as d
import json
import random

# members = []

async def group_init(group_id: str) -> dict:
    """初始化且更新群组老婆信息

    Args:
        group_id (str): 群号

    Returns:
        dict: 群组老婆信息
    """
    return wife_update(group_id)
    # global members
    # members_full = await nonebot.get_bot().get_group_member_list(group_id=group_id)
    # members = [member['user_id'] for member in members_full]
    # # load or create wifeinfo entry for this group
    # with open("./data/wife.json", 'r', encoding='utf-8') as file:
    #     wifeinfo = json.load(file)
    # if group_id not in wifeinfo:
    #     wifeinfo[group_id] = {
    #         "days": d.curr_days(),
    #         "members": []
    #     }
    #     with open("./data/wife.json", 'w', encoding='utf-8') as file:
    #         file.write(json.dumps(wifeinfo))
    # return wifeinfo


def wife_update(group_id: str) -> dict:
    """更新老婆数据并且返回wifeinfo

    Args:
        group_id (str): 群号
        members: 群员数据
    Returns:
        群员老婆数据
    """
    # Keep for backward compatibility but do not auto-generate pairs anymore.
    days = d.curr_days()
    with open("./data/wife.json", 'r', encoding='utf-8') as file:
        wifeinfo = json.load(file)
    print(days, wifeinfo[group_id]['days'], days > wifeinfo[group_id]['days'])
    if group_id not in wifeinfo or days > wifeinfo[group_id]['days']:
        wifeinfo[group_id] = {"days": days, "members": []}
        with open("./data/wife.json", 'w', encoding='utf-8') as file:
            file.write(json.dumps(wifeinfo))
    return wifeinfo


def _save_wifeinfo(wifeinfo: dict):
    with open("./data/wife.json", 'w', encoding='utf-8') as file:
        file.write(json.dumps(wifeinfo))


def _load_wifeinfo() -> dict:
    with open("./data/wife.json", 'r', encoding='utf-8') as file:
        return json.load(file)


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
    members_full = await nonebot.get_bot().get_group_member_list(group_id=group_id)
    members = [member['user_id'] for member in members_full]
    pairs = wifeinfo.get(group_id, {}).get("members", [])
    pair = lt.find_pair(pairs, user_id)
    # print(f"pair: {pair}")
    if pair != "":
        try:
            pair_user = await session.bot.get_group_member_info(group_id=group_id, user_id=pair)
        except:
            pair_user = await session.bot.get_stranger_info(user_id=pair)
        return pair_user

    # No existing partner: try to assign one for the caller
    paired_ids = set()
    for p in pairs:
        for x in p:
            paired_ids.add(x)
    candidates = [m for m in members if m not in paired_ids and m != user_id]
    # print("candidates", candidates)
    # print("paired_ids", paired_ids)
    if not candidates:
        return None
    random.seed()
    partner = random.choice(candidates)
    pairs.append((user_id, partner))
    wifeinfo[group_id]['members'] = pairs
    _save_wifeinfo(wifeinfo)
    try:
        pair_user = await session.bot.get_group_member_info(group_id=group_id, user_id=partner)
    except:
        pair_user = await session.bot.get_stranger_info(user_id=partner)
    return pair_user


# async def change_wife(wifeinfo: dict, group_id: str, user_id: int, session: BaseSession):
#     """Change the caller's wife to a new random unpaired member.

#     Returns the new partner user object, or None if no wife to change or no candidates.
#     """
#     pairs = wifeinfo.get(group_id, {}).get("members", [])
#     current_partner = lt.find_pair(pairs, user_id)
#     if current_partner == "":
#         return None

#     # Build set of currently paired ids
#     paired_ids = set()
#     for p in pairs:
#         for x in p:
#             paired_ids.add(x)

#     # Exclude current partner so the new one is different
#     candidates = [m for m in members if m not in paired_ids and m != user_id]
#     if not candidates:
#         return None

#     random.seed()
#     new_partner = random.choice(candidates)

#     # remove existing pair containing user_id
#     for i, p in enumerate(pairs):
#         if user_id in p:
#             pairs.pop(i)
#             break
#     pairs.append((user_id, new_partner))
#     wifeinfo[group_id]['members'] = pairs
#     _save_wifeinfo(wifeinfo)
#     try:
#         partner_user = await session.bot.get_group_member_info(group_id=group_id, user_id=new_partner)
#     except:
#         partner_user = await session.bot.get_stranger_info(user_id=new_partner)
#     return partner_user