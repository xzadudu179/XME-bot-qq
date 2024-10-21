from datetime import datetime
import nonebot
import config
import requests
import pytz
import json
from aiocqhttp.exceptions import Error as CQHttpError
from nonebot import log
from xme.xmetools import date_tools

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