
# from nonebot.session import BaseSession
# from xme.xmetools import listtools as lt
from xme.xmetools import timetools as d
import json
import random
from typing import List, Optional, Tuple

# import random
# from typing import List, Optional, Tuple

def add_random_pair(
    pairs: List[List[int]],
    candidates: List[int],
    new_value: int
) -> Tuple[Optional[List[List[int]]], Optional[int]]:

    used_numbers = {num for pair in pairs for num in pair}
    unused = [n for n in candidates if n not in used_numbers]

    if unused == [new_value]:
        pairs.append([new_value, new_value])
        return pairs, -1

    if new_value in used_numbers:
        return None, None
    available = [n for n in unused if n != new_value]

    if not available:
        return None, None

    partner = random.choice(available)
    pairs.append([new_value, partner])
    return pairs, partner


def group_init(group_id: str) -> dict:
    """初始化且群组老婆信息

    Args:
        group_id (str): 群号

    Returns:
        dict: 群组老婆信息
    """
    # Keep for backward compatibility but do not auto-generate pairs anymore.
    days = d.curr_days()
    with open("./data/wife.json", 'r', encoding='utf-8') as file:
        wifeinfo = json.load(file)
    # debug_msg(days, wifeinfo[group_id]['days'], days > wifeinfo[group_id]['days'])
    if group_id not in wifeinfo or days > wifeinfo[group_id]['days']:
        wifeinfo[group_id] = {"days": days, "members": []}
        with open("./data/wife.json", 'w', encoding='utf-8') as file:
            file.write(json.dumps(wifeinfo))
    return wifeinfo

def find_pair_value(pairs, target):
    for a, b in pairs:
        if a == target:
            return b
        if b == target:
            return a
    return None

def get_wife_id(group_id, user_id, group_members, can_gen=True):
    w_info: dict = group_init(group_id)
    group_wife_info = w_info[group_id]
    ms = group_wife_info["members"]
    wife_id = find_pair_value(ms, user_id)
    print(group_id, user_id, can_gen)
    if wife_id == user_id:
        return "NO_WIFE"
    if wife_id is not None:
        return wife_id
    if not can_gen:
        return "CANT_GEN"
    new_ms, wife_id = add_random_pair(ms, group_members, user_id)
    if new_ms is not None:
        with open("./data/wife.json", 'w', encoding='utf-8') as file:
            group_wife_info["members"] = new_ms
            file.write(json.dumps(w_info))
        if wife_id == -1:
            return "NO_WIFE"
        return wife_id
    return "NO_WIFE"


def change_wife(
    pairs: List[List[int]],
    candidates: List[int],
    user_id: int
) -> Optional[int]:
    old_pair = None
    for pair in pairs:
        if user_id in pair:
            old_pair = pair
            break
    if old_pair is None:
        return None

    old_wife = old_pair[1] if old_pair[0] == user_id else old_pair[0]
    pairs.remove(old_pair)
    used_numbers = {num for pair in pairs for num in pair}
    used_numbers.add(user_id)
    available = [
        n for n in candidates
        if n not in used_numbers and n != old_wife
    ]

    if len(available) <= 1:
        return None

    new_wife = random.choice(available)
    pairs.append([user_id, new_wife])
    return new_wife


def change_wife_id(group_id, user_id, group_members):
    w_info = group_init(group_id)
    group_wife_info = w_info[group_id]
    ms = group_wife_info["members"]

    new_wife = change_wife(ms, group_members, user_id)
    if new_wife is None:
        return None

    with open("./data/wife.json", 'w', encoding='utf-8') as file:
        file.write(json.dumps(w_info))

    return new_wife
