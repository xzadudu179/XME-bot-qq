"""Tavily 引擎实现（官方 SDK，OpenAI 之外的搜索 API）。

tavily 状态码与 SDK 异常的对应关系（见 tavily/errors.py 与 async_tavily.py 的处理）：
429 → UsageLimitExceededError（限流）；403/432/433 → ForbiddenError（额度用完/被禁）；
401 → InvalidAPIKeyError；400 → BadRequestError；另有 SDK 自定义 TimeoutError。
"""
import asyncio

from tavily import AsyncTavilyClient

from .types import (SearchError, SearchErrorKind, SearchResponse, SearchResult,
                    normalize_time_range)


def map_tavily_error(ex: Exception, engine: str = "tavily") -> SearchError:
    """把 tavily SDK 异常映射为统一 SearchError。"""
    from tavily.errors import (BadRequestError, ForbiddenError, InvalidAPIKeyError,
                               MissingAPIKeyError, UsageLimitExceededError)
    try:
        from tavily.errors import TimeoutError as TavilyTimeoutError
    except ImportError:      # 老版本 SDK 没有 TimeoutError，用名字兜底
        TavilyTimeoutError = ()
    if isinstance(ex, SearchError):
        return ex
    if isinstance(ex, asyncio.TimeoutError) or isinstance(ex, TimeoutError):
        return SearchError(SearchErrorKind.TIMEOUT, str(ex), engine=engine)
    if TavilyTimeoutError and isinstance(ex, TavilyTimeoutError):
        return SearchError(SearchErrorKind.TIMEOUT, str(ex), engine=engine)
    if isinstance(ex, (InvalidAPIKeyError, MissingAPIKeyError)):
        return SearchError(SearchErrorKind.AUTH, str(ex), engine=engine)
    if isinstance(ex, ForbiddenError):   # 403/432/433：额度用完或账号被禁，长冷却后重试探路
        return SearchError(SearchErrorKind.QUOTA, str(ex), engine=engine)
    if isinstance(ex, UsageLimitExceededError):  # 429：瞬时限流，短冷却
        return SearchError(SearchErrorKind.RATE_LIMIT, str(ex), engine=engine)
    return SearchError(SearchErrorKind.UNKNOWN, f"{type(ex).__name__}: {ex}", engine=engine)


class TavilyEngine:
    """tavily：需要 api_key；time_range 原生支持 day/week/month/year，直传。"""

    name = "tavily"

    def __init__(self, api_key: str):
        self._client = AsyncTavilyClient(api_key=api_key)

    async def search(self, query: str, *, max_results: int = 10,
                     time_range: str = "") -> SearchResponse:
        try:
            data = await self._client.search(
                query=query,
                max_results=max_results,
                search_depth="basic",
                time_range=normalize_time_range(time_range),
            )
        except Exception as ex:
            raise map_tavily_error(ex, self.name) from ex
        items = data.get("results") or [] if isinstance(data, dict) else []
        results = [SearchResult(
            title=str(item.get("title") or ""),
            url=str(item.get("url") or ""),
            content=str(item.get("content") or ""),
            score=float(item.get("score") or 0.0),
        ) for item in items if isinstance(item, dict)]
        return SearchResponse(query=query, engine=self.name, results=results, raw=data)
