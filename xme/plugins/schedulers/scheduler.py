import nonebot
import config
import requests
import json
from aiocqhttp.exceptions import Error as CQHttpError
from datetime import datetime
from nonebot import log
from xme.xmetools import random_tools
from xme.xmetools import date_tools
from xme.xmetools import json_tools
import random

async def send_time_message():
    bot = nonebot.get_bot()
    for group in config.SCHEDULER_GROUP:
        say = json.loads(requests.get('https://v1.hitokoto.cn/').text)
        something_to_say = f"{date_tools.get_time_period()}好呀~\n\n\"{say['hitokoto']}\"\n——{'无名' if not (x:=say['from_who']) else x} 《{say['from']}》"
        try:
            await bot.send_group_msg(group_id=group,
                                message=f'{something_to_say}')
        except CQHttpError:
            log.logger.error(f"定时器在 {group} 发消息失败")
            pass


@nonebot.scheduler.scheduled_job('cron', second='*', max_instances=3)
async def _():
    if not (6 <= datetime.now().hour <= 24): return
    if not random_tools.random_percent(0.05): return
    bot = nonebot.get_bot()
    group = random.choice(await bot.get_group_list())
    group_id = group['group_id']
    idles = json_tools.read_from_path("bot_messages.json")['idles']
    message = random.choice(idles)
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