from xme.plugins.commands.xme_user import __plugin_name__
from nonebot import on_command, CommandSession
from xme.xmetools.message_tools import send_session_msg
import config
from .classes import user as u
from .classes import xme_map
from xme.plugins.commands.xme_user.classes.user import User, coin_name, coin_pronoun
from character import get_message


# alias = []
# cmd_name = 'test'
# usage = {
#     "name": cmd_name,
#     "desc": get_message("plugins", __plugin_name__, cmd_name, 'desc'),
#     "introduction": get_message("plugins", __plugin_name__, cmd_name, 'introduction', coin_name=coin_name),
#     "usage": f'',
#     "permissions": [],
#     "alias": alias
# }
# @on_command(cmd_name, aliases=alias, only_to_me=False)
# @u.using_user(save_data=False)
# async def _(session: CommandSession, user: User):
#     point = session.current_arg_text.strip().split(" ")
#     galaxy_map = xme_map.GalaxyMap()
#     await user.draw_user_map(galaxy_map, center=(int(point[0]), int(point[1])), zoom_fac=5)
#     path = f'http://server.xzadudu179.top:17980/usermap'
#     # path = f'127.0.0.1:{config.PORT}/usermap'
#     print(galaxy_map.__dict__())
#     await send_cmd_msg(session, f"[CQ:image,file={path}]")

