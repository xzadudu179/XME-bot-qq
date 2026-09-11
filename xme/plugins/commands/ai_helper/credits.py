# some are made by Deepseek-v4-flash-vison-exp at Deepseek Harness
"""AI credits 双余额账本：每周免费额度 + 用户自存 credits（与金币 coins 体系无关）。

- 每周余额 = TOKENS_LIMIT_WEEKLY − 本周已计（counters["ai_helper"]["count"]，
  自然周：周一 00:00 GMT+8 惰性重置）。
- 自存 credits = user.plugin_datas["ai_helper"]["credits"]（float，可为负，初始 0）。
- 结算规则：消耗先记本周计数（封顶额度，防透支重复落账），溢出部分从自存 credits
  扣（可扣成负）；负数长期保存，下周额度重置后继续压低总余额。
"""
import config
from xme.xmetools import timetools
from xme.xmetools.dicttools import get_value, set_value

from xme.plugins.commands.xme_user.classes import user as u

from .constants import __plugin_name__, TOKENS_LIMIT_WEEKLY


def extra_credits(user) -> float:
    """读取用户自存 credits（plugin_datas["ai_helper"]["credits"]，无记录为 0）。"""
    return float(get_value(__plugin_name__, "credits", search_dict=user.plugin_datas, default=0) or 0)


def _refresh_weekly(user) -> None:
    """跨周惰性重置本周计数（周一 00:00 GMT+8 为界，原 custom_limit 的 detect_limit 等价逻辑）。"""
    u.detect_limit(user, __plugin_name__, 1,
                   count_limit=TOKENS_LIMIT_WEEKLY, unit=timetools.TimeUnit.WEEK)


def ai_credits_left(user) -> float:
    """用户当前总余额 = 本周免费剩余 + 自存 credits（可为负，≤0 时不可再调用）。"""
    _refresh_weekly(user)
    _, used = u.get_limit_info(user, __plugin_name__)
    return (TOKENS_LIMIT_WEEKLY - used) + extra_credits(user)


def settle_credits(user, amount: float) -> float:
    """结算一笔 credits 消耗：先扣本周免费额度（封顶），溢出从自存 credits 扣（可负）。

    返回结算后的总余额。不判断超管——是否跳过由调用方决定。
    """
    amount = max(0.0, float(amount))
    _refresh_weekly(user)
    _, used = u.get_limit_info(user, __plugin_name__)
    weekly_left = TOKENS_LIMIT_WEEKLY - used
    from_weekly = min(amount, max(0.0, weekly_left))
    to_extra = amount - from_weekly
    if from_weekly:
        u.limit_count_tick(user, __plugin_name__, from_weekly)
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
