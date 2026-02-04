from nonebot import NoneBot
import aiocqhttp
from nonebot.plugin import PluginManager
# from xme.xmetools import cmdtools
# from xme.xmetools.msgtools import send_event_msg
from nonebot import message_preprocessor
# from character import get_message
import config

@message_preprocessor
async def is_it_command(bot: NoneBot, event: aiocqhttp.Event, plugin_manager: PluginManager):
    # print("111")
    # print(event)
    raw_msg = event.raw_message
    # if raw_msg[0] not in config.COMMAND_START or not raw_msg[1:] or not raw_msg.replace(raw_msg[0], ""):
    if not raw_msg.startswith(config.COMMAND_START[0]) or not raw_msg[1:] or not raw_msg.replace(raw_msg[0], ""):
        return

    # if not command_tools.get_cmd_by_alias(raw_msg.split(" ")[0]):
    #     # await bot.send(event, get_message("event_parsers", "no_command", command=raw_msg[1:].split(" ")[0], help_cmd=config.COMMAND_START[0] + "help"))
    #     await event_send_msg(bot, event, get_message("event_parsers", "no_command", command=raw_msg[1:].split(" ")[0], help_cmd=config.COMMAND_START[0] + "help"))