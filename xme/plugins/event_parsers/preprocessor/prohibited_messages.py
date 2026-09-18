from nonebot import NoneBot
from nonebot.plugin import PluginManager
from nonebot.message import CanceledException
from nonebot import message_preprocessor
from xme.xmetools.bottools import get_settings
# from character import get_message
import aiocqhttp
# from xme.xmetools import jsontools
# import config
# import asyncio
@message_preprocessor
async def _(bot: NoneBot, event: aiocqhttp.Event, plugin_manager: PluginManager):
    # message = event.raw_message.strip()
    # prohibited_list = jsontools.read_from_path('./prohibited.json')['whitelist_prohibited']
    is_prohibited = False
    if event.user_id == event.self_id:
        return
    # 这是一般性违禁词
    blacklist = (await get_settings()).get("blacklist_users") or []
    if str(event.user_id) in blacklist:
        raise CanceledException(f"消息 \"{event.raw_message}\" 为黑名单用户发送")
    if is_prohibited:
        raise CanceledException(f"消息 \"{event.raw_message}\" 包含违禁词")
    return
