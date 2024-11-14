from nonebot.session import BaseSession
from nonebot import NoneBot
import time
import config
# import asyncio
last_messages = {
    "refresh_time": 0
}

async def anti_bursts_handler(session: BaseSession, bot: NoneBot):
    global last_messages
    # recalls = json_tools.read_from_path('./recalls.json')['recalls']
    THRESHOLD = 4
    SEC_THRESHOLD = 0.9
    key = f"{session['user_id']}{session['group_id']}"
    if session['group_id'] not in config.GROUPS_WHITELIST or session['user_id'] == session.self_id:
        return
    message = session['raw_message'].strip()
    if time.time() - last_messages['refresh_time'] > (SEC_THRESHOLD * THRESHOLD) and last_messages['refresh_time'] > 0:
        print(f"清除缓存")
        last_messages = {
            "refresh_time": time.time()
        }
    elif last_messages['refresh_time'] <= 0:
        last_messages['refresh_time'] = time.time()
    last_messages.setdefault(key, {}).setdefault(message, {})
    last_messages[key][message].setdefault("count", 0)
    if not last_messages[key][message].get("start_time", False):
        # print(f"记录新语句: {message}")
        last_messages[key][message]["start_time"] = time.time()
    last_messages[key][message]['count'] += 1
    # print(last_messages)

    if last_messages[key][message]['count'] >= THRESHOLD:
        # 刷屏了 禁言
        print(f"消息 \"{message}\" 刷屏了，禁言")
        if time.time() - last_messages[key][message]["start_time"] < (SEC_THRESHOLD * THRESHOLD):
            await bot.api.set_group_ban(group_id=session['group_id'], user_id=session['user_id'], duration=120)
            await bot.send_group_msg(message="不要刷屏 uwu", group_id=session['group_id'])
        # try:
        #     del last_messages[session['user_id']][message]
        # except:
        #     print("删除消息失败，跳过")
        #     pass
    return