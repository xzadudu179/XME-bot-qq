"""搜索引擎协议：所有引擎实现都满足同一接口，registry 据此按序调用与回退。"""
from typing import Protocol, runtime_checkable

from .types import SearchResponse


@runtime_checkable
class SearchEngine(Protocol):
    """一个可用的搜索引擎。

    契约（由 registry 在调用侧强制，实现也应自觉遵守）：
    - search 正常时返回 SearchResponse（results 可为空列表，空结果不算失败、不触发回退）；
    - 失败时必须抛 SearchError（kind 分类决定冷却时长），不允许抛其他异常类型——
      registry 仍会兜底把任意异常转成 UNKNOWN，但精确分类能让回退更聪明。
    """

    name: str

    async def search(self, query: str, *, max_results: int = 10,
                     time_range: str = "") -> SearchResponse:
        """按通用参数搜索。time_range 为通用枚举 day/week/month/year（""=不限）。"""
        ...
