import nonebot
from xme.xmetools.bottools import bot_call_action
bot = nonebot.get_bot()
import asyncio
import config

@nonebot.scheduler.scheduled_job('cron', day='*')
async def send_like():
    for f in await bot.get_friend_list():
        print(f"给 \"{f['nickname']}\" 点赞中")
        failed = True
        tried_times = 0
        if f['user_id'] == config.SELF_ID:
            continue
        while failed and tried_times < 30:
            try:
                await bot_call_action(bot, "send_like", user_id=f['user_id'], times=10)
                failed = False
            except:
                print("点赞失败，过五秒重新尝试")
                tried_times += 1
                await asyncio.sleep(5)