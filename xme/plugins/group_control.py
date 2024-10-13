from nonebot import on_command, CommandSession

__plugin_name__ = 'leave_group'
__plugin_usage__ = r"""
使机器人退出群聊

leave_group
""".strip()

@on_command('leave_group', aliases=('退群', '退出群聊', 'leave'), only_to_me=True, permission=lambda x: x.is_superuser or x.is_owner)
async def _(session: CommandSession):
    await session.send("正在退出群聊...")
    await session.bot.api.set_group_leave(group_id=session.event.group_id)