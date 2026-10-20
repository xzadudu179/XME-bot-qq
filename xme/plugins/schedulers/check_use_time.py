import asyncio
import time
from datetime import datetime

import nonebot
from nonebot.log import logger
from xme.xmetools.msgtools import send_to_superusers
from xme.xmetools.plugintools import PluginCallData

bot = nonebot.get_bot()

# 群聊被判为不活跃的无互动天数
INACTIVE_DAYS = 60
SECONDS_PER_DAY = 86400

@nonebot.scheduler.scheduled_job('cron', day='*')
async def check_use_time():
    """每天检查 bot 所在的所有群，把超过 INACTIVE_DAYS 天没有任何指令
    调用记录的群汇总警告给 SUPERUSER，无不活跃群时不发消息。"""
    groups = await bot.get_group_list()
    last_calls = await asyncio.to_thread(PluginCallData.get_last_call_times)
    now = time.time()
    threshold = now - INACTIVE_DAYS * SECONDS_PER_DAY
    lines = []
    # 暂时不用
    exit_groups = []
    for group in groups:
        last_call = last_calls.get(str(group["group_id"]))
        if last_call is not None and last_call >= threshold:
            continue
        if last_call is None:
            lines.append(f"- {group['group_name']}({group['group_id']})：从未有过调用记录")
        else:
            days = int((now - last_call) // SECONDS_PER_DAY)
            last_time = datetime.fromtimestamp(last_call).strftime("%Y-%m-%d %H:%M")
            lines.append(f"- {group['group_name']}({group['group_id']})：最后互动 {last_time}（{days} 天前）")
            exit_groups.append(group['group_id'])
    if not lines:
        return
    logger.warning(f"警告：有 {len(lines)} 个群超过 {INACTIVE_DAYS} 天没有任何互动：\n" + "\n".join(lines))
    # await send_to_superusers(bot, f"警告：有 {len(lines)} 个群超过 {INACTIVE_DAYS} 天没有任何互动：\n" + "\n".join(lines))
    # NOTE 之后加退群逻辑
    # exit_groups
