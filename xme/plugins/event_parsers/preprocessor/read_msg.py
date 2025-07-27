from nonebot import NoneBot
from nonebot.plugin import PluginManager
from nonebot import message_preprocessor
from xme.xmetools.bottools import bot_call_action
import aiocqhttp

@message_preprocessor
async def read_msg(bot: NoneBot, event: aiocqhttp.Event, plugin_manager: PluginManager):
    try:
        if event.group_id is None:
            print("私聊消息不读")
            return
        await bot_call_action(bot, "mark_msg_as_read", message_id=event.message_id)
        # print("已读")
    except Exception as ex:
        print(f"读消息出现错误: {ex}")
