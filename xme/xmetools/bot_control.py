from nonebot import get_bot


async def get_group_member_name(group_id, user_id, card=False):
    """得到群员名

    Args:
        group_id (int): 群 id
        user_id (int): 用户 id
        card (bool, optional): 是否优先获取群名片. Defaults to False.

    Returns:
        str: 获取结果
    """
    result = await get_bot().api.get_group_member_info(group_id=group_id, user_id=user_id)
    if card:
        result = result['card'] if result['card'] else result['nickname']
    else:
        result = result['nickname']
    return result