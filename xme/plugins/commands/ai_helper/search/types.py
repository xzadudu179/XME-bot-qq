"""搜索引擎抽象层的统一数据模型。

把各家搜索引擎（tavily / duckduckgo / brave ...）的请求响应差异收敛到这里：
上层（functions/web.py 的 web_search / registry）只处理 SearchResponse / SearchResult /
SearchError，不再直接接触各引擎 SDK 的私有结构。
"""
from dataclasses import dataclass, field


# 错误分类：registry 据此决定冷却时长与是否回退到下一个引擎
# （分类范式与 llm/types.py 的 LLMErrorKind 一致）
class SearchErrorKind:
    QUOTA = "quota"            # 额度/套餐用完（tavily 432、brave 月配额）→ 长冷却
    AUTH = "auth"              # key 无效/缺失 → 本进程内不再使用
    RATE_LIMIT = "rate_limit"  # 限流 → 短冷却
    TIMEOUT = "timeout"        # 超时 → 短冷却
    NETWORK = "network"        # 连接失败/DNS → 短冷却
    UNKNOWN = "unknown"        # 其他 → 中等冷却


class SearchError(Exception):
    """统一的搜索引擎调用异常（含分类、引擎原始状态码与引擎名）。"""

    def __init__(self, kind: str, message: str, *, code: str | int | None = None,
                 engine: str = "", status: int | None = None):
        super().__init__(message)
        self.kind = kind
        self.message = message
        self.code = code
        self.engine = engine
        self.status = status

    def __str__(self) -> str:
        parts = [f"[{self.engine or 'search'}]", self.kind]
        if self.status is not None:
            parts.append(f"http={self.status}")
        if self.code is not None:
            parts.append(f"code={self.code}")
        return " ".join(parts) + f": {self.message}"


# time_range 的通用取值（工具层对外口径）；各引擎在实现里映射成自家参数
TIME_RANGES = ("day", "week", "month", "year")


def normalize_time_range(time_range: str) -> str | None:
    """把工具层传入的 time_range 归一化为通用枚举值；空串/未知值 → None（不限定）。"""
    value = (time_range or "").strip().lower()
    return value if value in TIME_RANGES else None


@dataclass
class SearchResult:
    """单条搜索结果（各引擎字段差异在这里抹平）。"""

    title: str = ""
    url: str = ""
    content: str = ""
    score: float = 0.0      # 相关度（tavily 有；其他引擎缺省 0.0）


@dataclass
class SearchResponse:
    """一次搜索调用的统一结果。"""

    query: str = ""
    engine: str = ""
    results: list[SearchResult] = field(default_factory=list)
    raw: object = None       # 原始响应（排障用，不参与业务逻辑）
