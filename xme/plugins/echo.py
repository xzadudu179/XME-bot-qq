from nonebot import on_command, CommandSession

__plugin_name__ = 'echo'
__plugin_usage__ = r"""
重复

echo  [内容]
""".strip()

@on_command('echo', aliases=('e'), only_to_me=False)
async def echo(session: CommandSession):
    await session.send(session.current_arg_text.strip())