"""DuckDuckGo 引擎实现（ddgs 库，免 key）。

ddgs 是同步库（内部 httpx），统一用 asyncio.to_thread 包成异步；实例不跨线程复用，
每次调用新建（构造很轻）。国内服务器直连不可达（DNS 污染），配置 proxy: True 走统一代理。

已实测（2026-09，ddgs 9.16.0 + 代理）：text() 返回 list[dict]，字段 title / href / body。
后端（backend）默认取常量里的可用集合，不用 ddgs 的 "auto"，并且**逐个后端单独调用、自己
轮询**（见 _search_backend）：auto 会轮番去撞 google/brave/yandex 等国内不通的站点，而 ddgs
内部的 FIRST_EXCEPTION 聚合在某个后端先报错时会丢弃其它后端已拿到的结果。名单见
constants.SEARCH_DDGS_BACKENDS，可用 keys.SEARCH_PROVIDERS 的 backend 字段覆盖。

ddgs 没有结构化异常承诺，错误分类按异常消息关键词近似映射（第三方库限制，注释说明）：
- "No results found." 只在「后端都没报错、只是没结果」时出现 → 按空结果返回（不是故障）；
- 真实错误会被 ddgs 原样抛出（如 RequestError: ... Connection reset by peer）。
"""
import asyncio

from nonebot.log import logger

from .base import looks_like_network_error, looks_like_timeout_error
from .types import (SearchError, SearchErrorKind, SearchResponse, SearchResult,
                    normalize_time_range)

# ddgs 的 timelimit 只认 d/w/m（无 year）；"限一年"取最接近的 m（宁窄勿滥）
_TIMELIMIT_MAP = {"day": "d", "week": "w", "month": "m", "year": "m"}


def _is_no_results(ex: Exception) -> bool:
    """是否「后端都没报错、只是没结果」——ddgs 对这种情况抛的固定文案。"""
    return "no results" in f"{ex}".lower()


class DuckDuckGoEngine:
    """duckduckgo：免 key；proxy 传统一代理地址（None 直连），backend 传 ddgs 后端名单。"""

    name = "duckduckgo"

    def __init__(self, proxy: str | None = None, timeout: float = 15.0,
                 backend: str | None = None):
        self._proxy = proxy or None
        self._timeout = timeout
        if not backend:
            from ..constants import SEARCH_DDGS_BACKENDS
            backend = SEARCH_DDGS_BACKENDS
        self._backend = backend

    async def search(self, query: str, *, max_results: int = 10,
                     time_range: str = "") -> SearchResponse:
        timelimit = _TIMELIMIT_MAP.get(normalize_time_range(time_range) or "")
        backends = [b.strip() for b in str(self._backend).split(",") if b.strip()] or ["auto"]
        loop = asyncio.get_running_loop()
        deadline = loop.time() + self._timeout      # 所有后端共享一个总预算
        last_error: SearchError | None = None
        reached_empty = False                       # 有后端可达但没结果（据此按空结果返回）
        for backend in backends:
            budget = deadline - loop.time()
            if budget <= 0.5:
                last_error = last_error or SearchError(
                    SearchErrorKind.TIMEOUT, f"ddgs 搜索总耗时超过 {self._timeout:g}s",
                    engine=self.name)
                break
            try:
                rows = await asyncio.wait_for(
                    asyncio.to_thread(self._search_backend, query, max_results, timelimit, backend),
                    timeout=budget)
            except asyncio.TimeoutError:
                last_error = SearchError(
                    SearchErrorKind.TIMEOUT,
                    f"后端 {backend} 在 {self._timeout:g}s 预算内未返回", engine=self.name)
                continue
            except Exception as ex:
                if _is_no_results(ex):
                    reached_empty = True    # 该后端可达、只是没结果：换下一个后端再试
                    continue
                last_error = self._map_error(ex)
                continue
            if rows:
                return self._build_response(query, rows)
            reached_empty = True
        # 有过「可达但没结果」的后端 → 按空结果返回（不算故障、不冷却、不触发跨引擎回退）；
        # 全部后端都是连接类失败才抛错，让 registry 短冷却后回退到下一个引擎
        if last_error is not None and not reached_empty:
            raise last_error
        return self._build_response(query, [])

    def _search_backend(self, query: str, max_results: int, timelimit: str | None,
                        backend: str) -> list[dict]:
        """单后端搜索（同步，供 to_thread 调用）。

        逐后端单独调用、不交给 ddgs 的 auto 聚合：ddgs 内部按
        ``wait(FIRST_EXCEPTION)`` 收集结果，某个后端先抛错时会**丢弃**其它后端
        已拿到的结果（实测多后端反而 0 结果），自己轮询各后端才可靠。
        """
        from ddgs import DDGS
        client = DDGS(proxy=self._proxy, timeout=self._timeout)
        return list(client.text(query, max_results=max_results,
                                timelimit=timelimit, backend=backend) or [])

    def _build_response(self, query: str, rows: list) -> SearchResponse:
        """把 ddgs 的行数据转成统一返回类型（非 dict 条目跳过）。"""
        results = [SearchResult(
            title=str(item.get("title") or ""),
            url=str(item.get("href") or ""),
            content=str(item.get("body") or ""),
        ) for item in rows if isinstance(item, dict)]
        return SearchResponse(query=query, engine=self.name, results=results)

    @staticmethod
    def _map_error(ex: Exception) -> SearchError:
        # 分类错了只影响冷却时长（回退行为不受影响）
        text = f"{type(ex).__name__}: {ex}".lower()
        if isinstance(ex, asyncio.TimeoutError) or isinstance(ex, TimeoutError) \
                or looks_like_timeout_error(ex):
            return SearchError(SearchErrorKind.TIMEOUT, str(ex), engine="duckduckgo")
        if "ratelimit" in text or "rate limit" in text or "429" in text or "403" in text:
            # DDG 风控（403 anomaly detection）与限流同性质：短冷却
            return SearchError(SearchErrorKind.RATE_LIMIT, str(ex), engine="duckduckgo")
        if looks_like_network_error(ex):
            # 连接被重置 / 代理不可用：属网络抖动，短冷却后重试，别按未知错误封十分钟
            return SearchError(SearchErrorKind.NETWORK, str(ex), engine="duckduckgo")
        logger.debug(f"duckduckgo 未分类异常: {text}")
        return SearchError(SearchErrorKind.UNKNOWN, str(ex), engine="duckduckgo")
