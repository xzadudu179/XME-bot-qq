from xme.xmetools.specialtips import SpecialTip
from xme.xmetools.timetools import get_time_period, time_diff, TimeUnit
from xme.xmetools.texttools import strip_cq
import time

# 对于 100% 概率的 tips 是必然出现 不受 msg 的 tips 概率影响
# 对于 1%~99% 受到 msg 的 tips 概率影响，在 “会出现 tip 的消息里” 有 n% 的概率出现
# 对于 0% 的 tip，加进默认 tips 列表按照默认 tips 判定
SPECIAL_TIPS: list[SpecialTip] = [
    SpecialTip(
        id="morning",
        condition=lambda _: get_time_period() == "早上",
        perc=0,
    ),
    SpecialTip(
        id="noon",
        condition=lambda _: get_time_period() == "中午",
        perc=0,
    ),
    SpecialTip(
        id="before_dawn",
        condition=lambda _: get_time_period() == "凌晨",
        perc=0,
    ),
    SpecialTip(
        id="forgot_sign",
        # streak>1 且今天未签 ⇒ 最后签到必是昨天 ⇒ 今天签到即免费续签；
        # 需付费补签的场景（最后签到是前天）streak 已归 0，天然不命中
        condition=lambda ctx:
            get_time_period() not in ["凌晨", "早上", "上午"] and
            ctx.user is not None and
            ctx.user.get_sign_streak() > 1 and not ctx.user.is_signed_today(),
        perc=20,
        times=3,
    ),
    SpecialTip(
        id="noticed_179",
        condition=lambda ctx: strip_cq(ctx.message).count("179") > 1,
        perc=30,
        times=0,
        params={"count": lambda ctx: strip_cq(ctx.message).count("179")},
    ),
    SpecialTip(
        id="long_time_no_see",
        condition=lambda ctx: bool(
            ctx.user and ctx.user.last_call_time
            and time_diff(ctx.user.last_call_time, time.time(), TimeUnit.DAY) > 30
        )
    ),
]