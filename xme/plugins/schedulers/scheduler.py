import nonebot
import config
import requests
import json
from aiocqhttp.exceptions import Error as CQHttpError
from datetime import datetime
from nonebot import log
from xme.xmetools import random_tools
from xme.xmetools import time_tools
from character import get_item, get_message
import random
bot = nonebot.get_bot()

async def send_time_message():
    for group in config.SCHEDULER_GROUP:
        say = json.loads(requests.get('https://v1.hitokoto.cn/').text)
        something_to_say = get_message("schedulers", "time",
            period=time_tools.get_time_period(),
            hitokoto=say['hitokoto'],
            by=say['from_who'] if say['from_who'] else '无名',
            from_where=say['from']
        )
        # something_to_say = f"{date_tools.get_time_period()}好呀~\n\n\"{say['hitokoto']}\"\n——{'无名' if not (x:=say['from_who']) else x} 《{say['from']}》"
        try:
            await bot.send_group_msg(group_id=group,
                                message=f'{something_to_say}')
        except CQHttpError:
            log.logger.error(f"定时器在 {group} 发消息失败")
            pass


@nonebot.scheduler.scheduled_job('cron', second='*', max_instances=3)
async def _():
    if not (6 <= datetime.now().hour <= 24): return
    if not random_tools.random_percent(0.03): return
    groups = await bot.get_group_list()
    # 群组太少就降低概率
    if not random_tools.random_percent(min(100, 50 + len(groups) * 10)): return
    group = random.choice(groups)
    group_id = group['group_id']
    # idles = get_message("schedulers", "idles")
    # idles = json_tools.read_from_path("bot_messages.json")['idles']
    has_faces = True
    try:
        faces = await bot.api.call_action("fetch_custom_face")
    except:
        has_faces = False
    # print(faces)
    # 随机发表情
    messages = get_item("schedulers", "idles")
    if has_faces:
        messages.append(faces)
    message = random.choice(messages)
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
    print("send")
    await send_time_message()

@nonebot.scheduler.scheduled_job('cron', hour='8')
async def _():
    print("send")
    await send_time_message()

@nonebot.scheduler.scheduled_job('cron', hour='20')
async def _():
    print("send")
    await send_time_message()

@nonebot.scheduler.scheduled_job('cron', hour='0')
async def _():
    print("send")
    await send_time_message()