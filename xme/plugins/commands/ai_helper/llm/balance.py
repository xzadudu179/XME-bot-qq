"""Provider 余额查询抽象层。

把各服务商「账户余额」端点的差异收敛到这里：上层（status 等）只处理
ProviderBalance 与 format_balance，对接不上的 provider 余额为 None
（展示层据此显示「未知」）。新增服务商只需在 _BALANCE_FETCHERS 注册
一个查询器，再在 _DOMAIN_DEFAULTS 补域名默认映射（或由用户在 keys.py
的 provider 配置里写 billing 字段指定）。
"""
import asyncio
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit

import httpx

from .registry import get_provider_config, list_provider_names

# 单个余额端点的请求超时秒数（轻接口，快速失败回退「未知」，不拖慢 .stats）
BALANCE_TIMEOUT = 10.0
# 余额结果缓存秒数：.stats 可能被频繁调用，避免反复请求各余额端点
BALANCE_CACHE_TTL = 300.0

# keys.py provider 配置里 billing 字段的「显式禁用」取值
_BILLING_OFF = "none"

# 币种符号（未收录的币种按「金额 + 币种代码」展示）
_CURRENCY_SYMBOLS = {"CNY": "¥", "USD": "$"}


@dataclass
class ProviderBalance:
    """一个 provider 的账户余额信息（查不到的字段为 None，balance=None 即「未知」）。"""

    provider: str
    balance: float | None = None        # 剩余金额
    currency: str | None = None         # 币种代码（CNY / USD / ...）
    total_granted: float | None = None  # 累计授予额度（充值 + 赠送）
    total_used: float | None = None     # 累计消耗


def format_balance(data: ProviderBalance) -> str:
    """把余额信息格式化为展示文本；balance 为 None 时显示「未知」。"""
    if data.balance is None:
        return "未知"
    code = (data.currency or "").upper()
    amount = f"{data.balance:,.2f}"
    symbol = _CURRENCY_SYMBOLS.get(code)
    if symbol:
        return f"{symbol}{amount}"
    return f"{amount} {code}" if code else amount


async def _get_json(url: str, api_key: str) -> dict:
    """带 Bearer 鉴权的余额端点 GET（非 2xx / JSON 解析失败抛异常，由上层回退未知）。"""
    async with httpx.AsyncClient(timeout=BALANCE_TIMEOUT) as client:
        resp = await client.get(url, headers={"Authorization": f"Bearer {api_key}"})
        resp.raise_for_status()
        data = resp.json()
    return data if isinstance(data, dict) else {}


def _to_float(value) -> float | None:
    """余额接口的金额多为字符串，安全转 float（缺失 / 非法回 None）。"""
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


async def _fetch_deepseek(provider: str, base_url: str, api_key: str) -> ProviderBalance:
    """DeepSeek 官方余额端点：GET {站点根}/user/balance，取第一组余额信息。"""
    parts = urlsplit(base_url)
    origin = f"{parts.scheme}://{parts.netloc}"
    data = await _get_json(f"{origin}/user/balance", api_key)
    infos = data.get("balance_infos")
    info = infos[0] if isinstance(infos, list) and infos else {}
    return ProviderBalance(
        provider=provider,
        balance=_to_float(info.get("total_balance")),
        currency=info.get("currency") or None,
        total_granted=_to_float(info.get("granted_balance")),
    )


async def _fetch_moonshot(provider: str, base_url: str, api_key: str) -> ProviderBalance:
    """Moonshot 官方余额端点：GET {base_url}/users/me/balance（平台按 CNY 计价）。"""
    data = await _get_json(f"{base_url.rstrip('/')}/users/me/balance", api_key)
    info = data.get("data") or {}
    balance = _to_float(info.get("available_balance"))
    return ProviderBalance(
        provider=provider,
        balance=balance,
        currency="CNY" if balance is not None else None,
        total_granted=_to_float(info.get("voucher_credits")),
    )


async def _fetch_one_api(provider: str, base_url: str, api_key: str) -> ProviderBalance:
    """one-api 系中转的通用端点：subscription 给总额度、usage 给已用（美分），差额即余额。"""
    base = base_url.rstrip("/")
    now = datetime.now(timezone.utc)
    # usage 的统计窗口要盖住额度生效期，向前多取 90 天、向后多取 1 天避免时区边界漏算
    query = (f"start_date={(now - timedelta(days=90)):%Y-%m-%d}"
             f"&end_date={(now + timedelta(days=1)):%Y-%m-%d}")
    sub = await _get_json(f"{base}/dashboard/billing/subscription", api_key)
    usage = await _get_json(f"{base}/dashboard/billing/usage?{query}", api_key)
    granted = _to_float(sub.get("hard_limit_usd"))
    used = _to_float(usage.get("total_usage"))
    if granted is None or used is None:
        # 任一端点缺数据都宁可不报数（报大了会误导充值判断）
        return ProviderBalance(provider=provider)
    return ProviderBalance(
        provider=provider,
        balance=granted - used / 100,
        currency="USD",
        total_granted=granted,
        total_used=used / 100,
    )


# 余额查询器注册表（kind → 实现）
_BALANCE_FETCHERS = {
    "deepseek": _fetch_deepseek,
    "moonshot": _fetch_moonshot,
    "one_api": _fetch_one_api,
}

# 域名 → 默认查询器：只收录官方确定存在的接口；
# 中转站是否为 one-api 系因部署而异，让用户在 keys.py 里显式配 billing
_DOMAIN_DEFAULTS = {
    "api.deepseek.com": "deepseek",
    "api.moonshot.cn": "moonshot",
}

# 其余 provider 保持「未知」的调研结论（2026-10 逐家实测 + 官方文档核对）：
# - glm / minimax / xai：无 API key 鉴权的余额端点（候选路径实测 404，文档亦无）；
#   xai 需走代理可达，但 /v1/api-keys、/v1/usage 同样 404
# - doubao(火山方舟)：推理 API 无余额端点，计费查询（QueryBalanceAcct）需火山 AK/SK
#   签名，属 keys.py 之外另一套凭证
# - local 等自建端点：无账户概念
# - 未开启计费模拟的 one-api 系中转（如 qwen 实测 404）：可在站点支持后配 billing="one_api"


def _billing_kind(cfg: dict) -> str | None:
    """决定 provider 用哪个查询器：keys.py 的 billing 字段优先，否则按域名默认映射。"""
    kind = str(cfg.get("billing") or "")
    if kind:
        return None if kind == _BILLING_OFF else kind
    host = urlsplit(str(cfg.get("base_url") or "")).netloc
    return _DOMAIN_DEFAULTS.get(host)


# 查询结果缓存：provider 名 → (写入时间, 结果)
_balance_cache: dict[str, tuple[float, ProviderBalance]] = {}


async def _query_one(name: str) -> ProviderBalance:
    """查单个 provider 的余额；无对接方式 / 缺配置时直接返回未知。"""
    cfg = get_provider_config(name)
    fetcher = _BALANCE_FETCHERS.get(_billing_kind(cfg) or "")
    if fetcher is None or not cfg.get("api_key") or not cfg.get("base_url"):
        return ProviderBalance(provider=name)
    return await fetcher(name, str(cfg["base_url"]), str(cfg["api_key"]))


async def get_providers_balance() -> list[ProviderBalance]:
    """并发查询所有已配置 provider 的余额（TTL 缓存内直接复用）。

    单家失败 / 超时 / 未对接 → balance=None（「未知」），不影响其余 provider；
    返回顺序与 keys.py 的 LLM_PROVIDERS 配置顺序一致。
    """
    names = list_provider_names()
    now = time.time()
    results: dict[str, ProviderBalance] = {}
    pending: list[str] = []
    for name in names:
        cached = _balance_cache.get(name)
        if cached and now - cached[0] < BALANCE_CACHE_TTL:
            results[name] = cached[1]
        else:
            pending.append(name)
    if pending:
        fetched = await asyncio.gather(*(_query_one(n) for n in pending),
                                       return_exceptions=True)
        for name, item in zip(pending, fetched):
            # 异常（网络 / 鉴权 / 端点不符）与正常结果统一落缓存，避免失败方被高频重试
            data = item if isinstance(item, ProviderBalance) else ProviderBalance(provider=name)
            _balance_cache[name] = (now, data)
            results[name] = data
    return [results[name] for name in names]


def total_by_currency(balances: list[ProviderBalance]) -> dict[str, float]:
    """按币种汇总已知余额（balance=None 的 provider 跳过；币种未知的并入 "" 组）。

    不同币种不做汇率换算，分币种各自求和，避免报出一个失真的总额。
    """
    totals: dict[str, float] = {}
    for item in balances:
        if item.balance is None:
            continue
        code = (item.currency or "").upper()
        totals[code] = totals.get(code, 0.0) + item.balance
    return totals


async def get_total_balance() -> dict[str, float]:
    """所有 provider 的总余额，按币种分组（复用 get_providers_balance 的 TTL 缓存）。

    没有任何可查余额时返回空 dict。
    """
    return total_by_currency(await get_providers_balance())


def format_total_balance(totals: dict[str, float]) -> str:
    """把币种汇总格式化为展示文本（多币种用 + 连接；空 dict 显示「未知」）。"""
    if not totals:
        return "未知"
    parts = []
    for code, amount in totals.items():
        symbol = _CURRENCY_SYMBOLS.get(code)
        parts.append(f"{symbol}{amount:,.2f}" if symbol else f"{amount:,.2f} {code}".strip())
    return " + ".join(parts)
