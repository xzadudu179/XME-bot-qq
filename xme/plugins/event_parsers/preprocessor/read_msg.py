from nonebot import NoneBot
from nonebot.plugin import PluginManager
from nonebot import message_preprocessor
import aiocqhttp

@message_preprocessor
async def read_msg(bot: NoneBot, event: aiocqhttp.Event, plugin_manager: PluginManager):
    try:
        await bot.api.call_action("mark_msg_as_read", message_id=event.message_id)
        # print("已读")
    except Exception as ex:
        print(f"读消息出现错误: {ex}")
