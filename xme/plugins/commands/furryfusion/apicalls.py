"""兽聚数据访问统一入口：命令层只经此调用，不感知具体数据源。"""
from datetime import datetime

from .providers import get_provider
from .providers.base import CST, FurEvent

# 时间表上已结束活动的保留天数，结束超过该天数的不再展示
ENDED_KEEP_DAYS = 10


async def get_countdown() -> list[FurEvent]:
    """获取兽聚时间表（已结束超过 10 天的活动不展示），失败时抛 FurAPIError。"""
    events = await get_provider().get_countdown()
    today = datetime.now(CST).date()
    return [e for e in events if (today - e.end.date()).days <= ENDED_KEEP_DAYS]


async def search(content: str) -> list[FurEvent]:
    """按关键词搜索兽聚活动，失败时抛 FurAPIError。"""
    return await get_provider().search(content)
