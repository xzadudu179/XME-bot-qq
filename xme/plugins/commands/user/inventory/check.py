from xme.plugins.commands.user import __plugin_name__
from xme.plugins.commands.user.inventory import cmd_name
from . import inv_get
from xme.xmetools.message_tools import send_session_msg

async def check(session, user, arg):
    inv_item = await inv_get.get_inv_item_by_index(session, user, arg)
    if not inv_item:
        return False
    await send_session_msg(session, '\n' + inv_item.recorded_item.info())
    return False


arg_func_name = 'check'
info = {
    "func": check,
    "info": "检查物品",
    "args": "(物品栏序号)",
    "permissions": lambda _: True
}