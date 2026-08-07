from nonebot import NoneBot
from nonebot.plugin import PluginManager
from nonebot import message_preprocessor
from xme.xmetools.msgtools import send_event_msg, get_message
import aiocqhttp
from xme.xmetools.dicttools import get_value
import time
from xme.xmetools.texttools import remove_punctuation, is_repeated_substring
from nonebot.log import logger

called_deon = {
    # 成员: {
    #    count: 次数,
    #    last_time: time,
    #    annoying_index: 0,
    #    last_down_time: 0,
    #}
}

@message_preprocessor
async def call_deon(bot: NoneBot, event: aiocqhttp.Event, plugin_manager: PluginManager):
    character_name = get_message("bot_info", "name")
    msg = remove_punctuation(str(event.raw_message))
    last_time = get_value(event.user_id, "last_time", default=0, search_dict=called_deon)
    mute = get_value(event.user_id, "mute", default=False, search_dict=called_deon)
    annoying_index = get_value(event.user_id, "annoying_index", default=0, search_dict=called_deon)
    last_down_time = get_value(event.user_id, "last_down_time", default=0, search_dict=called_deon)
    time_interval = time.time() - last_time
    if annoying_index <= 0:
        mute = False

    down_time_interval = time.time() - (last_time if last_down_time == 0 else last_down_time)
    if down_time_interval > 30:
        annoying_index -= 15 * down_time_interval / 30
        annoying_index = max(annoying_index, 0)
        last_down_time = time.time()

    if msg.split(" ")[-1] not in [character_name, f"{character_name}在嘛", f"{character_name}在吗", f"{character_name}呢"] and not is_repeated_substring(msg, character_name):
        if mute:
            called_deon[event.user_id] = {
                # "count": count,
                "last_time": last_time,
                "last_down_time": last_down_time,
                "annoying_index": annoying_index,
                "mute": mute,
            }
        if last_time > 0 and time.time() -  (last_time if last_down_time == 0 else last_down_time) > 500:
            logger.info(f"删除呼叫{character_name}缓存")
            del called_deon[event.user_id]
        return

    # called_deon[]
    # count = get_value(event.user_id, "count", default=0)

    if time_interval < 7:
        append_mul = 3
    else:
        append_mul = min(15 / time_interval, 10)
    annoying_index += 5 * append_mul + 0.15 * annoying_index
    if annoying_index <= 0:
        annoying_index = 0
        mute = False
    if annoying_index > 100:
        annoying_index = 100
    if not mute:
        if annoying_index >= 100:
            await send_event_msg(bot, event, get_message("config", "call_response_too_many"))
            mute = True
        elif annoying_index > 80:
            await send_event_msg(bot, event, get_message("config", "call_response_many_4"))
        elif annoying_index > 60:
            await send_event_msg(bot, event, get_message("config", "call_response_many_3"))
        elif annoying_index > 40:
            await send_event_msg(bot, event, get_message("config", "call_response_many_2"))
        elif annoying_index > 20:
            await send_event_msg(bot, event, get_message("config", "call_response_many_1"))
        else:
            await send_event_msg(bot, event, get_message("config", "call_response"))
    called_deon[event.user_id] = {
        # "count": count,
        "last_time": time.time(),
        "last_down_time": last_down_time,
        "annoying_index": annoying_index,
        "mute": mute,
    }
    logger.info(called_deon[event.user_id])

