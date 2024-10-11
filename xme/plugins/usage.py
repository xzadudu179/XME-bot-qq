import nonebot
from nonebot import on_command, CommandSession
"""
没什么用 写个文档后就扔了
"""

__plugin_name__ = '/usage'
__plugin_usage__ = r"""
查看帮助

usage
""".strip()

@on_command('usage', aliases=['xme帮助', 'help', 'xmehelp', 'man'], only_to_me=False)
async def _(session: CommandSession):
    # 获取设置了名称的插件列表
    plugins = list(filter(lambda p: p.name, nonebot.get_loaded_plugins()))

    arg = session.current_arg_text.strip().lower()
    if not arg:
        # 如果用户没有发送参数，则发送功能列表
        await session.send(
            'XME-bot 现在有以下功能哦：\n\n' + '\n'.join(p.name for p in plugins))
        return

    # 如果发了参数则发送相应命令的使用帮助
    for p in plugins:
        if p.name.lower() == arg:
            await session.send(p.usage)