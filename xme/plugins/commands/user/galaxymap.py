from xme.plugins.commands.user import __plugin_name__
from nonebot import on_command, CommandSession
from xme.xmetools.command_tools import send_msg
from .classes import xme_user as u
from .classes import map
from xme.plugins.commands.user.classes.xme_user import User, coin_name, coin_pronoun
from character import get_message


alias = ['t']
cmd_name = 'test'
usage = {
    "name": cmd_name,
    "desc": get_message(__plugin_name__, cmd_name, 'desc'),
    "introduction": get_message(__plugin_name__, cmd_name, 'introduction', coin_name=coin_name),
    "usage": f'',
    "permissions": [],
    "alias": alias
}
@on_command(cmd_name, aliases=alias, only_to_me=False)
@u.using_user(save_data=False)
async def _(session: CommandSession, user: User):
    point = session.current_arg_text.strip().split(" ")
    await user.draw_galaxy_map(map.GalaxyMap(), center=(int(point[0]), int(point[1])), zoom_fac=10)
    path = f'http://server.xzadudu179.top:17980/map'
    await send_msg(session, f"[CQ:image,file={path}]")