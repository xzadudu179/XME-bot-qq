from nonebot import NoneBot
import aiocqhttp
from nonebot.plugin import PluginManager
# from xme.xmetools import cmdtools
# from xme.xmetools.msgtools import send_event_msg
from nonebot import message_preprocessor
# from character import get_message
import config

@message_preprocessor
async def _(bot: NoneBot, event: aiocqhttp.Event, plugin_manager: PluginManager):
    # print("111")
    # print(event)
    raw_msg = event.raw_message
    if raw_msg.startswith("//except") and event.user_id in config.SUPERUSERS:
        msg = " ".join(raw_msg.split(" ")[1:]) if len(raw_msg.split(" ")) > 1 else ""
        raise ValueError(msg)
    return