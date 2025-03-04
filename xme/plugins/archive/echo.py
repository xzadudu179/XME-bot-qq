from nonebot import on_command, CommandSession
import config
from xme.xmetools.msgtools import send_session_msg

alias = ["e"]
__plugin_name__ = 'echo'
__plugin_usage__ = rf"""
指令 {__plugin_name__}
简介：重复消息
作用：重复参数文本
用法：
- {config.COMMAND_START[0]}{__plugin_name__} (要重复的内容)
权限/可用范围：无
别名：{', '.join(alias)}
""".strip()

@on_command(__plugin_name__, aliases=alias, only_to_me=False)
async def echo(session: CommandSession):
    await send_session_msg(session, session.current_arg_text.strip())