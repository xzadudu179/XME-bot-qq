"""多搜索引擎抽象层：统一返回类型 + 按配置顺序自动回退。

对外入口：
    from ..search import search_with_fallback
    resp = await search_with_fallback("query", max_results=10, time_range="year")
    # resp: SearchResponse(query, engine, results=[SearchResult(title, url, content, score)])

引擎名单与回退顺序在 keys.SEARCH_PROVIDERS（dict 书写顺序即优先级），
冷却常量在 constants.SEARCH_*。新增引擎：本包内实现 SearchEngine 协议 + registry._engine_table 加一行。
"""
from .base import SearchEngine            # noqa: F401
from .registry import (configured_engines, get_engine, reset_state,  # noqa: F401
                       search_with_fallback)
from .types import (SearchError, SearchErrorKind, SearchResponse,      # noqa: F401
                    SearchResult, normalize_time_range)
