from xme.plugins.commands.xme_user import __plugin_name__
from nonebot import on_command, CommandSession
from xme.xmetools.msgtools import send_session_msg
from xme.xmetools.imgtools import gif_msg
from .classes import user as u
from xme.plugins.commands.xme_user.classes.xme_map import StarfieldMap, get_starfield_map
from xme.xmetools.cmdtools import use_args
from xme.plugins.commands.xme_user.classes.user import User, coin_name, coin_pronoun, is_galaxy_loaded
from character import get_message


alias = ['cele', 'celes', '查看天体', '天体']
cmd_name = 'celestial'
usage = {
    "name": cmd_name,
    "desc": get_message("plugins", __plugin_name__, cmd_name, 'desc'),
    "introduction": get_message("plugins", __plugin_name__, cmd_name, 'introduction', ),
    "usage": f'<星域坐标 x> <星域坐标 y>',
    "permissions": [],
    "alias": alias
}
@on_command(cmd_name, aliases=alias, only_to_me=False)
@u.using_user(save_data=True)
@use_args(arg_len=2)
async def _(session: CommandSession, user: User, arg_list: list[str]):
    # if is_galaxy_initing():
        # await send_session_msg(session, get_message("user", "galaxy_initing"))
    if not is_galaxy_loaded():
        await send_session_msg(session, get_message("user", "no_galaxy"))
    starfield: StarfieldMap = user.get_starfield()
    if arg_list[0].isdigit() and arg_list[1].isdigit():
        celestial = starfield.get_celestial(tuple([int(a) for a in arg_list]))
        if not celestial:
            return await send_session_msg(session, get_message("plugins", __plugin_name__, cmd_name, 'no_celestial'))
    elif (not arg_list[0].isdigit() or not arg_list[1].isdigit()) and arg_list[0]:
        return await send_session_msg(session, get_message("plugins", __plugin_name__, cmd_name, 'invalid_args'))
    else:
        celestial = user.celestial
    img = celestial.get_image("")
    return await send_session_msg(session, get_message("plugins", __plugin_name__, cmd_name, 'output', img=await gif_msg(img, scale=3) if img else "", desc=str(celestial)))
