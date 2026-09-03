from nonebot import NoneBot
import aiocqhttp
from nonebot.log import logger
from nonebot.plugin import PluginManager
from xme.xmetools.cmdtools import get_cmd_by_alias
from xme.xmetools.msgtools import send_event_msg, event_is_text_can_send
from nonebot import message_preprocessor
from character import get_message, get_character_item
import random
random.seed()

groups_messages = {

}

sending_msgs = {}

sent_msgs = {}

@message_preprocessor
async def is_it_command(bot: NoneBot, event: aiocqhttp.Event, plugin_manager: PluginManager):
    global sending_msgs
    global groups_messages
    raw_msg = event.raw_message
    if event.group_id is None:
        return
    s = sent_msgs.get(event.group_id, None)
    if s is None:
        sent_msgs[event.group_id] = []
    if not groups_messages.get(event.group_id, []):
        groups_messages[event.group_id] = []
    groups_messages[event.group_id].append(
        {
            "sender": event.user_id,
            "raw_msg": raw_msg,
        }
    )
    msgs = groups_messages[event.group_id]
    if len(msgs) < 2:
        return
    # print(groups_messages)
    logger.debug(f"sent {sent_msgs}")
    send = False
    sent = False
    break_chain = False
    chain_msg = ''
    chain_msg = msgs[0]["raw_msg"]
    needed_length = 3
    if sending_msgs.get(chain_msg, False):
        sent = True
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
            del groups_messages[event.group_id][i - 1]
            return
        if m["raw_msg"] != chain_msg:
            # print("接龙中断")
            groups_messages[event.group_id] = [m]
            return
        if i + 1 >= needed_length:
            send = True
    # del groups_messages[event.group_id]
    # if get_cmd_by_alias(chain_msg, True):
    #     print("忽略指令")
    #     return
    logger.debug(sending_msgs)
    # NOTE：当前架构（nonebot1）似乎对于部分 onebot 实现（napcat/snowluma）不兼容“上报自身消息”，bot无法得到自身消息，所以永远不会出现打断。
    if send and break_chain and not sending_msgs.get(chain_msg, False):
        logger.info(f"打断 \"{chain_msg}\"")
        sending_msgs[chain_msg] = True
        await send_event_msg(bot, event, random.choice([i for i in get_character_item("event_parsers", "break_chain") if i != chain_msg]), False)
    elif send and not sent and not sending_msgs.get(chain_msg, False):
        if chain_msg in sent_msgs[event.group_id]:
            return
        can_send = (await event_is_text_can_send(bot, event, chain_msg))["result"]
        if not can_send:
            return
        sending_msgs[chain_msg] = True
        logger.info(f"接龙 \"{chain_msg}\"")
        await send_event_msg(bot, event, chain_msg, False)
        sent_msgs[event.group_id].append(chain_msg)
    if sending_msgs.get(chain_msg, False):
        del sending_msgs[chain_msg]
