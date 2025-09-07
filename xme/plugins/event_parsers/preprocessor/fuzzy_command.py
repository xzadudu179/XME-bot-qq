from nonebot import NoneBot
import aiocqhttp
from nonebot.plugin import PluginManager
from xme.xmetools.texttools import fuzzy_search, is_valid_english_word
from xme.xmetools.cmdtools import get_cmds_alias_strings, event_send_cmd, get_cmds
from xme.xmetools.msgtools import send_event_msg
from nonebot import message_preprocessor
from character import get_message
import config
from nonebot.message import CanceledException

receiving = False
last_cmd = ""


@message_preprocessor
async def is_it_command(bot: NoneBot, event: aiocqhttp.Event, plugin_manager: PluginManager):
    global receiving
    global last_cmd
    raw_msg = event.raw_message.strip()
    if not raw_msg:
        return
    # 排除 at 漠月的情况
    if raw_msg.startswith(f"[CQ:at,qq={event.self_id}"):
        raw_msg = ("]".join(raw_msg.split("]")[1:])).strip()
    if receiving and raw_msg == "y":
        await event_send_cmd(last_cmd, bot, event)
        receiving = False
        last_cmd = ""
        raise CanceledException(f"消息已被作为指令")
    cmds = get_cmds_alias_strings()
    # print(raw_msg)
    # 没加指令开头字符的指令？
    if raw_msg in cmds and len(raw_msg) > 2 and (not is_valid_english_word(raw_msg.split(" ")[0]) or raw_msg.split(" ")[0] in ['wife', 'pick', 'lot']):
        print("没加指令开头")
        last_cmd = f"/{raw_msg}"
        receiving = True
        await send_event_msg(bot, event, get_message("config", "fuzzy_cmd", new_cmd=last_cmd))
        return
    if not raw_msg[0] in config.COMMAND_START or not raw_msg[1:] or not raw_msg.replace(raw_msg[0], ""):
        # print("不算指令")
        return
    cmd_msg = raw_msg[1:].split(" ")[0].strip()
    args = " ".join(raw_msg[1:].split(" ")[1:])
    # print(cmds)
    search_cmd = fuzzy_search(cmd_msg, cmds, 0.7)
    if search_cmd is None or cmd_msg == search_cmd:
        print("无法搜索到或者是没错", search_cmd, cmd_msg)
        return
    last_cmd = f"/{search_cmd} {args}"
    await send_event_msg(bot, event, get_message("config", "fuzzy_cmd", new_cmd=last_cmd))
    receiving = True

