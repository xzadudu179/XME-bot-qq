from xme.plugins.commands.xme_user import __plugin_name__
from xme.plugins.commands.xme_user.inventory import cmd_name
from . import inv_get
from ..classes import user as u
from ..classes.inv_item import InvItem
from ..classes.item import Item
from xme.xmetools.msgtools import send_session_msg
from character import get_message

name = "reduce"

def try_get_msg(message_value, key, default, **kwargs):
    """尝试通过自定义键获得消息

    Args:
        message_value (str): 消息名
        key (str): 自定义键
        default (str): 获取消息失败后用的默认键

    Returns:
        str: 获取到的消息
    """
    # print(value)
    result = get_message("plugins", __plugin_name__, cmd_name, key, message_value, default='[NULL]',**kwargs)
    if result == '[NULL]':
        return get_message("plugins", __plugin_name__, cmd_name, default, message_value, **kwargs)
    return result

async def reduce_item_by_id(
        session,
        user: u.User,
        id_str: str,
        count_str: str,
        default=False,
        action=None,
        message_key=name,
        silent=False,
        reduce_method=lambda inventory, item, count: inventory.reduce_item(item.id, count),
        **message_kwargs
    ):
    """通过 id 移除物品

    Args:
        session (CommandSession): session
        user (u.User): 用户
        id_str (str): 物品 id 字符串
        count_str (str): 移除数量字符串
        default (bool, optional): 移除失败默认返回的值. Defaults to False.
        action (function, optional): 自定义操作获取到的 Item 的函数. Defaults to None.
        message_key (str): 自定义 success 时消息发送的键名
        silent (bool): 出现错误时不发送任何消息
        reduce_method (function): 移除物品时调用的方法
        **message_kwargs: 自定义 success 时消息发送的字符串 format 键值对

    Returns:
        bool | Any: 移除结果
    """
    count = 1
    item_get: Item = await inv_get.get_item_by_id(session, id_str, silent=silent)
    print(type(item_get))
    if not item_get:
        return default

    if action and not (await action(session, user, item_get)):
        return default

    item_name = item_get.name
    item_pronoun = item_get.pronoun

    if count_str and not count_str.isdigit() and not count_str == 'all':
        if not silent:
            await send_session_msg(session,  try_get_msg("invalid_count", message_key, name))
            # await send_msg(session,  get_message("plugins", __plugin_name__, cmd_name, name, "invalid_count"))
        return default
    elif count_str == 'all':
        count = user.inventory.count_item(item_get)
    elif count_str:
        count = int(count_str)

    if count <= 0:
        if not silent:
            await send_session_msg(session, try_get_msg("invalid_count", message_key, name))
        return default
    if count > user.inventory.count_item(item_get):
        if not silent:
            await send_session_msg(session, try_get_msg("item_count_too_many", message_key, name))
        return default

    if reduce_method(user.inventory, item_get, count):
    # if user.inventory.reduce_item(item.id, count):
        if message_key:
            if not silent:
                await send_session_msg(session,  try_get_msg("success", message_key, name, count=count, name=item_name, pronoun=item_pronoun, **message_kwargs))
                # await send_msg(session,  get_message("plugins", __plugin_name__, cmd_name, message_key, "success", count=count, name=item_name, pronoun=item_pronoun, **message_kwargs))
        return True
    else:
        if not silent:
            await send_session_msg(session,  try_get_msg("error", message_key, name, count=count, name=item_name, pronoun=item_pronoun))
            # await send_msg(session,  get_message("plugins", __plugin_name__, cmd_name, name, "error", count=count, name=item_name, pronoun=item_pronoun))
    return default

async def reduce_item_by_name(
        session,
        user: u.User,
        item_name: str,
        count_str: str,
        default=False,
        action=None,
        message_key=name,
        silent=False,
        reduce_method=lambda inventory, item, count: inventory.reduce_item(item.id, count),
        fuzzy=True,
        threshold=0.8,
        **message_kwargs
    ):
    """通过名字移除物品

    Args:
        session (CommandSession): session
        user (u.User): 需要操作的用户
        item_name (str): 物品名
        count_str (str): 物品数量字符串
        default (bool, optional): 移除失败默认返回的值. Defaults to False.
        action (function, optional): 自定义操作获取到的 Item 的函数. Defaults to None.
        message_key (str, optional): 自定义 success 时消息发送的键名. Defaults to name.
        silent (bool, optional): 出现错误时不发送任何消息. Defaults to False.
        reduce_method (_type_, optional): 移除物品时调用的方法. Defaults to lambdainventory.
        fuzzy (bool, optional): 是否启用模糊搜索. Defaults to True.
        threshold (float, optional): 模糊搜索阈值. Defaults to 0.8.

    Returns:
        bool | Any: 移除结果
    """
    item: Item = await inv_get.get_item_by_name(session, item_name, silent=silent, fuzzy=fuzzy, threshold=threshold, user=user)
    if not item:
        return default
    # 懒了
    return await reduce_item_by_id(session, user, str(item.id), count_str, default, action, message_key, silent, reduce_method, **message_kwargs)

async def reduce_item_by_index(
        session,
        user: u.User,
        index_str: str,
        count_str: str,
        default=False,
        action=None,
        message_key=name,
        silent=False,
        reduce_method=lambda inv_item, count: inv_item.try_reduce_item(count=count),
        **message_kwargs
    ):
    """通过物品栏序号移除物品

    Args:
        session (CommandSession): session
        user (u.User): 用户
        index_str (str): 物品栏序号字符串
        count_str (str): 移除数量字符串
        default (bool, optional): 移除失败默认返回的值. Defaults to False.
        action (function, optional): 自定义操作获取到的 InvItem 的函数. Defaults to None.
        message_key (str): 自定义 success 时消息发送的键名
        silent (bool): 出现错误时不发送任何消息. Defaults to False.
        sell (bool): 是否是卖物品而不是移除物品. Defaults to False.
        **message_kwargs: 自定义 success 时消息发送的字符串 format 键值对

    Returns:
        bool | Any: 移除结果
    """
    count = 1
    inv_item: InvItem = await inv_get.get_inv_item_by_index(session, user, index_str, silent=silent)
    if not inv_item:
        return default

    if action and not (await action(session, user, inv_item)):
        return default

    item_name = inv_item.recorded_item.name
    item_pronoun = inv_item.recorded_item.pronoun

    if count_str and not count_str.isdigit() and not count_str == "all":
        if not silent:
            await send_session_msg(session,  try_get_msg("invalid_count", message_key, name))
        return default

    if count_str == "all":
        count = inv_item.count
    elif count_str.isdigit():
        count = int(count_str)

    if count > inv_item.count:
        if not silent:
            await send_session_msg(session,  try_get_msg("count_too_many", message_key, name))
        return default

    if count <= 0:
        if not silent:
            await send_session_msg(session,  try_get_msg("invalid_count", message_key, name))
        return default
    result = reduce_method(inv_item, count)
    # result = inv_item.try_reduce_item(count=count)
    if result:
        if message_key and not silent:
            await send_session_msg(session,  try_get_msg("success", message_key, name, count=count, name=item_name, pronoun=item_pronoun, **message_kwargs))
        return result
    else:
        if not silent:
            await send_session_msg(session,  try_get_msg("error", message_key, name, count=count, name=item_name))
    return default
