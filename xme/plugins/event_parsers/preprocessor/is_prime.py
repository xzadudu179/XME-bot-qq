from nonebot import NoneBot
import asyncio
import aiocqhttp
from nonebot.plugin import PluginManager
from xme.xmetools.msgtools import send_event_msg
from xme.xmetools.texttools import remove_punctuation, remove_suffix, text_combinations
# from xme.xmetools import numtools
from nonebot import message_preprocessor
from character import get_message
import sympy

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
    msgs = text_combinations(("是不是{prime}", "是不是{prime}{punc}", "是否是{prime}", "是{prime}吗", "是{prime}嘛"), punc=punc, prime=prime)
    # print(no_punc_msg, msgs, no_punc_msg.endswith(tuple(msgs)), remove_suffix(no_punc_msg, tuple(msgs)))
    if no_punc_msg.endswith(tuple(msgs)) and (x:=remove_suffix(no_punc_msg, tuple(msgs))).isdecimal():
        if len(x) > 576:
            try:
                del last_process[id]
            except Exception:
                pass
            return await send_event_msg(bot, event, get_message("event_parsers", "is_prime", "too_long"))
        try:
            # BPSW 对 576 位是多项式时间（几十~几百 ms），但跑在事件循环上会短冻
            # 整个 bot 且可被连发叠加；放后台线程 + 墙钟兜底，超时按数字过长处理
            is_prime = await asyncio.wait_for(
                asyncio.to_thread(sympy.isprime, int(x)), 5)
        except (OverflowError, asyncio.TimeoutError):
            try:
                del last_process[id]
            except Exception:
                pass
            return await send_event_msg(bot, event, get_message("event_parsers", "is_prime", "too_long"))
    else:
        try:
            del last_process[id]
        except Exception:
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
    return await send_event_msg(bot, event, get_message("event_parsers", "is_prime", "is_prime" if is_prime else "not_prime", num=int(x), append=append))