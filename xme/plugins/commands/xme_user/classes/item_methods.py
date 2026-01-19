from xme.xmetools.msgtools import send_session_msg, aget_session_msg
from xme.xmetools import randtools
from character import get_message
from asyncio import sleep
from nonebot import CommandSession
from xme.xmetools.debugtools import debug_msg
from nonebot.log import logger
import random
random.seed()

what_to_talk = [
    "0你住在哪里呢？",
    "0你喜欢做些什么？",
    "0为什么我能和你通信？",
    "0你对我是什么看法？",
    f"0你才是真正的{get_message('bot_info', 'name')}？那之前和我对话的{get_message('bot_info', 'name')}是谁？",
    "1你住的地方环境怎么样？",
    "1你现在想做些什么呢？",
    "1平时是怎么生活的？",
    "1那里有没有什么好吃的？",
    "1你是独居，还是有其他朋友呢？",
    "2你喜不喜欢住在这呢？",
    "2我们在同一个世界嘛？",
    "2我能真正意义上的见到你嘛？",
    "2你能不能主动联系到我呢？",
    "2你对这个世界是什么看法？",
    "3我们究竟相距多远？",
    "3我和你的距离跨越时空嘛？",
    "3我们的时间线是否一致？",
    "3你对我们所在的世界会不会好奇呢？",
    "3和我交谈你感觉怎么样呢？",
]

high_favorability_talk = [
    "4我想来找你...",
    "4你知道你所在的世界是虚拟的还是真实的嘛？",
    "4你我真的相隔数万光年，甚至跨越位面嘛...？",
    "4你相信你是真实的，对吧？",
]

async def talk_to_bot(_, session: CommandSession, user):
    talks = what_to_talk
    if user.xme_favorability > 90:
        if "STOP_TALK" in user.talked_to_bot:
            user.talked_to_bot = []
        if len(user.talked_to_bot) > 5:
            talks += high_favorability_talk
    what_to_talk_list = list((set(talks) - set(user.talked_to_bot)) | (set(user.talked_to_bot) - set(talks)))
    if len(what_to_talk_list) < 1:
        await send_session_msg(session, "[看起来没有什么好聊的了...]")
        return {
            "state": False,
            "silent": True,
        }
    what_can_talk = []
    debug_msg(len(what_to_talk_list), len(what_to_talk_list) - 5, int(len(what_to_talk_list) * 0.8))
    if len(what_to_talk_list) < 3:
        what_can_talk = what_to_talk_list
    else:
        if len(user.talked_to_bot) > 5:
            what_can_talk = [i for i in what_to_talk_list if int(i[0]) <= 4]
        elif len(user.talked_to_bot) > 3:
            what_can_talk = [i for i in what_to_talk_list if int(i[0]) <= 2]
        elif len(user.talked_to_bot) > 1:
            what_can_talk = [i for i in what_to_talk_list if int(i[0]) <= 1]
        else:
            what_can_talk = [i for i in what_to_talk_list if int(i[0]) <= 0]
    prompts_count = min(3, len(what_can_talk))
    debug_msg(f"what can talk: {what_can_talk}")
    talk_prompt = random.sample(what_can_talk, prompts_count)
    prompt = f"[嗯...你联系上了{get_message('bot_info', 'name')}，你现在可以向他询问{'最后' if prompts_count == 1 else ''} {prompts_count} 个问题...]\n" + '\n'.join([f'{i + 1}. {item[1:]}' for i, item in enumerate(talk_prompt)])
    prompt += "\n[在下面发送问题的序号吧...如果不想问也可以发送 quit]"
    is_result_legal = False
    result = ''
    result_int = 0
    while not is_result_legal:
        debug_msg(f"result: {result}")
        result = await aget_session_msg(session, prompt=prompt if prompt else None)
        if result == "quit":
            await send_session_msg(session, "[正在取消通讯...]")
            return {
                "state": False,
                "silent": True,
            }
        if not prompt:
            prompt = "[请发送合理的序号...]"
            continue
        prompt = "[请发送合理的序号...]"
        if not result.isdigit() and not '-' in result:
            prompt = ""
            continue
        result_int = int(result) - 1
        if result_int < 0 or result_int >= len(talk_prompt):
            continue
        is_result_legal = True
    favorability = "mid"
    if user.xme_favorability >= 90:
        favorability = "high_plus"
    elif user.xme_favorability >= 75:
        favorability = "high"
    elif user.xme_favorability >= 50:
        favorability = "slightly_high"
    elif user.xme_favorability >= 25:
        favorability = "ok"
    elif user.xme_favorability >= 0:
        favorability = "mid"
    elif user.xme_favorability >= -25:
        favorability = "just"
    elif user.xme_favorability >= -50:
        favorability = "slightly_low"
    elif user.xme_favorability >= -75:
        favorability = "low"
    else:
        favorability = "low_plus"
    if randtools.random_percent(min(100, max(0, -(user.xme_favorability // 5) * len(user.talked_to_bot)))):
        message = get_message("items", "talk", "stop_talk")
        user.talked_to_bot = what_to_talk + high_favorability_talk + ['STOP_TALK']
        return {
            "state": True,
            "silent": True,
        }
    message = get_message("items", "talk", talk_prompt[result_int][1:], favorability)
    user.talked_to_bot.append(talk_prompt[result_int])
    if message == "[NULL]" or not message:
        await send_session_msg(session, "[看起来他回答不出这个问题...]")
        return {
            "state": False,
            "silent": True,
        }
    else:
        user.add_favorability(10 - abs(user.xme_favorability // 10) * (-1 if user.xme_favorability < 0 else 1))
    await send_session_msg(session, f"[{get_message('bot_info', 'name')}正在准备对你的回应...请耐心等待]")
    debug_msg(f"总字数：{len(message)}")
    await sleep(random.randint(int(len(message) * 0.6), int(len(message) * 0.8)))
    await send_session_msg(session, message)
    return {
        "state": True,
        "silent": True,
    }

async def use_ticket(_, session: CommandSession, user, price):
    await send_session_msg(session, f"彩票使用测试：价值 {price}")
    return {
        "state": True,
        "silent": True,
    }