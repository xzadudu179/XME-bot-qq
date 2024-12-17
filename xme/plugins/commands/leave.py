from nonebot import on_command, CommandSession
from xme.xmetools.doc_gen import CommandDoc
from xme.xmetools.command_tools import send_msg
from character import get_message, CHARACTER

alias = [f'{get_message("bot_info", "name")}退群', f'{get_message("bot_info", "name")}退出群聊', f'{CHARACTER}_exit']
__plugin_name__ = 'bot_leave'
__plugin_usage__ = str(CommandDoc(
    name=__plugin_name__,
    desc=get_message(__plugin_name__, 'desc'),
    # desc='机器人退群',
    introduction=get_message(__plugin_name__, 'introduction'),
    # introduction='使机器人退出群聊',
    usage=f'',
    permissions=["是群主 或 是 SUPERUSER"],
    alias=alias
))

@on_command(__plugin_name__, aliases=alias, only_to_me=True, permission=lambda x: x.is_superuser or x.is_owner and x.is_groupchat)
async def _(session: CommandSession):
    await send_msg(session, get_message(__plugin_name__, 'leave_message'))
    # await send_msg(session, "正在退出群聊...")
    await session.bot.api.set_group_leave(group_id=session.event.group_id)