"""DuckDuckGo 引擎实现（ddgs 库，免 key）。

ddgs 是同步库（内部 httpx），统一用 asyncio.to_thread 包成异步；实例不跨线程复用，
每次调用新建（构造很轻）。国内服务器直连不可达（DNS 污染），配置 proxy: True 走统一代理。

已实测（2026-09，ddgs 9.16.0 + 代理）：text() 返回 list[dict]，字段 title / href / body。
ddgs 没有结构化异常承诺，错误分类按异常消息关键词近似映射（第三方库限制，注释说明）。
"""
import asyncio

from nonebot.log import logger

from .types import (SearchError, SearchErrorKind, SearchResponse, SearchResult,
                    normalize_time_range)

# ddgs 的 timelimit 只认 d/w/m（无 year）；"限一年"取最接近的 m（宁窄勿滥）
_TIMELIMIT_MAP = {"day": "d", "week": "w", "month": "m", "year": "m"}


class DuckDuckGoEngine:
    """duckduckgo：免 key；proxy 传统一代理地址（None 直连）。"""

    name = "duckduckgo"

    def __init__(self, proxy: str | None = None, timeout: float = 15.0):
        self._proxy = proxy or None
        self._timeout = timeout

    async def search(self, query: str, *, max_results: int = 10,
                     time_range: str = "") -> SearchResponse:
        timelimit = _TIMELIMIT_MAP.get(normalize_time_range(time_range) or "")

        def _run() -> list[dict]:
            from ddgs import DDGS
            client = DDGS(proxy=self._proxy, timeout=self._timeout)
            return list(client.text(query, max_results=max_results, timelimit=timelimit) or [])

        try:
            rows = await asyncio.to_thread(_run)
        except Exception as ex:
            raise self._map_error(ex) from ex
        results = [SearchResult(
            title=str(item.get("title") or ""),
            url=str(item.get("href") or ""),
            content=str(item.get("body") or ""),
        ) for item in rows if isinstance(item, dict)]
        return SearchResponse(query=query, engine=self.name, results=results)

    @staticmethod
    def _map_error(ex: Exception) -> SearchError:
        # ddgs 异常无结构化分类（不同版本类名不稳定），按消息关键词近似映射；
        # 分类错了只影响冷却时长（回退行为不受影响）
        text = f"{type(ex).__name__}: {ex}".lower()
        if isinstance(ex, asyncio.TimeoutError) or isinstance(ex, TimeoutError) \
                or "timeout" in text or "timed out" in text:
            return SearchError(SearchErrorKind.TIMEOUT, str(ex), engine="duckduckgo")
        if "ratelimit" in text or "rate limit" in text or "429" in text or "403" in text:
            # DDG 风控（403 anomaly detection）与限流同性质：短冷却
            return SearchError(SearchErrorKind.RATE_LIMIT, str(ex), engine="duckduckgo")
        logger.debug(f"duckduckgo 未分类异常: {text}")
        return SearchError(SearchErrorKind.UNKNOWN, str(ex), engine="duckduckgo")
