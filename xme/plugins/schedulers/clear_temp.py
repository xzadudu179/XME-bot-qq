import nonebot
from xme.xmetools import file_tools
bot = nonebot.get_bot()

@nonebot.scheduler.scheduled_job('cron', day='*')
async def del_temp_images():
    file_tools.clear_temps()