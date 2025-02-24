from nonebot import NoneBot
from nonebot.plugin import PluginManager
from nonebot.message import CanceledException
from nonebot import message_preprocessor
from character import get_message
import aiocqhttp
from xme.xmetools.message_tools import send_to_superusers
from xme.xmetools.bot_control import get_stranger_name
import config

@message_preprocessor
async def private_message_copy(bot: NoneBot, event: aiocqhttp.Event, plugin_manager: PluginManager):
    if event.group_id:
        # 不处理群聊消息
        return
    if event.user_id in config.SUPERUSERS:
        # 不处理 SUPERUSERS 消息
        return
    await send_to_superusers(bot, get_message("event_parsers", "private_message_copy_prefix", msg=event.raw_message, sender=f'{await get_stranger_name(event.user_id)}({event.user_id})'))