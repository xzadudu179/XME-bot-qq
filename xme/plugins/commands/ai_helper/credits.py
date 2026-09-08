# some are made by Deepseek-v4-flash-vison-exp at Deepseek Harness
"""AI credits 双余额账本：每日免费额度 + 用户自存 credits（与金币 coins 体系无关）。

- 每日余额 = TOKENS_LIMIT − 当日已计（counters["ai_helper"]["count"]，跨天惰性重置）。
- 自存 credits = user.plugin_datas["ai_helper"]["credits"]（float，可为负，初始 0）。
- 结算规则：消耗先记每日计数（封顶 TOKENS_LIMIT，防透支重复落账），溢出部分从
  自存 credits 扣（可扣成负）；负数长期保存，次日每日额度重置后继续压低总余额。
"""
import config
from xme.xmetools import timetools
from xme.xmetools.dicttools import get_value, set_value

from xme.plugins.commands.xme_user.classes import user as u

from .constants import __plugin_name__, TOKENS_LIMIT


def extra_credits(user) -> float:
    """读取用户自存 credits（plugin_datas["ai_helper"]["credits"]，无记录为 0）。"""
    return float(get_value(__plugin_name__, "credits", search_dict=user.plugin_datas, default=0) or 0)


def _refresh_daily(user) -> None:
    """跨天惰性重置每日计数（原 custom_limit.check_invalid 的 detect_limit 等价逻辑）。"""
    u.detect_limit(user, __plugin_name__, 1,
                   count_limit=TOKENS_LIMIT, unit=timetools.TimeUnit.DAY)


def ai_credits_left(user) -> float:
    """用户当前总余额 = 每日免费剩余 + 自存 credits（可为负，≤0 时不可再调用）。"""
    _refresh_daily(user)
    _, used = u.get_limit_info(user, __plugin_name__)
    return (TOKENS_LIMIT - used) + extra_credits(user)


def settle_credits(user, amount: float) -> float:
    """结算一笔 credits 消耗：先扣每日免费额度（封顶），溢出从自存 credits 扣（可负）。

    返回结算后的总余额。不判断超管——是否跳过由调用方决定。
    """
    amount = max(0.0, float(amount))
    _refresh_daily(user)
    _, used = u.get_limit_info(user, __plugin_name__)
    daily_left = TOKENS_LIMIT - used
    from_daily = min(amount, max(0.0, daily_left))
    to_extra = amount - from_daily
    if from_daily:
        u.limit_count_tick(user, __plugin_name__, from_daily)
    if to_extra:
        set_value(__plugin_name__, "credits", search_dict=user.plugin_datas,
                  set_method=lambda v: (float(v) if v is not None else 0.0) - to_extra)
    user.update("plugin_datas", "counters")
    return ai_credits_left(user)


def settle_split(credits_split: dict) -> dict[str, float]:
    """按均摊表逐参与者结算 credits，返回 {uid 字符串: 结算后总余额}。"""
    lefts: dict[str, float] = {}
    for split_id, amount in credits_split.items():
        uid = int(split_id)
        # if uid in config.SUPERUSERS:
            # continue
        lefts[split_id] = settle_credits(u.try_load(uid), amount)
    return lefts
