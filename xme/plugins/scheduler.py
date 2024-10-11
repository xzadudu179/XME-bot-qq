from datetime import datetime
import nonebot
import config
import pytz
from aiocqhttp.exceptions import Error as CQHttpError


@nonebot.scheduler.scheduled_job('cron', hour='0')
async def _():
    bot = nonebot.get_bot()
    now = datetime.now(pytz.timezone('Asia/Shanghai'))
    try:
        for group in config.GROUPS_WHITELIST:
            await bot.send_group_msg(group_id=group,
                                    message=f'又过了一天了——')
    except CQHttpError:
        pass