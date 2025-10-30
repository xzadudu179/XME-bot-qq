import nonebot
from xme.xmetools import filetools
bot = nonebot.get_bot()

@nonebot.scheduler.scheduled_job('cron', day='*')
async def check_use_time():
    # 检查各群的调用
    ...