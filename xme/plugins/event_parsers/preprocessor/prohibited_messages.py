from nonebot import NoneBot
from nonebot.plugin import PluginManager
from nonebot.message import CanceledException
from nonebot import message_preprocessor
# from character import get_message
import aiocqhttp
# from xme.xmetools import jsontools
# import config
# import asyncio
@message_preprocessor
async def recall_handler(bot: NoneBot, event: aiocqhttp.Event, plugin_manager: PluginManager):
    # message = event.raw_message.strip()
    # prohibited_list = jsontools.read_from_path('./prohibited.json')['whitelist_prohibited']
    is_prohibited = False
    if event.user_id == event.self_id:
        return
    # 这是一般性违禁词

    # 这是抽象词屏蔽
    # if event.group_id not in config.GROUPS_WHITELIST:
    #     return
    # for prohibited in prohibited_list:
    #     if type(prohibited) == list:
    #         if message not in prohibited: continue
    #     elif prohibited not in message: continue
    #     print(f"{event.raw_message} 是/有不该出现的词汇: {prohibited}")
    #     # asyncio.sleep(0.5)
    #     await bot.api.delete_msg(message_id=event.message_id)
    #     await bot.send_group_msg(message=f"[CQ:at,qq={event.user_id}] " + get_message("event_parsers", "message_prohibited"), group_id=event.group_id)
    #     # await bot.send_group_msg(message="不要发奇怪的词汇 uwu", group_id=event.group_id)
    #     is_prohibited = True
    #     break
    if is_prohibited:
        raise CanceledException(f"消息 \"{event.raw_message}\" 包含违禁词")
    return
