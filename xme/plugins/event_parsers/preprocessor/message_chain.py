from nonebot import NoneBot
import aiocqhttp
from nonebot.plugin import PluginManager
from xme.xmetools.command_tools import get_cmd_by_alias
from xme.xmetools.message_tools import event_send_msg
from nonebot import message_preprocessor
from character import get_message, get_item
import random

groups_messages = {

}

@message_preprocessor
async def is_it_command(bot: NoneBot, event: aiocqhttp.Event, plugin_manager: PluginManager):
    raw_msg = event.raw_message
    if event.group_id is None:
        return
    if not groups_messages.get(event.group_id, []):
        groups_messages[event.group_id] = []
    groups_messages[event.group_id].append(
        {
            "sender": event.user_id,
            "raw_msg": raw_msg
        }
    )
    msgs = groups_messages[event.group_id]
    if len(msgs) < 2:
        return
    # print(groups_messages)
    send = False
    sent = False
    break_chain = False
    chain_msg = ''
    chain_msg = msgs[0]["raw_msg"]
    needed_length = 3
    for i, m in enumerate(msgs):
        if m["sender"] == event.self_id and i == 0:
            break_chain = True
        if m["sender"] == event.self_id:
            # print("接过龙了")
            sent = True
        if i == 0: continue
        # print(m["raw_msg"], chain_msg)
        if i > 0 and msgs[i]["sender"] == msgs[i - 1]["sender"] and msgs[i]["raw_msg"] == msgs[i - 1]["raw_msg"]:
            # print("不是接龙")
            del groups_messages[event.group_id]
            return
        if m["raw_msg"] != chain_msg:
            # print("接龙中断")
            groups_messages[event.group_id] = [m]
            return
        if i + 1 >= needed_length:
            send = True
    # del groups_messages[event.group_id]
    if get_cmd_by_alias(chain_msg, True):
        print("忽略指令")
        return
    if break_chain:
        print(f"打断 \"{chain_msg}\"")
        return await event_send_msg(bot, event, random.choice([i for i in get_item("event_parsers", "break_chain") if i != chain_msg]), False)
    if send and not sent:
        print(f"接龙 \"{chain_msg}\"")
        return await event_send_msg(bot, event, chain_msg, False)
