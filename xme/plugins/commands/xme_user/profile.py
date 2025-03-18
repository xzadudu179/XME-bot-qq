# from xme.plugins.commands.xme_user import __plugin_name__
# from nonebot import on_command, CommandSession
# from xme.xmetools.msgtools import send_session_msg
# from xme.xmetools import randtools
# from .classes import user as u
# from xme.plugins.commands.xme_user.classes.user import User, coin_name, coin_pronoun
# from character import get_message


# alias = ['pf', 'bio', 'intro']
# cmd_name = 'profile'
# usage = {
#     "name": cmd_name,
#     "desc": get_message("plugins", __plugin_name__, cmd_name, 'desc'),
#     "introduction": get_message("plugins", __plugin_name__, cmd_name, 'introduction', coin_name=coin_name),
#     "usage": f'<at人>',
#     "permissions": [],
#     "alias": alias
# }
# @on_command(cmd_name, aliases=alias, only_to_me=False)
# @u.using_user(save_data=False)
# async def _(session: CommandSession, user: User):
#     arg = session.current_arg.strip()
#     at_id = 0
#     if arg.startswith("[CQ:at,qq="):
#         at_id = int(arg.split("[CQ:at,qq=")[-1].split(",")[0])
#     if at_id != 0:
#         user = u.User.load(at_id, False)
#     else:
#         at_id = session.event.user_id
#     if not user:
#         message = get_message("plugins", __plugin_name__, cmd_name, 'no_user')
#         await send_session_msg(session, message)
#         return False
#     target_user = (await session.bot.api.get_stranger_info(user_id=at_id))['nickname']
#     reaction = "\n" + get_message("bot_info", "name") + ": " + get_message("character", "info_reactions") if randtools.random_percent(max(100, max(0, user.xme_favorability))) else ""
#     message = f'\n{target_user}\n' + str(user) + reaction
#     await send_session_msg(session, message)
#     return True