import nonebot
from xme.xmetools.bottools import bot_call_action
bot = nonebot.get_bot()

@nonebot.scheduler.scheduled_job('cron', day='*')
async def send_like():
    for f in await bot.get_friend_list():
        print(f"给 \"{f['nickname']}\" 点赞中")
        await bot_call_action(bot, "send_like", user_id=f['user_id'], times=10)