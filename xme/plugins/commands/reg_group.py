# from nonebot import CommandSession
# from xme.xmetools.plugintools import on_command
# from xme.xmetools.cmdtools import use_args
# from xme.xmetools.doctools import CommandDoc
# # from aiocqhttp import Message
# from character import get_message
# from xme.xmetools.msgtools import send_session_msg, aget_session_msg, aget_arg
# # from xme.plugins.commands.xme_user.classes import user

# alias = ['登记群']
# __plugin_name__ = 'group'
# __plugin_usage__ = CommandDoc(
#     name=__plugin_name__,
#     desc=get_message("plugins", __plugin_name__, 'desc'),
#     # desc='查看系统状态',
#     introduction=get_message("plugins", __plugin_name__, 'introduction'),
#     # introduction='查看运行该 XME-Bot 实例的设备的系统状态',
#     usage='',
#     permissions=["无"],
#     alias=alias
# )


# @on_command(__plugin_name__, aliases=alias, only_to_me=False, permission=lambda _: True)
# @use_args(arg_len=3)
# async def _(session: CommandSession, args: list[str]):
#     for a in args:
#         if a:
#             continue
#         await aget_arg(
#                 session,

#             )
