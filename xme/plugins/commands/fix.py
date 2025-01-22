from nonebot import on_command, CommandSession, NoneBot, MessageSegment, message_preprocessor, Message
from nonebot.command import call_command
from nonebot.plugin import PluginManager
import aiocqhttp
import config
from xme.xmetools.doc_tools import CommandDoc, shell_like_usage
from xme.xmetools.json_tools import read_from_path
from xme.xmetools import command_tools
from xme.xmetools.message_tools import change_group_message_content, send_forward_msg, get_pure_text_message
from character import get_message
import xme.xmetools.text_tools as t
import asyncio
from zhipuai import ZhipuAI

# alias = ['f', '重输']
# __plugin_name__ = 'fix'
# __plugin_usage__ = str(CommandDoc(
#     name=__plugin_name__,
#     desc=get_message(__plugin_name__, 'desc'),
#     introduction=get_message(__plugin_name__, 'introduction'),
#     usage=f'',
#     permissions=[],
#     alias=alias
# ))

# @on_command(__plugin_name__, aliases=alias, only_to_me=False)
# async def _(session: CommandSession):
#     ...

# async def fix(bot, event):
#     ...

# @message_preprocessor
# async def get_command(bot: NoneBot, event: aiocqhttp.Event, plugin_manager: PluginManager):
#     raw_msg = "]".join(event.raw_message.split("]")[1:]).strip()
#     if not raw_msg[0] in config.COMMAND_START or not raw_msg[1:] or not raw_msg.replace(raw_msg[0], ""):
#         return
#     await command_tools.send_cmd(raw_msg)