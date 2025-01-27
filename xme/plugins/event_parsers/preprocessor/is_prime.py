from nonebot import NoneBot
import aiocqhttp
from nonebot.plugin import PluginManager
from xme.xmetools.message_tools import event_send_msg
from xme.xmetools.text_tools import remove_punctuation, remove_suffix
from xme.xmetools import num_tools
from nonebot import message_preprocessor
from character import get_message

last_process = {}

@message_preprocessor
async def is_message_prime(bot: NoneBot, event: aiocqhttp.Event, plugin_manager: PluginManager):
    global last_process
    if event.user_id == event.self_id:
        return
    id = event.group_id if event.group_id else 00000 + event.user_id
    raw_msg = event.raw_message.strip()
    no_punc_msg = remove_punctuation(raw_msg)
    prime = ("质数", "素数")
    punc = ("呢", "呀", "哦", "哇", "诶", "耶", "唔", "啊", "阿")
    msgs_default = ("是不是prime", "是不是primepunc", "是否是prime", "是prime吗", "是prime嘛")
    msgs = [m.replace("prime", d).replace("punc", p) for d in prime for p in punc for m in msgs_default]
    # print(no_punc_msg, msgs, no_punc_msg.endswith(tuple(msgs)), remove_suffix(no_punc_msg, tuple(msgs)))
    if no_punc_msg.endswith(tuple(msgs)) and (x:=remove_suffix(no_punc_msg, tuple(msgs))).isdigit():
        if len(x) > 500:
            try:
                del last_process[id]
            except:
                pass
            return await event_send_msg(bot, event, get_message("event_parsers", "is_prime", "too_long"))
        try:
            is_prime = num_tools.is_prime(int(x))
        except OverflowError:
            try:
                del last_process[id]
            except:
                pass
            return await event_send_msg(bot, event, get_message("event_parsers", "is_prime", "too_long"))
    else:
        try:
            del last_process[id]
        except:
            pass
        return
    append = ""
    last = last_process.get(id, False)
    if last:
        if last["num"] == x:
            last_process[id] = {
                "to": event.user_id,
                "num": x,
                "is": is_prime
            }
            return
        if last["to"] == event.user_id and last['is'] == is_prime:
            append ="也"
    last_process[id] = {
        "to": event.user_id,
        "num": x,
        "is": is_prime
    }
    return await event_send_msg(bot, event, get_message("event_parsers", "is_prime", "is_prime" if is_prime else "not_prime", num=int(x), append=append))