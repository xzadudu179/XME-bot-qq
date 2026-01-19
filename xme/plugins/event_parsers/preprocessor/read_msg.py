from nonebot import NoneBot
from nonebot.plugin import PluginManager
from nonebot import message_preprocessor
from xme.xmetools.bottools import bot_call_action
import aiocqhttp
from xme.xmetools.debugtools import debug_msg
from nonebot.log import logger

@message_preprocessor
async def read_msg(bot: NoneBot, event: aiocqhttp.Event, plugin_manager: PluginManager):
    try:
        if event.group_id is None:
            debug_msg("私聊消息不读")
            return
        await bot_call_action(bot, "mark_msg_as_read", message_id=event.message_id)
        # debug_msg("已读")
    except Exception as ex:
        logger.error(f"读消息出现错误:")
        logger.exception(ex)
