"""爱发电发电奖励：规则定义、待发奖励规划、发放与查重。

规则分两类：
- threshold：累计真实付款达到阈值发一次（按规则 id 一次性查重）
- per_amount：每满 N 元发一次（按「已发批次号」查重，可重复、只补新增批次）

查重状态存放在 user.plugin_datas["afdian"]["rewards"]，不新建表：
    {"granted": ["规则id", ...], "batches": {"规则id": 已发批次}, "history": [...]}
发放全程在 RewardEngine 的进程内锁里完成，避免绑定回调、webhook、命令
三个入口并发时重复发放；user.flush() 使用增量写回，不覆盖其他并发写入。
"""
import asyncio
import time
from dataclasses import dataclass, field

from nonebot.log import logger

from xme.plugins.commands.drift_bottle import __plugin_name__ as bottle_plugin_name
from xme.plugins.commands.xme_user.classes.user import User, coin_name
from xme.xmetools import dicttools
from xme.xmetools.afdiantools import AFDIAN_CLIENT, AfdianApiError, get_sponsor_profile

# plugin_datas 下的存储位置
PLUGIN_DATA_KEY = "afdian"
REWARD_DATA_KEY = "rewards"
GRANTED_KEY = "granted"
BATCHES_KEY = "batches"
HISTORY_KEY = "history"
HISTORY_LIMIT = 50

# 规则类型
RULE_THRESHOLD = "threshold"
RULE_PER_AMOUNT = "per_amount"
# 奖励类型
REWARD_COINS = "coins"
REWARD_BOTTLE_SKIN = "bottle_skin"


@dataclass(frozen=True)
class RewardSpec:
    """单个奖励内容：kind 决定用哪个发放函数，value/name 依 kind 解释。"""

    kind: str
    value: int = 0      # coins：星币数量
    name: str = ""      # bottle_skin：皮肤名（须存在于 drift_bottle CARD_SKINS）


@dataclass(frozen=True)
class RewardRule:
    """一条奖励规则；id 是查重键，发布后不要修改。"""

    id: str
    desc: str           # 给用户看的说明
    kind: str           # RULE_THRESHOLD / RULE_PER_AMOUNT
    target: float       # 阈值金额 / 每满多少元
    reward: RewardSpec


@dataclass
class PendingReward:
    """规划出的待发奖励；batch 仅 per_amount 规则使用。"""

    rule_id: str
    desc: str
    reward: RewardSpec
    batch: int | None = None


@dataclass
class ClaimResult:
    """一次结算的结果。"""

    granted: list[str] = field(default_factory=list)   # 本次发放描述
    total_amount: float = 0.0                          # 累计真实付款
    next_hints: list[str] = field(default_factory=list)  # 距下一档的提示
    bound: bool = True                                 # 是否已绑定爱发电账号


def _coins(amount: int) -> RewardSpec:
    return RewardSpec(kind=REWARD_COINS, value=amount)


def _skin(name: str) -> RewardSpec:
    return RewardSpec(kind=REWARD_BOTTLE_SKIN, name=name)


# ---- 奖励规则（改这里即可调整发放策略；id 一经使用不要改）----
# 皮肤名必须是 drift_bottle/tools/cards.py 中 CARD_SKINS 的键，否则渲染会回退默认皮肤。
REWARD_RULES: list[RewardRule] = [
    RewardRule(
        id="total_50_coins",
        desc="累计发电满 50 元",
        kind=RULE_THRESHOLD,
        target=50,
        reward=_skin("流浪地球"),
    ),
    # RewardRule(
    #     id="total_200_skin",
    #     desc="累计发电满 200 元",
    #     kind=RULE_THRESHOLD,
    #     target=200,
    #     reward=_skin("基础宇喵天枢"),
    # ),
    # RewardRule(
    #     id="per_100_coins",
    #     desc="每累计发电满 100 元",
    #     kind=RULE_PER_AMOUNT,
    #     target=100,
    #     reward=_coins(50),
    # ),
]


def plan_rewards(
    total_amount: float,
    rules: list[RewardRule] | None = None,
    granted: list[str] | None = None,
    batches: dict[str, int] | None = None,
) -> list[PendingReward]:
    """纯函数：算出按规则应发但尚未发放的奖励（不修改入参、不碰 IO）。

    Args:
        total_amount (float): 累计真实付款金额（兑换码计 0）
        rules (list[RewardRule] | None): 规则表，默认 REWARD_RULES
        granted (list[str] | None): 已发放的一次性规则 id
        batches (dict[str, int] | None): 已发放的 per_amount 批次号

    Returns:
        list[PendingReward]: 待发奖励，按规则表顺序
    """
    rules = REWARD_RULES if rules is None else rules
    granted = granted or []
    batches = batches or {}
    pending: list[PendingReward] = []
    for rule in rules:
        if rule.kind == RULE_THRESHOLD:
            if rule.id in granted or total_amount < rule.target:
                continue
            pending.append(PendingReward(rule_id=rule.id, desc=rule.desc, reward=rule.reward))
        elif rule.kind == RULE_PER_AMOUNT:
            if rule.target <= 0:
                continue
            reached = int(total_amount // rule.target)
            granted_batch = int(batches.get(rule.id, 0) or 0)
            for batch in range(granted_batch + 1, reached + 1):
                pending.append(PendingReward(
                    rule_id=rule.id,
                    desc=f"{rule.desc}（第 {batch} 次）",
                    reward=rule.reward,
                    batch=batch,
                ))
    return pending


def get_reward_state(user: User) -> dict:
    """读取用户的奖励查重状态（缺失时返回空结构，不写入）。"""
    state = dicttools.get_value(
        PLUGIN_DATA_KEY, REWARD_DATA_KEY, search_dict=user.plugin_datas, default=None,
    )
    if not isinstance(state, dict):
        state = {}
    return {
        GRANTED_KEY: list(state.get(GRANTED_KEY) or []),
        BATCHES_KEY: dict(state.get(BATCHES_KEY) or {}),
        HISTORY_KEY: list(state.get(HISTORY_KEY) or []),
    }


def _mark_granted(user: User, pending: PendingReward, desc: str) -> None:
    """把一条奖励写入查重状态与发放历史（只改内存）。"""
    state = get_reward_state(user)

    def update(old):
        old = old if isinstance(old, dict) else {}
        granted = list(old.get(GRANTED_KEY) or [])
        batches = dict(old.get(BATCHES_KEY) or {})
        history = list(old.get(HISTORY_KEY) or [])
        if pending.batch is None:
            if pending.rule_id not in granted:
                granted.append(pending.rule_id)
        else:
            batches[pending.rule_id] = pending.batch
        history.append({"rule": pending.rule_id, "desc": desc, "time": int(time.time())})
        return {
            GRANTED_KEY: granted,
            BATCHES_KEY: batches,
            HISTORY_KEY: history[-HISTORY_LIMIT:],
        }

    dicttools.set_value(
        PLUGIN_DATA_KEY, REWARD_DATA_KEY,
        search_dict=user.plugin_datas,
        set_method=update,
    )


def get_owned_skins(user: User) -> list[str]:
    """读取用户已拥有的漂流瓶皮肤列表。"""
    owned = dicttools.get_value(
        bottle_plugin_name, "custom_cards", search_dict=user.plugin_datas, default=[],
    )
    return list(owned) if isinstance(owned, list) else []


def grant_coins(user: User, spec: RewardSpec) -> str:
    """发放星币（只改内存），返回给用户看的描述。"""
    user.add_coins(spec.value)
    return f"{spec.value} {coin_name}"


def grant_bottle_skin(user: User, spec: RewardSpec) -> str:
    """发放漂流瓶皮肤到收藏（不自动选中），已拥有时返回「已拥有」描述。"""
    if spec.name in get_owned_skins(user):
        return f"漂流瓶皮肤「{spec.name}」（已拥有，跳过）"

    def append(old):
        return (list(old) if isinstance(old, list) else []) + [spec.name]

    dicttools.set_value(
        bottle_plugin_name, "custom_cards",
        search_dict=user.plugin_datas,
        set_method=append,
    )
    return f"漂流瓶皮肤「{spec.name}」"


# 奖励类型 -> 发放函数；新增奖励类型只需实现函数并在此登记
GRANT_REGISTRY = {
    REWARD_COINS: grant_coins,
    REWARD_BOTTLE_SKIN: grant_bottle_skin,
}


class RewardEngine:
    """结算引擎：进程内串行化「读状态 → 规划 → 发放 → 写库」。"""

    def __init__(self, rules: list[RewardRule] | None = None) -> None:
        self.rules = REWARD_RULES if rules is None else rules
        self._lock = asyncio.Lock()

    def _apply(self, user: User, total_amount: float) -> ClaimResult:
        """同步执行规划与发放（调用方须持锁），返回本次结果。"""
        result = ClaimResult(total_amount=round(total_amount, 2))
        state = get_reward_state(user)
        pending = plan_rewards(
            total_amount=total_amount,
            rules=self.rules,
            granted=state[GRANTED_KEY],
            batches=state[BATCHES_KEY],
        )
        for item in pending:
            grant = GRANT_REGISTRY.get(item.reward.kind)
            if grant is None:
                logger.warning(f"afdian 奖励规则 {item.rule_id} 的奖励类型 {item.reward.kind} 未注册，已跳过")
                continue
            desc = grant(user, item.reward)
            _mark_granted(user, item, desc)
            result.granted.append(f"{item.desc}：{desc}")
        result.next_hints = self._next_hints(user, total_amount)
        return result

    def _next_hints(self, user: User, total_amount: float) -> list[str]:
        """提示各规则距离下一档还差多少（只读）。"""
        state = get_reward_state(user)
        hints: list[str] = []
        for rule in self.rules:
            if rule.kind == RULE_THRESHOLD:
                if rule.id in state[GRANTED_KEY]:
                    continue
                remaining = rule.target - total_amount
                if remaining > 0:
                    hints.append(f"{rule.desc}（还差 {remaining:.2f} 元）")
            elif rule.kind == RULE_PER_AMOUNT and rule.target > 0:
                remaining = rule.target - (total_amount % rule.target)
                hints.append(f"{rule.desc}（再发电 {remaining:.2f} 元）")
        return hints

    async def claim(self, user: User, total_amount: float) -> ClaimResult:
        """持锁结算并写库：无待发奖励时不产生任何写入。"""
        async with self._lock:
            result = self._apply(user, total_amount)
            if result.granted:
                user.flush()
            return result


REWARD_ENGINE = RewardEngine()


async def settle_rewards(user: User, force: bool = False) -> ClaimResult:
    """结算指定用户的发电奖励（唯一入口：命令、绑定回调、webhook 共用）。

    Args:
        user (User): 已绑定 afdian_id 的用户
        force (bool): 是否绕过订单列表缓存（新订单到达时必须为 True）

    Returns:
        ClaimResult: 本次发放结果；未绑定或查询失败时返回 bound=False 的空结果
    """
    if not user.afdian_id:
        return ClaimResult(bound=False)
    try:
        profile = await get_sponsor_profile(AFDIAN_CLIENT, user.afdian_id, force=force)
    except AfdianApiError as e:
        logger.warning(f"afdian 奖励结算失败（{user.id}）：{e}")
        return ClaimResult(bound=True)
    except Exception as e:
        # 奖励结算不是关键路径：任何异常都只记日志，绝不打断绑定/通知流程
        logger.warning(f"afdian 奖励结算出现异常（{user.id}）：{e}")
        return ClaimResult(bound=True)
    total_amount = profile.total_amount if profile is not None else 0.0
    return await REWARD_ENGINE.claim(user, total_amount)
