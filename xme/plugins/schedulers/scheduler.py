from datetime import datetime
import nonebot
import config
import pytz
from aiocqhttp.exceptions import Error as CQHttpError


@nonebot.scheduler.scheduled_job('cron', hour='12')
async def _():
    bot = nonebot.get_bot()
    now = datetime.now(pytz.timezone('Asia/Shanghai'))
    try:
        for group in config.GROUPS_WHITELIST:
            await bot.send_group_msg(group_id=group,
                                    message=f'中午好哇——')
    except CQHttpError:
        pass