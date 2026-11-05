"""爱发电工具包：开放平台 API 客户端与数据聚合，供命令插件、server_app 路由复用。

典型用法：
    from xme.xmetools.afdiantools import AFDIAN_CLIENT, get_ranking
    ranking = await get_ranking(AFDIAN_CLIENT)
"""
from xme.xmetools.afdiantools.client import (
    AFDIAN_CLIENT,
    AfdianApiError,
    AfdianClient,
    parse_order_time,
)
from xme.xmetools.afdiantools.plans import (
    PLAN_BENEFITS,
    ActivePlan,
    PlanBenefit,
    find_benefit,
    get_active_plan,
    get_daily_sign_bonus,
    is_plan_active,
    parse_plan,
)
from xme.xmetools.afdiantools.stats import (
    MonthStats,
    OrderBrief,
    PlanInfo,
    RankEntry,
    SponsorProfile,
    TotalStats,
    get_month_stats,
    get_plans,
    get_ranking,
    get_shop_orders,
    get_sponsor_profile,
    get_total_stats,
    is_sponsor_order,
    order_amount,
)

__all__ = [
    "AFDIAN_CLIENT",
    "AfdianApiError",
    "AfdianClient",
    "parse_order_time",
    "PLAN_BENEFITS",
    "ActivePlan",
    "PlanBenefit",
    "find_benefit",
    "get_active_plan",
    "get_daily_sign_bonus",
    "is_plan_active",
    "parse_plan",
    "MonthStats",
    "OrderBrief",
    "PlanInfo",
    "RankEntry",
    "SponsorProfile",
    "TotalStats",
    "get_month_stats",
    "get_plans",
    "get_ranking",
    "get_shop_orders",
    "get_sponsor_profile",
    "get_total_stats",
    "is_sponsor_order",
    "order_amount",
]
