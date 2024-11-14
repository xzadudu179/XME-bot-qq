from nonebot import NoneBot
from nonebot.plugin import PluginManager
from nonebot.message import CanceledException
from nonebot import message_preprocessor
import aiocqhttp
from xme.xmetools import json_tools
import config
# import asyncio
@message_preprocessor
async def recall_handler(bot: NoneBot, event: aiocqhttp.Event, plugin_manager: PluginManager):
    recalls = json_tools.read_from_path('./recalls.json')['recalls']
    is_prohibited = False
    if event.user_id == event.self_id:
        return
    # 这是一般性违禁词

    # 这是抽象词屏蔽
    if event.group_id not in config.GROUPS_WHITELIST:
        return
    for recall in recalls:
        if type(recall) == list:
            if event.raw_message.strip() not in recall: continue
        elif recall not in event.raw_message.strip(): continue
        print(f"{event.raw_message} 是/有不该出现的词汇: {recall}")
        # asyncio.sleep(0.5)
        await bot.api.delete_msg(message_id=event.message_id)
        await bot.send_group_msg(message="不要发奇怪的词汇 uwu", group_id=event.group_id)
        is_prohibited = True
        break
    if is_prohibited:
        raise CanceledException(f"消息 \"{event.raw_message}\" 包含违禁词")
    return