"""爱发电套餐权益：订阅期间持续生效的权益（目前为「每日签到额外星币」）。

与一次性发电奖励（afdian/rewards.py）互补：
- 一次性奖励按累计金额触发，领一次就结束；
- 套餐权益按「当前订阅是否有效」判断，订阅期间每天都能享受。

套餐按 plan_id 精确匹配 > 套餐名匹配 > 价格门槛（min_price）三级匹配：
不想逐个登记套餐时，直接按「实际支付价格 ≥ N 元」配置即可，多买的套餐不会叠加。
本模块只依赖爱发电客户端，不感知 QQ/User，签到等插件从 xmetools 调用。
"""
import asyncio
import time
from dataclasses import dataclass

from nonebot.log import logger

from xme.xmetools.afdiantools.client import AfdianApiError, AfdianClient

# 签到等高频路径的查询超时：绝不能因为爱发电接口慢而卡住签到
PLAN_QUERY_TIMEOUT = 5.0


@dataclass(frozen=True)
class PlanBenefit:
    """一个套餐对应的权益配置。

    匹配优先级（find_benefit 实现）：plan_ids 精确 > plan_names 名称 > min_price 价格门槛。
    min_price：套餐实际支付价格（show_price）≥ 该值时适用；多个门槛同时命中时取门槛最高的一条。
    daily_sign_bonus：订阅期间每天签到的额外星币数。
    label：给用户看的套餐名（列表展示用）。
    """

    plan_ids: tuple[str, ...] = ()
    plan_names: tuple[str, ...] = ()
    daily_sign_bonus: int = 0
    label: str = ""
    min_price: float = 0.0


@dataclass(frozen=True)
class ActivePlan:
    """用户当前有效的套餐（由 query-sponsor 的 current_plan/sponsor_plans 解析）。"""

    plan_id: str = ""
    name: str = ""
    expire_time: int | None = None
    permanent: bool = False
    pay_month: int = 0
    price: str = ""
    benefit: PlanBenefit | None = None


# ---- 套餐权益配置（改这里即可）----
PLAN_BENEFITS: list[PlanBenefit] = [
    PlanBenefit(
        min_price=17.9,
        daily_sign_bonus=15,
        label="签到星币奖励（15）",
    ),
    # 也可以按具体套餐精确配置（优先级高于价格门槛）：
    # PlanBenefit(
    #     plan_ids=("填爱发电方案 id",),
    #     plan_names=("套餐名",),
    #     daily_sign_bonus=30,
    #     label="某个特殊套餐",
    # ),
]


def _to_float(value) -> float:
    """把价格字段（字符串或数字）安全转为 float，非法值按 0 处理。"""
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return 0.0


def find_benefit(plan_id: str = "", plan_name: str = "", price: float | str = 0.0,
                 benefits: list[PlanBenefit] | None = None) -> PlanBenefit | None:
    """纯函数：匹配套餐权益配置，未配置返回 None。

    优先级：plan_id 精确匹配 > 套餐名匹配 > 价格门槛（取门槛最高的一条）。
    """
    benefits = PLAN_BENEFITS if benefits is None else benefits
    if plan_id:
        for benefit in benefits:
            if plan_id in benefit.plan_ids:
                return benefit
    if plan_name:
        for benefit in benefits:
            if plan_name in benefit.plan_names:
                return benefit
    price_value = _to_float(price)
    matched = [
        benefit for benefit in benefits
        if benefit.min_price > 0 and price_value >= benefit.min_price
    ]
    if not matched:
        return None
    return max(matched, key=lambda benefit: benefit.min_price)


def parse_plan(raw: dict) -> ActivePlan | None:
    """纯函数：把 query-sponsor 返回的单个方案 dict 解析为 ActivePlan。

    没有 plan_id 且没有名称（未订阅时的 {"name": ""}）返回 None。
    """
    if not isinstance(raw, dict):
        return None
    plan_id = str(raw.get("plan_id") or "")
    name = str(raw.get("name") or "")
    if not plan_id and not name:
        return None
    try:
        expire_time = int(raw["expire_time"]) if raw.get("expire_time") else None
    except (TypeError, ValueError):
        expire_time = None
    try:
        pay_month = int(raw.get("pay_month") or 0)
    except (TypeError, ValueError):
        pay_month = 0
    return ActivePlan(
        plan_id=plan_id,
        name=name,
        expire_time=expire_time,
        permanent=bool(raw.get("permanent")),
        pay_month=pay_month,
        price=str(raw.get("show_price") or raw.get("price") or ""),
    )


def is_plan_active(plan: ActivePlan, now: float | None = None) -> bool:
    """纯函数：套餐是否在有效期内。

    永久方案直接有效；平台只在订阅有效时返回 current_plan，
    因此缺失 expire_time 也按有效处理；否则比较到期时间。
    """
    if plan.permanent:
        return True
    if plan.expire_time is None:
        return True
    return plan.expire_time > (time.time() if now is None else now)


def _benefit_bonus(plan: ActivePlan) -> int:
    """该套餐在当前配置下的每日签到加成（用于多套餐择优，不叠加）。"""
    benefit = find_benefit(plan.plan_id, plan.name, plan.price)
    return benefit.daily_sign_bonus if benefit else 0


def _pick_plan(sponsor: dict, now: float | None = None) -> ActivePlan | None:
    """从一条赞助者记录里选出当前有效套餐。

    同时有多个有效套餐（多买/续费/历史方案未到期）时只取一个：加成最高优先，
    相同则取到期更晚的。因此「多买」不会重复发放，权益只按最优套餐给一份。
    """
    raw_plans = [sponsor.get("current_plan") or {}] + list(sponsor.get("sponsor_plans") or [])
    unique: dict[str, ActivePlan] = {}
    for raw in raw_plans:
        plan = parse_plan(raw)
        if plan is None or not is_plan_active(plan, now):
            continue
        key = plan.plan_id or plan.name
        existing = unique.get(key)
        if existing is None or (plan.expire_time or 0) > (existing.expire_time or 0):
            unique[key] = plan
    if not unique:
        return None
    return max(unique.values(), key=lambda plan: (_benefit_bonus(plan), plan.expire_time or 0))


async def get_active_plan(client: AfdianClient, afdian_id: str) -> ActivePlan | None:
    """查询该爱发电用户当前有效的套餐并匹配权益；未订阅/查询失败返回 None。"""
    if not afdian_id:
        return None
    sponsors, _ = await client.get_all_sponsors()
    sponsor = next(
        (s for s in sponsors if str((s.get("user") or {}).get("user_id") or "") == str(afdian_id)),
        None,
    )
    if sponsor is None:
        return None
    plan = _pick_plan(sponsor)
    if plan is None:
        return None
    return ActivePlan(
        plan_id=plan.plan_id,
        name=plan.name,
        expire_time=plan.expire_time,
        permanent=plan.permanent,
        pay_month=plan.pay_month,
        price=plan.price,
        benefit=find_benefit(plan.plan_id, plan.name, plan.price),
    )


async def get_daily_sign_bonus(client: AfdianClient, afdian_id: str,
                               timeout: float = PLAN_QUERY_TIMEOUT) -> tuple[int, str]:
    """每日签到额外星币：返回 (数量, 套餐名)；无套餐/无权益/查询失败为 (0, "")。

    签到是高频路径，任何异常都吞掉并返回 0，绝不因爱发电接口问题打断签到。
    """
    if not afdian_id:
        return 0, ""
    try:
        plan = await asyncio.wait_for(get_active_plan(client, afdian_id), timeout=timeout)
    except (AfdianApiError, asyncio.TimeoutError) as e:
        logger.debug(f"afdian 套餐查询失败（{afdian_id}）：{e}")
        return 0, ""
    except Exception as e:
        logger.warning(f"afdian 套餐查询出现异常（{afdian_id}）：{e}")
        return 0, ""
    if plan is None or plan.benefit is None or plan.benefit.daily_sign_bonus <= 0:
        return 0, ""
    return plan.benefit.daily_sign_bonus, plan.name or plan.benefit.label
