from xme.plugins.commands.user import __plugin_name__
from xme.plugins.commands.user.inventory import cmd_name
from . import reduce_item
from ..classes import xme_user as u
from xme.xmetools.command_tools import send_cmd_msg
from character import get_message

async def valid_drop(session, _, invitem):
    if not invitem.recorded_item.can_drop():
        send_cmd_msg(session, get_message(__plugin_name__, cmd_name, arg_func_name, "item_cant_drop", name=invitem.recorded_item.name))
        return False
    return True

async def valid_drop_item(session, _, item):
    if not item.can_drop():
        send_cmd_msg(session, get_message(__plugin_name__, cmd_name, arg_func_name, "item_cant_drop", name=item.name))
        return False
    return True

async def drop(session, user: u.User, arg):
    args = arg.split(" ")
    if not args[0].strip():
        await send_cmd_msg(session,  get_message(__plugin_name__, cmd_name, arg_func_name, "no_num"))
        return False

    if len(args) <= 1:
        args.append("")

    if args[0].strip().isdigit():
        result = await reduce_item.reduce_item_by_index(
            session, user, args[0].strip(), args[1],
            action=valid_drop,
            message_key=arg_func_name)
    else:
        result = await reduce_item.reduce_item_by_name(
            session,
            user,
            args[0].strip(),
            args[1],
            action=valid_drop_item,
            message_key=arg_func_name,
            threshold=0.9,
        )

    if result == True:
        return True
    return False

arg_func_name = 'drop'
info = {
    "func": drop,
    "info": "丢弃物品",
    "args": "(物品栏序号或名字) <物品数量，all则丢弃全部>",
    "permissions": lambda _: True
}