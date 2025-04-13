from nonebot import get_bot, NoneBot
import aiocqhttp


async def get_group_member_name(group_id, user_id, card=False, default=None):
    """得到群员名

    Args:
        group_id (int): 群 id
        user_id (int): 用户 id
        card (bool, optional): 是否优先获取群名片. Defaults to False.

    Returns:
        str: 获取结果
    """
    try:
        result = await get_bot().api.get_group_member_info(group_id=group_id, user_id=user_id)
    except:
        return default
    if card:
        result = result['card'] if result['card'] else result['nickname']
    else:
        result = result['nickname']
    return result

async def get_stranger_name(user_id, default=None):
    try:
        result = (await get_bot().api.get_stranger_info(user_id=user_id))['nickname']
    except:
        return default
    return result

async def bot_call_action(bot: NoneBot, action: str, error_action=None, *error_action_args, **kwargs):
    """bot 调用方法

    Args:
        bot (NoneBot): bot 实例
        action (str): 方法名
        error_action (function, optional): 出现错误时调用的异步函数. Defaults to None.

    Returns:
        Any: 调用结束返回的值
    """
    try:
        return await bot.api.call_action(action=action, **kwargs)
    except Exception as ex:
        print(f"bot 调用接口出现错误： {ex}")
        if not error_action:
            raise ex
        return error_action(bot, *error_action_args)

async def get_group_name(group_id, default=None):
    try:
        result = (await get_bot().api.get_group_info(group_id=group_id))['group_name']
    except:
        return default
    return result