"""搜索引擎协议：所有引擎实现都满足同一接口，registry 据此按序调用与回退。"""
from typing import Protocol, runtime_checkable

from .types import SearchResponse

# 连接层失败的常见措辞：第三方 SDK（httpx / ddgs）把网络错误包成各自的异常类型，
# 版本间类名不稳定、消息也可能为空，只能按「类型名 + 消息」关键词近似判断。
# 判错的代价只是冷却时长（网络类 60s vs 未知 600s），不影响回退行为。
_NETWORK_KEYWORDS = (
    "connect", "connection", "network", "socket", "ssl", "proxy", "dns",
    "temporary failure", "name or service not known", "remote end closed",
    "incomplete read", "reset by peer", "os error", "requesterror", "clienterror",
)
# 超时类（httpx.ReadTimeout、ddgs.TimeoutException 等都不是标准 TimeoutError）
_TIMEOUT_KEYWORDS = ("timeout", "timed out")


def looks_like_timeout_error(ex: Exception) -> bool:
    """异常是否像超时（含各 SDK 自定义的超时异常类型）。"""
    text = f"{type(ex).__name__}: {ex}".lower()
    return any(k in text for k in _TIMEOUT_KEYWORDS)


def looks_like_network_error(ex: Exception) -> bool:
    """异常是否像连接层失败（用 network 分类做短冷却，而不是按未知错误长冷却）。"""
    return any(k in f"{type(ex).__name__}: {ex}".lower() for k in _NETWORK_KEYWORDS)


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
