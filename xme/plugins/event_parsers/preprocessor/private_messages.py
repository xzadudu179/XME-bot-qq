from nonebot import NoneBot
from nonebot.plugin import PluginManager
from xme.xmetools import command_tools
from nonebot import message_preprocessor
from character import get_message
import aiocqhttp
from xme.xmetools.message_tools import send_to_superusers
from xme.xmetools.bot_control import get_stranger_name, get_group_name
import config

@message_preprocessor
async def private_message_copy(bot: NoneBot, event: aiocqhttp.Event, plugin_manager: PluginManager):
    raw_msg = event.raw_message
    if event.user_id == event.self_id:
        return
    if event.user_id in config.SUPERUSERS:
        # 不处理 SUPERUSERS 消息
        return
    if "[CQ:at,qq=" in raw_msg and raw_msg.split("[CQ:at,qq=")[1].split(",")[0] == str(event.self_id):
        return await send_to_superusers(bot, get_message("event_parsers", "private_message_copy_prefix", msg=event.raw_message, sender=f"[{await get_group_name(event.group_id)}] {await get_stranger_name(event.user_id)}({event.user_id})"))
    if event.group_id:
        return
    if not command_tools.get_cmd_by_alias(raw_msg.split(" ")[0]):
        await send_to_superusers(bot, get_message("event_parsers", "private_message_copy_prefix", msg=event.raw_message, sender=f'{await get_stranger_name(event.user_id)}({event.user_id})'))
        return
    print("被私聊发送了指令")