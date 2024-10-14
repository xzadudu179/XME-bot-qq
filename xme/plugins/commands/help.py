import nonebot
import config
from xme.xmetools.doc_gen import CommandDoc
from nonebot import on_command, CommandSession

alias = ["xme帮助", "usage", "xmehelp", "docs", "帮助"]
__plugin_name__ = 'help'

__plugin_usage__ = str(CommandDoc(
    name=__plugin_name__,
    desc='显示帮助',
    introduction='显示帮助，或某个指令的帮助',
    usage=f'<功能名>',
    permissions=[],
    alias=alias
))

@on_command(__plugin_name__, aliases=alias, only_to_me=False)
async def _(session: CommandSession):
    plugins = list(filter(lambda p: p.name, nonebot.get_loaded_plugins()))
    arg = session.current_arg_text.strip().lower()
    # 如果发了参数则发送相应命令的使用帮助
    print("发送帮助")
    if arg:
        for p in plugins:
            if p.name.lower() != arg: continue
            return await session.send(p.usage if p.usage else "无内容")
    help_list_str = ""
    if config.DEBUG:
        for p in plugins:
            try:
                help_list_str += "\n- " + f"{p.name}\t" + p.usage.split('简介：')[1].split('\n')[0].strip()
            except:
                help_list_str += "\n- " + f"{p.name}\t"
    await session.send(f'[XME-bot V0.1.0]\n指令开头字符: {" ".join(config.COMMAND_START)} 中任选\n' + "XME-Bot 现在有以下功能哦：" + help_list_str + f"\nXME-Bot 机器人帮助文档: http://docs.xme.179.life/#/help\n可以使用 {config.COMMAND_START[0]}help 功能名 查看某功能的详细介绍哦")
