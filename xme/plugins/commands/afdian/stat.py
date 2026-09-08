"""afd stat 子命令：SUPERUSER 专用的爱发电经营统计（收入数据不公开）。"""
from character import get_message
from nonebot import CommandSession
from nonebot.log import logger
from xme.xmetools.bottools import permission

from xme.plugins.commands.afdian import __plugin_name__
from xme.plugins.commands.afdian.constants import CMD_STAT
from xme.xmetools.afdiantools import (
    AFDIAN_CLIENT,
    AfdianApiError,
    get_month_stats,
    get_total_stats,
)

cmd_name = CMD_STAT
alias = ['统计']
usage = {
    "name": cmd_name,
    "desc": get_message("plugins", __plugin_name__, cmd_name, 'desc'),
    "introduction": get_message("plugins", __plugin_name__, cmd_name, 'introduction'),
    "usage": '<年份> <月份>',
    "permissions": ["是 SUPERUSER"],
    "alias": alias
}


@permission(lambda sender: sender.is_superuser, permission_help=usage["permissions"])
async def handle(session: CommandSession, arg: str) -> str:
    """汇总本月与累计发电数据，仅 SUPERUSER 可调用。"""
    parts = arg.split()
    year = int(parts[0]) if len(parts) > 0 and parts[0].isdigit() and len(parts[0]) == 4 else None
    month = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None
    try:
        month_stats = await get_month_stats(AFDIAN_CLIENT, year=year, month=month)
        total_stats = await get_total_stats(AFDIAN_CLIENT)
    except AfdianApiError as e:
        logger.warning(f"afd stat 获取统计失败: {e}")
        return get_message("plugins", __plugin_name__, 'api_error')
    return get_message(
        "plugins", __plugin_name__, cmd_name, 'success',
        # 年份以字符串传入，避免文案格式化时被加千分位（2026 -> 2,026）
        year=str(month_stats.year),
        month=str(month_stats.month),
        month_amount=f"{month_stats.total_amount:,.2f}",
        month_count=month_stats.order_count,
        month_sponsors=month_stats.sponsor_count,
        total_amount=f"{total_stats.total_amount:,.2f}",
        total_count=total_stats.order_count,
        sponsor_count=total_stats.sponsor_count,
    )
