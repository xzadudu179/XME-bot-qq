from nonebot import NoneBot
from nonebot.plugin import PluginManager
from nonebot import message_preprocessor
from xme.xmetools.cmdtools import is_it_command
from xme.xmetools.bottools import bot_call_action
import aiocqhttp

@message_preprocessor
async def use_check(bot: NoneBot, event: aiocqhttp.Event, plugin_manager: PluginManager):
    if event.group_id is None:
        return
    # 登记指令上一次在群里的调用时间
    if not is_it_command(event.raw_message):
        return
    