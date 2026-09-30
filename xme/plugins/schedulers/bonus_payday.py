"""奖金账户每日发放调度：零点 cron + 启动补发，共用幂等的 pay_daily_bonuses。"""
import asyncio
from datetime import datetime, timedelta

import nonebot
from nonebot.log import logger

from xme.plugins.commands.xme_user.bonus import DAILY_BONUS_LIMIT, pay_daily_bonuses


@nonebot.scheduler.scheduled_job('cron', hour='0')
async def _bonus_payday():
    """每天 0 点把奖金账户余额发放到星币（每人每天最多 DAILY_BONUS_LIMIT）。"""
    # 发放是同步 DB 操作，放后台线程避免卡事件循环
    count, total = await asyncio.to_thread(pay_daily_bonuses)
    if count:
        logger.info(f"零点奖金发放完成：{count} 名用户，共 {total} 星币")


# 启动补发：bot 跨过零点不在线（关机/重启）时，启动后补发当天份（函数幂等，已发过则跳过）
@nonebot.scheduler.scheduled_job('date', run_date=datetime.now() + timedelta(seconds=30))
async def _bonus_startup_catchup():
    try:
        count, total = await asyncio.to_thread(pay_daily_bonuses)
        if count:
            logger.info(f"启动补发奖金完成：{count} 名用户，共 {total} 星币")
    except Exception as ex:
        logger.warning(f"启动补发奖金失败: {ex}")
