from xme.xmetools.timetools import *
from xme.xmetools import jsontools
from character import get_message
from xme.xmetools.msgtools import send_session_msg
from xme.plugins.commands.drift_bottle import __plugin_name__
from nonebot import CommandSession
from xme.xmetools.plugintools import on_command
from xme.xmetools.bottools import permission
from . import DriftBottle

cthulhu_alias = ["毁坏瓶子", "break", "break_bottle"]
command_name = 'cthulhu'
@on_command(command_name, aliases=cthulhu_alias, only_to_me=False, permission=lambda x: True)
@permission(lambda sender: sender.is_superuser, permission_help="是 SUPERUSER")
async def _(session: CommandSession):
    message = ''
    arg_text = session.current_arg_text.strip()
    args = arg_text.split(" ")
    if not arg_text:
        await send_session_msg(session, get_message("plugins", __plugin_name__, 'cthulhu_no_arg'))
        return
    # bottles_dict = jsontools.read_from_path('./data/drift_bottles.json')
    # bottles = bottles_dict['bottles']
    error_args = []
    for arg in args:
        # bottle = bottles.get(arg, None)
        bottle: DriftBottle = DriftBottle.get(arg)
        if bottle is None:
            error_args.append((arg, get_message("plugins", __plugin_name__, 'bottle_not_exist')))
            # await send_msg(session, get_message("plugins", __plugin_name__, 'cthulhu_bottle_not_exist', id=arg))
            # return
            continue
        is_special = False
        try:
            arg_int = int(arg)
            if arg_int == -179:
                is_special = True
        except ValueError:
            is_special = True
        if is_special:
            error_args.append((arg, get_message("plugins", __plugin_name__, 'bottle_special')))
            continue
        if bottle.views == 114514:
            error_args.append((arg, get_message("plugins", __plugin_name__, 'cthulhu_bottle_already_broken')))
            continue
        bottle.views = 114514
        bottle.save()
    for error_arg in error_args:
        args.remove(error_arg[0])
    if len(error_args) > 0:
        message += get_message("plugins", __plugin_name__, 'error_bottles', ids='\n'.join([f'{i + 1}. #{item} {info}' for i, (item, info) in enumerate(error_args)]))
    prefix = get_message("plugins", __plugin_name__, 'cthulhu_fail')
    if args:
        prefix = get_message("plugins", __plugin_name__, 'cthulhu_success', ids=', '.join([f'#{arg}' for arg in args]))
    # jsontools.save_to_path('./data/drift_bottles.json', bottles_dict)
    message = prefix + '\n' + message
    await send_session_msg(session, message)