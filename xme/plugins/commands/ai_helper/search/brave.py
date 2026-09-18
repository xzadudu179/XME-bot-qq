"""Brave Search 引擎实现（aiohttp 直连 REST，需 api_key）。

API：GET https://api.search.brave.com/res/v1/web/search，
认证头 X-Subscription-Token；freshness 参数 pd/pw/pm/py 与通用 day/week/month/year 一一对应。
免费层 2000 次/月（brave.com/search/api 注册）。
状态码：401/403 → 鉴权问题；429 → 限流或月配额用完（按响应消息区分，quota 字样按额度处理）。
"""
import asyncio

import aiohttp

from .types import (SearchError, SearchErrorKind, SearchResponse, SearchResult,
                    normalize_time_range)

_API_URL = "https://api.search.brave.com/res/v1/web/search"
_FRESHNESS_MAP = {"day": "pd", "week": "pw", "month": "pm", "year": "py"}


class BraveEngine:
    """brave：需要 api_key；proxy 传统一代理地址（None 直连）。"""

    name = "brave"

    def __init__(self, api_key: str, proxy: str | None = None, timeout: float = 15.0):
        self._api_key = api_key
        self._proxy = proxy or None
        self._timeout = timeout

    async def search(self, query: str, *, max_results: int = 10,
                     time_range: str = "") -> SearchResponse:
        params = {"q": query, "count": max(1, min(int(max_results), 20))}
        freshness = _FRESHNESS_MAP.get(normalize_time_range(time_range) or "")
        if freshness:
            params["freshness"] = freshness
        headers = {"Accept": "application/json", "X-Subscription-Token": self._api_key}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    _API_URL, params=params, headers=headers, proxy=self._proxy,
                    timeout=aiohttp.ClientTimeout(total=self._timeout),
                ) as resp:
                    body = await resp.text()
                    if resp.status != 200:
                        raise self._map_status(resp.status, body)
                    data = await resp.json(content_type=None)
        except SearchError:
            raise
        except (asyncio.TimeoutError, TimeoutError) as ex:
            raise SearchError(SearchErrorKind.TIMEOUT, str(ex), engine=self.name) from ex
        except aiohttp.ClientError as ex:
            raise SearchError(SearchErrorKind.NETWORK, str(ex), engine=self.name) from ex
        except OSError as ex:   # DNS 解析失败等连接层问题
            raise SearchError(SearchErrorKind.NETWORK, str(ex), engine=self.name) from ex
        items = ((data or {}).get("web") or {}).get("results") or []
        results = [SearchResult(
            title=str(item.get("title") or ""),
            url=str(item.get("url") or ""),
            content=str(item.get("description") or ""),
        ) for item in items if isinstance(item, dict)]
        return SearchResponse(query=query, engine=self.name, results=results, raw=data)

    @staticmethod
    def _map_status(status: int, body: str) -> SearchError:
        text = (body or "")[:300].lower()
        kind = SearchErrorKind.UNKNOWN
        if status in (401, 403):
            kind = SearchErrorKind.AUTH
        elif status == 429:
            # 429 既可能是瞬时限流也可能是月配额用完：按响应消息区分，
            # 区分不了按限流处理（短冷却，多撞几次可接受）
            kind = SearchErrorKind.QUOTA if "quota" in text or "monthly" in text \
                else SearchErrorKind.RATE_LIMIT
        elif status == 422:
            kind = SearchErrorKind.UNKNOWN   # 参数问题（query 空等），换引擎重试
        return SearchError(kind, text or f"HTTP {status}", engine="brave", status=status)
