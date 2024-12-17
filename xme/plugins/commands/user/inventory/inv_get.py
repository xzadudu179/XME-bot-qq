from xme.plugins.commands.user import __plugin_name__
from xme.plugins.commands.user.inventory import cmd_name
from typing import Any
from ..classes import xme_user as u
from ..classes.inv_item import InvItem
from ..classes.item import Item
from xme.xmetools.command_tools import send_msg
from character import get_message

name = "get"

async def get_inv_item_by_index(session, user: u.User, index_str: str, default=False, silent=False) -> InvItem | Any:
    """通过索引获得物品栏位

    Args:
        session (CommandSession): session
        user (u.User): 当前用户
        index_str (str): 物品栏序号字符串
        default (Any): 默认返回什么. Defaults to False.
        silent (bool): 是否不输出任何信息. Defaults to False.

    Returns:
        InvItem | Any: 获取结果
    """
    if not index_str and not silent:
        await send_msg(session,  get_message(__plugin_name__, cmd_name, name, "no_num"))
    if index_str.isdigit():
        index = int(index_str) - 1
    else:
        if not silent:
            await send_msg(session,  get_message(__plugin_name__, cmd_name, name, "invalid_num"))
        return default

    if index >= len(user.inventory.inv_items) or index < 0:
        if not silent:
            await send_msg(session,  get_message(__plugin_name__, cmd_name, name, "index_out_range", num=index + 1))
        return default

    inv_item = user.inventory.find_item(index)

    if inv_item.recorded_item is None:
        if not silent:
            await send_msg(session,  get_message(__plugin_name__, cmd_name, name, "no_item", num=index + 1))
        return default
    return inv_item

async def get_item_by_name(session, item_name: str, default=False, silent=False, fuzzy=True, threshold=80.0, user: u.User | None = None) -> Item | Any:
    """通过名字获取物品

    Args:
        session (CommandSession): session
        name (str): 物品名
        default (bool, optional): 获取不到时默认返回的值. Defaults to False.
        silent (bool, optional): 是否不输出任何消息. Defaults to False.
        fuzzy (bool, optional): 是否启用模糊搜索. Defaults to True.
        threshold (float, optional): 模糊搜索相似度阈值. Defaults to 80.0.
        user (User, optional): 如果输入用户就会搜索用户物品栏内的东西. Defaults to None.

    Returns:
        Item | Any: 获取结果
    """
    item_list = None
    if user:
        item_list = [item.recorded_item for item in user.inventory.inv_items if item.recorded_item is not None]
    item = Item.get_item_by_name(item_name, fuzzy, threshold, item_list)
    if item is None:
        if not silent:
            await send_msg(session,  get_message(__plugin_name__, cmd_name, name, "no_name_item", name=item_name) if user is None else get_message(__plugin_name__, cmd_name, name, "user_no_item", name=item_name))
        return default
    return item

async def get_item_by_id(session, id_str: str, default=False, silent=False) -> Item | Any:
    """通过 id 获取物品

    Args:
        session (CommandSession): session
        id_str (str): id 字符串
        default (bool, optional): 获取失败时默认返回的内容. Defaults to False.
        silent (bool): 是否不输出任何信息. Defaults to False.

    Returns:
        Item | Any: 获取结果
    """
    if id_str.isdigit():
        id = int(id_str)
    else:
        if not silent:
            await send_msg(session,  get_message(__plugin_name__, cmd_name, name, "invalid_id"))
        return default

    item = Item.get_item(id)
    if item is None:
        if not silent:
            await send_msg(session,  get_message(__plugin_name__, cmd_name, name, "no_id_item", id=str(id)))
        return default
    return item