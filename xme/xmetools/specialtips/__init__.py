"""特殊 tip：
对于 perc 100 的 tips 是必然出现 不受 msg 的 tips 概率影响
对于 1~99 受到 msg 的 tips 概率影响，在 “会出现 tip 的消息里” 有 n% 的概率出现
对于 0 的 tip，加进默认 tips 列表按照默认 tips 判定

所有特殊 tip 默认对每个用户每天最多出现一次，可用 times 调整（0=不限）。新增一条特殊 tip 两步：
1. 在 special_tip_list.py 的 SPECIAL_TIPS 中添加 SpecialTip(id=..., condition=..., perc=...)；
2. 在角色文件 bot_info.special_tips 下添加该 id 对应的文本（支持 {bot_name} 等占位符）。
"""
import random
from dataclasses import dataclass, field
from typing import Any, Callable

from nonebot.log import logger
from nonebot.session import BaseSession

from xme.xmetools import jsontools
from xme.xmetools.randtools import random_percent
from xme.xmetools.timetools import curr_days

# 记账文件：{tip_id: {str(user_id): {"day": 天数（curr_days）, "count": 当天已出现次数}}}
SPECIAL_TIPS_VARS_PATH = "data/special_tips.json"


@dataclass
class SpecialTipContext:
    """特殊 tip 条件函数的入参上下文"""
    message: str  # 即将发送的消息全文（不含 tip 部分）
    session: BaseSession  # 触发本次回复的会话，可取 event / bot 等

    @property
    def user_id(self) -> int | None:
        """触发消息的用户 qq，取不到为 None（此时不参与特殊 tip）"""
        return getattr(self.session.event, "user_id", None)

    @property
    def group_id(self) -> int | None:
        """触发消息的群号，私聊为 None"""
        return getattr(self.session.event, "group_id", None)

    @property
    def user(self) -> "User | None": # type: ignore
        """触发消息的 xme 用户，不存在时返回 None（不创建新用户）"""
        if self.user_id is None:
            return None
        from xme.plugins.commands.xme_user.classes.user import User
        return User.load(self.user_id, create_default_user=False)

    @property
    def command(self) -> str | None:
        """触发回复的指令名；非指令会话（如定时任务）为 None"""
        return getattr(getattr(self.session, "cmd", None), "name", None)

    @property
    def arg(self) -> str | None:
        """触发回复的指令参数纯文本（去 CQ 码）；非指令会话为 None，指令无参数时为空串"""
        if self.command is None:
            return None
        if getattr(self.session, "current_arg", None) is None:
            return ""
        return self.session.current_arg_text


@dataclass
class SpecialTip:
    """一条特殊 tip 的定义"""
    # 文本键
    id: str
    condition: Callable[[SpecialTipContext], bool]
    # 出现概率，详见顶部
    perc: float | int = 100
    # 每天对每个用户最多出现次数；0=不限
    times: int = 1
    # 文本占位符
    params: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        # 定义期校验（fail fast），不把非法 perc/times 拖到每次消息求值时才炸
        if not (0 <= self.perc <= 100):
            raise ValueError(f"特殊 tip {self.id} 的 perc 需在 0~100 之间，当前为 {self.perc}")
        if self.times < 0:
            raise ValueError(f"特殊 tip {self.id} 的 times 不能为负数，当前为 {self.times}")


# 注册表实际内容在 special_tip_list.py（惰性导入，避免与插件层循环依赖）



def _load_used_days(path: str) -> dict:
    """读取记账文件，返回 {tip_id: {str(user_id): {"day": 天数, "count": 次数}}}

    兼容旧格式（值为天数 int，按当天出现 1 次处理）；文件缺失/损坏按空记账处理。
    """
    data = jsontools.read_from_path(path)
    if not isinstance(data, dict):
        return {}
    for entries in data.values():
        if not isinstance(entries, dict):
            continue
        for user_id, entry in entries.items():
            if isinstance(entry, int):
                entries[user_id] = {"day": entry, "count": 1}
    return data


def _save_used_day(path: str, tip_id: str, user_id: int, day: int) -> None:
    """记录某用户某特殊 tip 出现一次：同一天累加次数，跨天重置为 1；文件缺失时初始化为空结构"""
    data = _load_used_days(path)
    entry = data.setdefault(tip_id, {}).setdefault(str(user_id), {})
    if isinstance(entry, dict) and entry.get("day") == day:
        entry["count"] = entry.get("count", 0) + 1
    else:
        data[tip_id][str(user_id)] = {"day": day, "count": 1}
    jsontools.save_to_path(path, data)


def _eligible_tips(used_days: dict, user_id: int | None, today: int, context: SpecialTipContext, perc_match: Callable[[float | int], bool]) -> list[SpecialTip]:
    """过滤出 perc 满足 perc_match、条件命中且该用户今天出现次数未达上限（times=0 不限）的特殊 tip"""
    if user_id is None:
        return []
    eligible = []
    from . import special_tip_list
    for tip in special_tip_list.SPECIAL_TIPS:
        if not perc_match(tip.perc):
            continue
        entry = used_days.get(tip.id, {}).get(str(user_id)) or {}
        if tip.times > 0 and entry.get("day") == today and entry.get("count", 0) >= tip.times:
            continue
        try:
            if tip.condition(context):
                eligible.append(tip)
        except Exception as ex:
            logger.warning(f"特殊 tip {tip.id} 的条件函数出错（{type(ex).__name__}: {str(ex)[:120]}），视为不匹配")
    return eligible


def pick_special_tip(context: SpecialTipContext, *, vars_path: str = SPECIAL_TIPS_VARS_PATH) -> SpecialTip | None:
    """随机挑一条该用户今天可出现的必现类（perc=100）特殊 tip，没有则返回 None"""
    eligible = _eligible_tips(_load_used_days(vars_path), context.user_id, curr_days(), context, lambda p: p == 100)
    if not eligible:
        return None
    return random.choice(eligible)


def roll_special_tip(context: SpecialTipContext, *, vars_path: str = SPECIAL_TIPS_VARS_PATH) -> SpecialTip | None:
    """出 tip 名额已定时，对掷点类（0<pers<100）特殊 tip 各自掷 perc 抢占出场，随机返回一条掷中的，没有则返回 None"""
    eligible = _eligible_tips(_load_used_days(vars_path), context.user_id, curr_days(), context, lambda p: 0 < p < 100)
    winners = [tip for tip in eligible if random_percent(tip.perc)]
    if not winners:
        return None
    return random.choice(winners)


def eligible_special_tips(context: SpecialTipContext, *, vars_path: str = SPECIAL_TIPS_VARS_PATH) -> list[SpecialTip]:
    """列出该用户今天可出现的池掺杂类（perc=0）特殊 tip，供普通 tip 池等权重抽取"""
    return _eligible_tips(_load_used_days(vars_path), context.user_id, curr_days(), context, lambda p: p == 0)


def mark_special_tip_used(tip: SpecialTip, user_id: int, *, vars_path: str = SPECIAL_TIPS_VARS_PATH) -> None:
    """记账：该用户该特殊 tip 出现次数 +1（同日累加，跨天重置）"""
    _save_used_day(vars_path, tip.id, user_id, curr_days())


def resolve_tip_params(tip: SpecialTip, context: SpecialTipContext) -> dict[str, Any] | None:
    """解析特殊 tip 的 params：可调用的值以 ctx 求值，其余原样透传

    任一项求值出错返回 None（本次不显示该 tip，也不记账），不让单个参数拖垮消息发送。
    """
    resolved: dict[str, Any] = {}
    try:
        for key, value in tip.params.items():
            resolved[key] = value(context) if callable(value) else value
    except Exception as ex:
        logger.warning(f"特殊 tip {tip.id} 的 params 解析出错（{type(ex).__name__}: {str(ex)[:120]}），本次不显示")
        return None
    return resolved
