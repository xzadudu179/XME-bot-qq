import nonebot
import config
import requests
import json
from aiocqhttp.exceptions import Error as CQHttpError
from datetime import datetime
from nonebot import log
from xme.xmetools.bottools import bot_call_action
from xme.xmetools import randtools
from xme.xmetools.jsontools import read_from_path
from xme.xmetools import timetools
from xme.xmetools import msgtools
from character import get_character_item, get_message
import random
bot = nonebot.get_bot()

async def send_time_message():
    scheduler_groups = read_from_path(config.BOT_SETTINGS_PATH).get("schtime_groups", [])
    for group in scheduler_groups:
        say = random.choice(read_from_path("./static/hitokoto.json"))
        # try:
        #     say = json.loads(requests.get('https://v1.hitokoto.cn/').text)
        # except json.JSONDecodeError:
        #     say = {
        #         "hitokoto": get_message("schedulers", "hitokoto_error"),
        #         "from_who": get_message("bot_info", "name"),
        #         "from": "XME_bot"
        #     }
        anno = read_from_path(config.BOT_SETTINGS_PATH).get("announcement", "").strip()
        latest = read_from_path(config.BOT_SETTINGS_PATH).get("latest_update", "")
        latest_prefix = "\n最近更新：\n"
        if len(latest) <= 0:
            latest = ""
        elif isinstance(latest, list):
            latest = latest_prefix + "\n".join([f"{i + 1}. {content}" for i, content in enumerate(latest)])
        anno_message = get_message("config", "anno_message", anno=("[九九的公告] " + anno + "\n") if anno != "" else "")
        if not anno_message:
            anno_message = ''
        something_to_say = get_message("schedulers", "time",
            period=timetools.get_time_period(),
            hitokoto=say['hitokoto'],
            by=say['author'] if say['author'] else '无名',
            from_where=say['source'] if say['source'] else "未知",
            anno=anno_message,
            update=latest,
            tips=get_message("bot_info", "tips")
        )
        try:
            await bot.send_group_msg(group_id=group,
                                message=f'{something_to_say}')
        except CQHttpError:
            log.logger.error(f"定时器在 {group} 发消息失败")
            pass

@nonebot.scheduler.scheduled_job(
    'cron',
    year="*",
)
async def _():
    print("新年报时")
    await msgtools.send_to_groups(bot, get_message("schedulers", "new_year"))

@nonebot.scheduler.scheduled_job('cron', second='*', max_instances=3)
async def _():
    if not (6 <= datetime.now().hour <= 24): return
    if not randtools.random_percent(0.03): return
    groups = await bot.get_group_list()
    # 群组太少就降低概率
    if not randtools.random_percent(min(100, 50 + len(groups) * 10)): return
    group = random.choice(groups)
    group_id = group['group_id']
    has_faces = True
    try:
        faces = await bot_call_action(bot, "fetch_custom_face")
    except:
        has_faces = False
    # print(faces)
    # 随机发表情
    messages = get_character_item("schedulers", "idles")
    if has_faces:
        messages += faces
    message = random.choice(messages)
    # print(has_faces, messages)
    if message in faces:
        message = f"[CQ:image,file={message}]"
    log.logger.info(f"发一条随机消息 \"{message}\" 给 {group['group_name']} ({group_id})")
    try:
        await bot.send_group_msg(group_id=group_id,
                            message=message)
    except CQHttpError:
        log.logger.error(f"定时器在 {group['group_name']} ({group_id}) 发消息失败")
        pass




@nonebot.scheduler.scheduled_job('cron', hour='12')
async def _():
    print("报时")
    await send_time_message()

# @nonebot.scheduler.scheduled_job('cron', minute='*')
# async def _():
#     print("测试报时")
#     await send_time_message()

@nonebot.scheduler.scheduled_job('cron', hour='8')
async def _():
    print("报时")
    await send_time_message()

@nonebot.scheduler.scheduled_job('cron', hour='20')
async def _():
    print("报时")
    await send_time_message()

@nonebot.scheduler.scheduled_job('cron', hour='0')
async def _():
    print("报时")
    await send_time_message()