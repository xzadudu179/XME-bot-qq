from xme.plugins.commands.xme_user import __plugin_name__
from nonebot import on_command, CommandSession
from xme.xmetools.msgtools import send_session_msg
from xme.xmetools.imgtools import image_msg
from xme.xmetools.jsontools import save_to_path
from .classes import user as u
from .classes import xme_map
from xme.plugins.commands.xme_user.classes.user import User, coin_name, coin_pronoun
from character import get_message


alias = []
cmd_name = 'map'
usage = {
    "name": cmd_name,
    "desc": get_message("plugins", __plugin_name__, cmd_name, 'desc'),
    "introduction": get_message("plugins", __plugin_name__, cmd_name, 'introduction', coin_name=coin_name),
    "usage": f'',
    "permissions": [],
    "alias": alias
}
@on_command(cmd_name, aliases=alias, only_to_me=False)
@u.using_user(save_data=True)
async def _(session: CommandSession, user: User):
    zoom_fac = 3
    path = await user.draw_user_galaxy_map(zoom_fac=zoom_fac)
    zoom_fac = 1
    path2 = await user.draw_user_starfield_map(zoom_fac=zoom_fac)
    await send_session_msg(session, f"{await image_msg(path, to_jpeg=False)}{await image_msg(path2, to_jpeg=False)}")