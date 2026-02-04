# from xme.plugins.commands.xme_user import __plugin_name__
# from xme.plugins.commands.xme_user.inventory import cmd_name
from . import inv_get
from .inv_get import InvItem
from xme.xmetools.msgtools import send_session_msg

async def check(session, user, arg):
    inv_item: InvItem = await inv_get.get_inv_item_by_index(session, user, arg)
    if not inv_item:
        return False
    await send_session_msg(session, '\n' + inv_item.recorded_item.info(inv_item.count), tips=True, tips_percent=10)
    return False


arg_func_name = 'check'
info = {
    "func": check,
    "info": "检查物品",
    "args": "(物品栏序号)",
    "permissions": lambda _: True
}