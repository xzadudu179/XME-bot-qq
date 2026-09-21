"""搜索引擎注册表：配置读取、惰性构造、进程内熔断与按序回退。

- **引擎名单与回退顺序**：`keys.py` 的 `SEARCH_PROVIDERS`（该文件不提交），dict 书写
  顺序即回退优先级，删除某项即禁用该引擎。缺配置时回落 tavily-only（保持老部署零改动）。
- **冷却常量**：`constants.py` 的 `SEARCH_*`（可提交，不含敏感信息）。
"""
from nonebot.log import logger

from .base import SearchEngine  # noqa: F401
from .types import SearchError, SearchErrorKind, SearchResponse  # noqa: F401

# 引擎名 → (实现类, 是否必须配置 api_key)
_ENGINE_TABLE: dict[str, tuple[type, bool]] = {}

_engines: dict[str, object] = {}            # 引擎名 → 已构造实例（惰性缓存）
_cooldown_until: dict[str, float] = {}      # 引擎名 → 冷却截止时间戳（进程内）


def _engine_table() -> dict[str, tuple[type, bool]]:
    """延迟填充引擎实现表（import 引擎模块可能拉起 SDK，避免在包 import 时发生）。"""
    if not _ENGINE_TABLE:
        from .brave import BraveEngine
        from .duckduckgo import DuckDuckGoEngine
        from .tavily import TavilyEngine
        _ENGINE_TABLE.update({
            "tavily": (TavilyEngine, True),
            "duckduckgo": (DuckDuckGoEngine, False),
            "brave": (BraveEngine, True),
        })
    return _ENGINE_TABLE


def _default_configs() -> dict:
    """keys 里没有 SEARCH_PROVIDERS 时的兜底：tavily-only（升级前的等价行为）。"""
    try:
        from keys import TAVILY_API_KEY
    except Exception:
        return {}
    return {"tavily": {"api_key": TAVILY_API_KEY}} if TAVILY_API_KEY else {}


def _load_engine_configs() -> dict:
    """读取 keys.SEARCH_PROVIDERS；文件里没有该配置或为空时回落 tavily-only。"""
    try:
        from keys import SEARCH_PROVIDERS
        if isinstance(SEARCH_PROVIDERS, dict) and SEARCH_PROVIDERS:
            return {str(k): dict(v or {}) for k, v in SEARCH_PROVIDERS.items()}
    except Exception:
        pass
    return _default_configs()


def _search_timeout() -> float:
    from ..constants import SEARCH_TIMEOUT
    return float(SEARCH_TIMEOUT)


def _proxy_of(cfg: dict) -> str | None:
    """引擎配置的 proxy 字段 → 实际代理地址：True 走 config 统一代理，字符串直用。"""
    value = cfg.get("proxy")
    if value is True:
        from xme.xmetools.reqtools import PROXY_URL
        return PROXY_URL
    if isinstance(value, str) and value:
        return value
    return None


def configured_engines() -> list[str]:
    """按回退顺序列出当前实际可用的引擎名（配置齐全、key 齐备）。"""
    engines: list[str] = []
    for name, cfg in _load_engine_configs().items():
        table = _engine_table()
        if name not in table:
            logger.warning(f"web_search 配置了未知引擎 {name}（可用：{'、'.join(table)}），已跳过")
            continue
        _, need_key = table[name]
        if need_key and not str(cfg.get("api_key") or "").strip():
            logger.debug(f"web_search 引擎 {name} 未配置 api_key，已跳过")
            continue
        engines.append(name)
    return engines


def get_engine(name: str):
    """按名取引擎实例（惰性构造并缓存）；配置不齐全返回 None。"""
    if name in _engines:
        return _engines[name]
    table = _engine_table()
    if name not in table:
        return None
    cfg = _load_engine_configs().get(name) or {}
    cls, _ = table[name]
    timeout = float(cfg.get("timeout") or _search_timeout())
    if name == "tavily":
        engine = cls(api_key=str(cfg.get("api_key") or ""))
    elif name == "duckduckgo":
        # backend 可按部署覆盖 ddgs 后端名单（缺省用 constants.SEARCH_DDGS_BACKENDS）
        engine = cls(proxy=_proxy_of(cfg), timeout=timeout, backend=cfg.get("backend"))
    elif name == "brave":
        engine = cls(api_key=str(cfg.get("api_key") or ""), proxy=_proxy_of(cfg), timeout=timeout)
    else:
        return None
    _engines[name] = engine
    return engine


def reset_state() -> None:
    """清空实例缓存与冷却状态（测试用；生产进程内无需调用）。"""
    _engines.clear()
    _cooldown_until.clear()


# ---------- 熔断冷却 ----------

def _cooldown_seconds(kind: str) -> float:
    """错误类别 → 冷却秒数（constants 单点配置）。"""
    from .. import constants
    if kind == SearchErrorKind.QUOTA:
        return float(constants.SEARCH_COOLDOWN_QUOTA)
    if kind == SearchErrorKind.AUTH:
        return float(constants.SEARCH_COOLDOWN_AUTH)
    if kind in (SearchErrorKind.RATE_LIMIT, SearchErrorKind.TIMEOUT, SearchErrorKind.NETWORK):
        return float(constants.SEARCH_COOLDOWN_RETRYABLE)
    return float(constants.SEARCH_COOLDOWN_UNKNOWN)


def _in_cooldown(name: str, now: float) -> bool:
    until = _cooldown_until.get(name)
    return until is not None and now < until


def _set_cooldown(name: str, kind: str, now: float) -> None:
    seconds = _cooldown_seconds(kind)
    _cooldown_until[name] = now + seconds


# ---------- 按序回退入口 ----------

async def search_with_fallback(query: str, *, max_results: int = 10,
                               time_range: str = "") -> SearchResponse:
    """按配置顺序逐个引擎尝试，失败（含冷却中的引擎）自动换下一个。

    - 冷却中的引擎直接跳过（额度用完后不浪费往返，冷却结束再自动探路恢复）；
    - 空结果不算失败（换引擎搜同样的词大概率也空），原样返回；
    - 全部引擎失败时抛最后一个 SearchError（engine 为实际最末尝试的引擎）。
    """
    import time as _time
    names = configured_engines()
    if not names:
        raise SearchError(SearchErrorKind.UNKNOWN,
                          "没有任何可用的搜索引擎配置（keys.SEARCH_PROVIDERS）")
    last_error: SearchError | None = None
    for name in names:
        now = _time.monotonic()
        if _in_cooldown(name, now):
            logger.debug(f"web_search 引擎 {name} 冷却中，跳过")
            continue
        engine = get_engine(name)
        if engine is None:
            continue
        try:
            response = await engine.search(query, max_results=max_results, time_range=time_range)
        except SearchError as ex:
            if not ex.engine:      # 实现忘填引擎名时补上，保证错误消息可定位
                ex.engine = name
            last_error = ex
            _set_cooldown(name, ex.kind, _time.monotonic())
            remaining = [n for n in names[names.index(name) + 1:] if not _in_cooldown(n, _time.monotonic())]
            logger.warning(
                f"web_search 引擎 {name} 失败({ex.kind})：{ex.message}"
                + (f"，回退到 {remaining[0]}" if remaining else "，已无更多引擎")
            )
            continue
        except Exception as ex:   # 引擎实现漏分类的兜底（base.py 契约由这里强制收口）
            last_error = SearchError(SearchErrorKind.UNKNOWN, f"{type(ex).__name__}: {ex}", engine=name)
            _set_cooldown(name, last_error.kind, _time.monotonic())
            logger.opt(exception=ex).warning(f"web_search 引擎 {name} 未分类异常，按 unknown 冷却")
            continue
        logger.info(f"web_search 使用 {name}，{len(response.results)} 条结果（query: {query[:50]}）")
        return response
    raise last_error or SearchError(SearchErrorKind.UNKNOWN, "所有搜索引擎均不可用")
