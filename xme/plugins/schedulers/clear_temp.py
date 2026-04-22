import nonebot
from xme.xmetools import filetools
bot = nonebot.get_bot()

@nonebot.scheduler.scheduled_job('cron', day='*')
async def del_temp_images():
    filetools.clear_temps()