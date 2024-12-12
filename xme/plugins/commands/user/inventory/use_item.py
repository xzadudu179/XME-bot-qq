from xme.plugins.commands.user import __plugin_name__
from xme.plugins.commands.user.inventory import cmd_name
from . import inv_get
from xme.xmetools.command_tools import send_msg
from character import get_message


async def use(session, user, arg):
    inv_item = await inv_get.get_inv_item_by_index(session, user, arg)
    if not inv_item:
        return False
    item_name = inv_item.recorded_item.name
    if not inv_item.recorded_item.has_action("use"):
        await send_msg(session,  get_message(__plugin_name__, cmd_name, arg_func_name, "cannot_use"))
        return False
    state, result = await inv_item.try_use_item("use", True, session=session, user=user)
    print(f"result: {result}")
    if not state or not result.get("state", True):
        if not result.get("silent", False):
            await send_msg(session,  get_message(__plugin_name__, cmd_name, arg_func_name, "error"))
        return False
    if not result.get("silent", False):
        await send_msg(session, result.get('info', get_message(__plugin_name__, cmd_name, arg_func_name, "default_msg", item=item_name)))
    return True


arg_func_name = 'use'
info = {
    "func": use,
    "info": "使用物品",
    "args": "(物品栏序号)",
    "permissions": lambda _: True
}