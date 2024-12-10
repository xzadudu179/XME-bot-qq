from nonebot import NoneBot
from nonebot.plugin import PluginManager
from nonebot.message import CanceledException
from nonebot import message_preprocessor
from xme.xmetools.command_tools import get_cmd_by_alias
from xme.xmetools import json_tools
from xme.xmetools import time_tools
import aiocqhttp

def save_usage(cmd_usage: dict, name):
    usage: dict = json_tools.read_from_path("./data/usage_stats.json")['usages']
    usage[name] = cmd_usage
    json_tools.save_to_path("./data/usage_stats.json", {"usages": usage})

@message_preprocessor
async def recall_handler(bot: NoneBot, event: aiocqhttp.Event, plugin_manager: PluginManager):
    raw_msg = event.raw_message.strip()
    if not raw_msg:
        return
    if (cmd:=get_cmd_by_alias(raw_msg)) == False: return
    usage: dict = json_tools.read_from_path("./data/usage_stats.json")['usages']
    cmd_name = cmd.name[0]
    cmd_usage: dict = usage.get(cmd_name, {
        "calls": [],
    })
    cmd_usage['calls'].append({
        "hour": time_tools.get_curr_hour(),
        "by": event.user_id
    })
    save_usage(cmd_usage, cmd_name)
