from nonebot import on_command, CommandSession
from xme.xmetools.doc_gen import CommandDoc

alias = ['bot_退群', 'bot_退出群聊', 'bot_exit']
__plugin_name__ = 'bot_leave'
__plugin_usage__ = str(CommandDoc(
    name=__plugin_name__,
    desc='机器人退群',
    introduction='使机器人退出群聊',
    usage=f'',
    permissions=["是群主 或 是 SUPERUSER"],
    alias=alias
))

@on_command(__plugin_name__, aliases=alias, only_to_me=True, permission=lambda x: x.is_superuser or x.is_owner and x.is_groupchat)
async def _(session: CommandSession):
    await session.send("正在退出群聊...")
    await session.bot.api.set_group_leave(group_id=session.event.group_id)