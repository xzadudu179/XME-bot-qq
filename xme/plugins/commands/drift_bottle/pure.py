# from xme.xmetools.timetools import *
# from xme.xmetools import jsontools
from character import get_message
from xme.xmetools.msgtools import send_session_msg
from xme.plugins.commands.drift_bottle import __plugin_name__
from nonebot import CommandSession
from xme.xmetools.plugintools import on_command
from xme.xmetools.bottools import permission
from . import DriftBottle

pure_alias = ["净化"]
command_name = 'pure'
@on_command(command_name, aliases=pure_alias, only_to_me=False, permission=lambda x: True)
@permission(lambda sender: sender.is_superuser, permission_help="是 SUPERUSER")
async def _(session: CommandSession):
    message = ''
    arg_text = session.current_arg_text.strip()
    args = arg_text.split(" ")
    if not arg_text:
        await send_session_msg(session, get_message("plugins", __plugin_name__, 'pure_no_arg'))
        return
    # bottles_dict = jsontools.read_from_path('./data/drift_bottles.json')
    # bottles = bottles_dict['bottles']
    error_args = []
    for arg in args:
        bottle: DriftBottle = DriftBottle.get(arg)
        if bottle is None:
            error_args.append((arg, get_message("plugins", __plugin_name__, 'bottle_not_exist')))
            # await send_msg(session, get_message("plugins", __plugin_name__, 'cthulhu_bottle_not_exist', id=arg))
            # return
            continue
        is_special = False
        is_pure = False
        try:
            arg_int = int(arg)
            if arg_int == -179:
                is_special = True
        except ValueError:
            is_pure = True
        if is_special:
            error_args.append((arg, get_message("plugins", __plugin_name__, 'bottle_special')))
            continue
        if is_pure:
            error_args.append((arg, get_message("plugins", __plugin_name__, 'already_pure')))
            continue
        pure_id = f"PURE {arg}"
        bottle.bottle_id = pure_id
    for error_arg in error_args:
        args.remove(error_arg[0])
    if len(error_args) > 0:
        message += get_message("plugins", __plugin_name__, 'error_bottles', ids='\n'.join([f'{i + 1}. #{item} {info}' for i, (item, info) in enumerate(error_args)]))
    prefix = get_message("plugins", __plugin_name__, 'pure_fail')
    if args:
        prefix = get_message("plugins", __plugin_name__, 'pure_success', ids=', '.join([f'#{arg}' for arg in args]))
    bottle.save()
    # jsontools.save_to_path('./data/drift_bottles.json', bottles_dict)
    message = prefix + '\n' + message
    await send_session_msg(session, message)