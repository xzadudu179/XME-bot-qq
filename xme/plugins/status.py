from nonebot import on_command, CommandSession
from ..xmetools import cur_system as st
import config

alias = ['系统状态', 'stats']
__plugin_name__ = 'status'
__plugin_usage__ = rf"""
指令 {__plugin_name__}
简介：查看系统状态
作用：查看 bot 运行设备的系统状态
用法：
- {config.COMMAND_START[0]}{__plugin_name__}
权限/可用范围：无
别名：{', '.join(alias)}
""".strip()

@on_command(__plugin_name__, aliases=alias, only_to_me=False)
async def _(session: CommandSession):
    message = ""
    try:
        message = st.system_info()
    except:
        message = "当前运行设备暂不支持展示系统状态——"
    await session.send(message)