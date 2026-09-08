"""爱发电数据聚合：月度/累计统计、发电排行、用户画像、方案订阅与商品订单。

所有函数只做纯聚合（数据来自 AfdianClient），返回 dataclass，
供命令插件、server_app 路由和未来 AI 工具复用。
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from xme.xmetools.afdiantools.client import AfdianClient, parse_order_time

# 订单状态：2 = 交易成功（官方文档）
ORDER_STATUS_SUCCESS = 2
# 商品类型：0 = 发电方案，1 = 售卖方案（官方文档）
PRODUCT_TYPE_SPONSOR = 0
PRODUCT_TYPE_SHOP = 1


def order_time(order: dict) -> datetime | None:
    """订单下单时间：优先 create_time 字段，缺失时退回订单号前缀解析。"""
    create_time = order.get("create_time")
    if create_time:
        try:
            return datetime.fromtimestamp(int(create_time))
        except (TypeError, ValueError, OSError, OverflowError):
            return None
    return parse_order_time(order.get("out_trade_no", ""))


@dataclass
class MonthStats:
    """自然月发电统计。"""

    year: int
    month: int
    order_count: int = 0        # 发电笔数
    total_amount: float = 0.0   # 真实付款合计（元）
    sponsor_count: int = 0      # 发电人数（按用户去重）


@dataclass
class TotalStats:
    """累计发电统计。"""

    sponsor_count: int = 0      # 总发电人数（query-sponsor total_count）
    order_count: int = 0        # 累计发电笔数
    total_amount: float = 0.0   # 累计真实付款合计（元）


@dataclass
class RankEntry:
    """发电排行条目，amount 为真实付款金额（兑换码计 0）。"""

    rank: int = 0
    user_id: str = ""
    name: str = ""
    avatar: str = ""
    amount: float = 0.0
    order_count: int = 0
    last_pay_time: int | None = None


@dataclass
class OrderBrief:
    """最近订单摘要。"""

    out_trade_no: str = ""
    amount: float = 0.0          # 真实付款
    show_amount: str = "0.00"    # 界面展示金额（含折扣前口径）
    plan_title: str = ""
    time: datetime | None = None
    remark: str = ""


@dataclass
class SponsorProfile:
    """单个用户的发电画像（供 .afd me 与"指定用户查询"工具使用）。"""

    user_id: str = ""
    name: str = ""
    avatar: str = ""
    month_amount: float = 0.0        # 本月发电金额（真实付款）
    month_order_count: int = 0
    recent_amount: float = 0.0       # 最近 days 天发电金额
    recent_order_count: int = 0
    recent_days: int = 30
    total_amount: float = 0.0        # 累计发电金额（真实付款）
    all_sum_amount: str = "0.00"     # 平台口径累计（折扣前，含兑换码）
    first_pay_time: int | None = None
    last_pay_time: int | None = None
    current_plan_name: str = "无"
    plan_expire_time: int | None = None
    plan_permanent: bool = False
    recent_orders: list[OrderBrief] = field(default_factory=list)


@dataclass
class PlanInfo:
    """发电方案（订阅制度）聚合信息。"""

    plan_id: str = ""
    name: str = ""
    price: str = "0.00"          # 折扣前价格
    show_price: str = "0.00"     # 实际价格
    current_count: int = 0       # 当前订阅人数（current_plan 指向该方案）
    total_count: int = 0         # 历史订阅过的人数


def is_sponsor_order(order: dict) -> bool:
    """订单是否为交易成功的发电订单（排除售卖方案商品）。"""
    return (
        order.get("status") == ORDER_STATUS_SUCCESS
        and int(order.get("product_type") or PRODUCT_TYPE_SPONSOR) == PRODUCT_TYPE_SPONSOR
    )


def order_amount(order: dict) -> float:
    """订单真实付款金额（兑换码订单为 0）。"""
    try:
        return float(order.get("total_amount") or 0)
    except (TypeError, ValueError):
        return 0.0


async def get_month_stats(client: AfdianClient, year: int | None = None, month: int | None = None) -> MonthStats:
    """统计指定自然月（默认当月）的发电笔数、真实收入与发电人数。"""
    now = datetime.now()
    year = year or now.year
    month = month or now.month
    start = datetime(year, month, 1)
    end = datetime(year + (month // 12), (month % 12) + 1, 1)
    stats = MonthStats(year=year, month=month)
    users: set[str] = set()
    for order in await client.get_all_orders():
        if not is_sponsor_order(order):
            continue
        time = order_time(order)
        if time is None or not (start <= time < end):
            continue
        stats.order_count += 1
        stats.total_amount += order_amount(order)
        users.add(order.get("user_id") or "")
    stats.total_amount = round(stats.total_amount, 2)
    stats.sponsor_count = len(users - {""})
    return stats


async def get_total_stats(client: AfdianClient) -> TotalStats:
    """统计累计发电：总人数（平台口径）与累计真实收入。"""
    sponsors, total_count = await client.get_all_sponsors()
    stats = TotalStats(sponsor_count=total_count)
    for order in await client.get_all_orders():
        if not is_sponsor_order(order):
            continue
        stats.order_count += 1
        stats.total_amount += order_amount(order)
    stats.total_amount = round(stats.total_amount, 2)
    return stats


async def get_ranking(client: AfdianClient) -> list[RankEntry]:
    """获取所有发电用户按真实付款金额降序的排行。

    金额按订单 total_amount 聚合（兑换码计 0）；昵称/头像来自
    query-sponsor，无订单记录的赞助者金额记 0 以保证名单完整。
    """
    sponsors, _ = await client.get_all_sponsors()
    orders = await client.get_all_orders()
    # 先按赞助者名单初始化，保证仅兑换码/无订单用户也出现在排行中
    agg: dict[str, dict] = {}
    infos: dict[str, dict] = {}
    for sponsor in sponsors:
        user = sponsor.get("user") or {}
        user_id = str(user.get("user_id") or "")
        if not user_id:
            continue
        infos[user_id] = sponsor
        agg[user_id] = {"amount": 0.0, "count": 0, "last_pay": None, "name": ""}
    for order in orders:
        if not is_sponsor_order(order):
            continue
        user_id = str(order.get("user_id") or "")
        if user_id not in agg:
            agg[user_id] = {"amount": 0.0, "count": 0, "last_pay": None, "name": ""}
        # 赞助者名单里没有的用户，用订单自带的 user_name 作昵称兜底
        if not agg[user_id]["name"]:
            agg[user_id]["name"] = str(order.get("user_name") or "")
        agg[user_id]["amount"] += order_amount(order)
        agg[user_id]["count"] += 1
        time = order_time(order)
        if time is not None:
            ts = int(time.timestamp())
            if agg[user_id]["last_pay"] is None or ts > agg[user_id]["last_pay"]:
                agg[user_id]["last_pay"] = ts
    entries: list[RankEntry] = []
    for user_id, data in agg.items():
        sponsor = infos.get(user_id) or {}
        user = sponsor.get("user") or {}
        entries.append(RankEntry(
            user_id=user_id,
            name=user.get("name") or data["name"] or "匿名发电用户",
            avatar=user.get("avatar") or "",
            amount=round(data["amount"], 2),
            order_count=data["count"],
            last_pay_time=data["last_pay"],
        ))
    entries.sort(key=lambda e: (e.amount, e.order_count), reverse=True)
    for index, entry in enumerate(entries, start=1):
        entry.rank = index
    return entries


async def get_sponsor_profile(client: AfdianClient, user_id: str, days: int = 30) -> SponsorProfile | None:
    """获取指定用户的发电画像，从未发电且不在赞助名单时返回 None。

    Args:
        client (AfdianClient): 爱发电客户端
        user_id (str): 被查询用户的爱发电 user_id
        days (int): 「最近」统计窗口天数，默认 30 天
    """
    sponsors, _ = await client.get_all_sponsors()
    sponsor = next(
        (s for s in sponsors if str((s.get("user") or {}).get("user_id") or "") == str(user_id)),
        None,
    )
    orders = await client.get_all_orders()
    now = datetime.now()
    month_start = datetime(now.year, now.month, 1)
    recent_start = now - timedelta(days=days)
    profile = SponsorProfile(
        user_id=str(user_id),
        recent_days=days,
        recent_orders=[],
    )
    if sponsor is not None:
        user = sponsor.get("user") or {}
        plan = sponsor.get("current_plan") or {}
        profile.name = user.get("name") or ""
        profile.avatar = user.get("avatar") or ""
        profile.all_sum_amount = str(sponsor.get("all_sum_amount") or "0.00")
        first_pay = sponsor.get("first_pay_time")
        last_pay = sponsor.get("last_pay_time")
        profile.first_pay_time = int(first_pay) if first_pay else None
        profile.last_pay_time = int(last_pay) if last_pay else None
        profile.current_plan_name = plan.get("name") or "无"
        profile.plan_expire_time = plan.get("expire_time")
        profile.plan_permanent = bool(plan.get("permanent"))
    user_orders: list[dict] = []
    for order in orders:
        if not is_sponsor_order(order) or str(order.get("user_id") or "") != str(user_id):
            continue
        user_orders.append(order)
        time = order_time(order)
        if time is None:
            continue
        amount = order_amount(order)
        profile.total_amount += amount
        if time >= month_start:
            profile.month_amount += amount
            profile.month_order_count += 1
        if time >= recent_start:
            profile.recent_amount += amount
            profile.recent_order_count += 1
    profile.total_amount = round(profile.total_amount, 2)
    profile.month_amount = round(profile.month_amount, 2)
    profile.recent_amount = round(profile.recent_amount, 2)
    user_orders.sort(
        key=lambda o: order_time(o) or datetime.min,
        reverse=True,
    )
    profile.recent_orders = [
        OrderBrief(
            out_trade_no=o.get("out_trade_no") or "",
            amount=order_amount(o),
            show_amount=str(o.get("show_amount") or "0.00"),
            plan_title=str(o.get("plan_title") or ""),
            time=order_time(o),
            remark=str(o.get("remark") or ""),
        )
        for o in user_orders[:5]
    ]
    if sponsor is None and not user_orders:
        return None
    return profile


async def get_plans(client: AfdianClient) -> list[PlanInfo]:
    """聚合所有发电方案与订阅情况，供订阅类功能接入。

    方案信息来自每个赞助者的 sponsor_plans / current_plan，
    价格为平台返回的折扣前 price 与实际 show_price。
    """
    sponsors, _ = await client.get_all_sponsors()
    plans: dict[str, PlanInfo] = {}
    seen: dict[str, set[str]] = {}
    for sponsor in sponsors:
        user_id = str((sponsor.get("user") or {}).get("user_id") or "")
        current = sponsor.get("current_plan") or {}
        for plan in sponsor.get("sponsor_plans") or [current]:
            plan_id = str(plan.get("plan_id") or "")
            if not plan_id:
                continue
            if plan_id not in plans:
                plans[plan_id] = PlanInfo(
                    plan_id=plan_id,
                    name=str(plan.get("name") or "未命名方案"),
                    price=str(plan.get("price") or "0.00"),
                    show_price=str(plan.get("show_price") or plan.get("price") or "0.00"),
                )
                seen[plan_id] = set()
            if user_id and user_id not in seen[plan_id]:
                seen[plan_id].add(user_id)
        current_id = str(current.get("plan_id") or "")
        if current_id and current_id in plans:
            plans[current_id].current_count += 1
    for plan_id, plan in plans.items():
        plan.total_count = len(seen[plan_id])
    return sorted(plans.values(), key=lambda p: (p.current_count, p.total_count), reverse=True)


async def get_shop_orders(client: AfdianClient, days: int | None = None) -> list[dict]:
    """获取售卖方案（商品购买）的成功订单，供购买类功能接入。

    Args:
        days (int | None): 仅保留最近 N 天的订单，None 表示全部
    """
    orders = await client.get_all_orders()
    cutoff = datetime.now() - timedelta(days=days) if days else None
    result: list[dict] = []
    for order in orders:
        if order.get("status") != ORDER_STATUS_SUCCESS:
            continue
        if int(order.get("product_type") or PRODUCT_TYPE_SPONSOR) != PRODUCT_TYPE_SHOP:
            continue
        time = order_time(order)
        if cutoff and time is not None and time < cutoff:
            continue
        result.append(order)
    return result
