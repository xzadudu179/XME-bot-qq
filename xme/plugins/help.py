import nonebot
import config
from nonebot import on_command, CommandSession

alias = ["xme帮助", "usage", "xmehelp", "docs", "帮助"]
__plugin_name__ = 'help'
__plugin_usage__ = rf"""
指令 {__plugin_name__}
简介：显示帮助
作用：显示帮助，或某个指令的帮助
用法：
- {config.COMMAND_START[0]}{__plugin_name__} <指令名>
权限/可用范围：无
别名：{', '.join(alias)}
""".strip()


@on_command(__plugin_name__, aliases=alias, only_to_me=False)
async def _(session: CommandSession):
    plugins = list(filter(lambda p: p.name, nonebot.get_loaded_plugins()))
    arg = session.current_arg_text.strip().lower()
    # 如果发了参数则发送相应命令的使用帮助
    if not arg:
        print("发送帮助")
        help_list_str = ""

        for p in plugins:
            try:
                help_list_str += "\n- " + f"{p.name}\t" + p.usage.split('简介：')[1].split('\n')[0].strip()
            except:
                pass
        await session.send(f'[XME-bot V0.1.0]\n指令开头字符: {" ".join(config.COMMAND_START)} 中任选\n' + "XME-Bot 现在有以下功能哦：" + help_list_str + f"\nXME-Bot 机器人帮助文档: http://docs.xme.179.life/#/help\n可以使用 {config.COMMAND_START[0]}help 指令名 查看某指令的使用方法哦")
    for p in plugins:
        if p.name.lower() == arg:
            await session.send(p.usage)