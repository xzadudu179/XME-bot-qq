from asyncio.log import logger
from bot_init import is_hook_need_update, reset_hook

from keys import VERCEL_DOCS_DEPLOY_HOOK
import nonebot
from xme.xmetools.reqtools import fetch_data_post

@nonebot.scheduler.scheduled_job(
    'cron',
    minute="*",
)
async def _():
    if is_hook_need_update():
        logger.info("正在触发文档站重建")
        try:
            await fetch_data_post(VERCEL_DOCS_DEPLOY_HOOK, {})
        except Exception as ex:
            logger.warning(f"触发文档站重建失败: {ex}")
        reset_hook()

