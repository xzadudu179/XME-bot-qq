from nonebot import NoneBot
import aiocqhttp
from nonebot.message import CanceledException
from nonebot.plugin import PluginManager
from xme.xmetools import cmdtools
from xme.xmetools.msgtools import send_event_msg
from nonebot import message_preprocessor
from xme.plugins.commands.drift_bottle.seek import seeking_players
from character import get_message
# import config

@message_preprocessor
async def _(bot: NoneBot, event: aiocqhttp.Event, plugin_manager: PluginManager):
    if not cmdtools.is_command(event.raw_message):
        return
    global seeking_players
    if seeking_players.get(event.user_id) is not None:
        await send_event_msg(bot, event, get_message("config", "task_prevent_cmd"))
        raise CanceledException(f"用户 {event.user_id} 正在寻宝，不能用指令。")
