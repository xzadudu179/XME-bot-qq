import nonebot
from nonebot.log import logger
from xme.xmetools.bottools import is_group_member_count_legal
bot = nonebot.get_bot()

@nonebot.scheduler.scheduled_job('cron', day='*')
async def leave_groups():
    groups = await bot.get_group_list()
    for group in groups:
        if is_group_member_count_legal(group):
            continue
        logger.info(f"退出群 {group} 因为人数过低")
        await bot.api.set_group_leave(group_id=group['group_id'])