"""afd rank 子命令：发电用户排行榜。"""
from character import get_message
from nonebot import CommandSession
from nonebot.log import logger

from xme.plugins.commands.afdian import __plugin_name__
from xme.plugins.commands.afdian.constants import (
    CMD_RANK,
    RANK_DEFAULT_COUNT,
    RANK_MAX_COUNT,
)
from xme.xmetools.afdiantools import (
    AFDIAN_CLIENT,
    AfdianApiError,
    RankEntry,
    get_ranking,
)

cmd_name = CMD_RANK
alias = ['排行', '排行榜']
usage = {
    "name": cmd_name,
    "desc": get_message("plugins", __plugin_name__, cmd_name, 'desc'),
    "introduction": get_message("plugins", __plugin_name__, cmd_name, 'introduction'),
    "usage": '<数量>',
    "permissions": [],
    "alias": alias
}

# 排名前三的奖牌图标
# MEDALS = ["🥇", "🥈", "🥉"]


def _parse_count(arg: str) -> int:
    """解析排行条数参数，非法或越界时回落到默认值/上限。"""
    try:
        count = int(arg)
    except (TypeError, ValueError):
        return RANK_DEFAULT_COUNT
    return max(1, min(count, RANK_MAX_COUNT))


def format_rank_line(entry: RankEntry) -> str:
    """把单条排行数据格式化为一行文案。"""
    # medal = MEDALS[entry.rank - 1] if entry.rank <= len(MEDALS) else f"{entry.rank}."
    medal = entry.rank
    return f"{medal} {entry.name}：￥{entry.amount:.2f} （{entry.order_count} 次）"


async def handle(session: CommandSession, arg: str) -> str:
    """查询发电排行并返回排行文案，arg 可指定展示条数。"""
    try:
        entries = await get_ranking(AFDIAN_CLIENT)
    except AfdianApiError as e:
        logger.warning(f"afd rank 获取排行失败: {e}")
        return get_message("plugins", __plugin_name__, 'api_error')
    if not entries:
        return get_message("plugins", __plugin_name__, cmd_name, 'empty')
    count = _parse_count(arg)
    ranking_text = "\n".join(format_rank_line(entry) for entry in entries[:count])
    return get_message(
        "plugins", __plugin_name__, cmd_name, 'success',
        ranking=ranking_text,
        total=len(entries),
        shown=min(count, len(entries)),
    )
