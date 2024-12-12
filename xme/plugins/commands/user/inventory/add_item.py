from xme.plugins.commands.user import __plugin_name__
from xme.plugins.commands.user.inventory import cmd_name
import config
from ..classes import xme_user as u
from ..classes.item import Item
from xme.xmetools.command_tools import send_msg
from character import get_message


async def add(session, user: u.User, arg):
    args = arg.split(" ")
    count = 1
    try:
        id = int(args[0])
    except:
        await send_msg(session,  get_message(__plugin_name__, cmd_name, arg_func_name, "invalid_arg"))
        return False
    try:
        count = int(args[1])
    except TypeError:
        pass
    try:
        print(user)
        if user.inventory.add_item(id, count):
            item = Item.get_item(id)
            await send_msg(session,  get_message(__plugin_name__, cmd_name, arg_func_name, "success", count=count, name=item, pronoun=item.pronoun))
            return True
    except ValueError:
        await send_msg(session,  get_message(__plugin_name__, cmd_name, arg_func_name, "no_item", id=id))
        return False
    await send_msg(session,  get_message(__plugin_name__, cmd_name, arg_func_name, "error"))
    return False

arg_func_name = 'add'
info = {
    "func": add,
    "info": "增加物品（仅限 SUPERUSER）",
    "args": "(物品 id) <物品数量>",
    "permissions": lambda x: x in config.SUPERUSERS
}