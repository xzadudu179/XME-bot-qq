# some are made by Deepseek-v4-flash-vison-exp at Deepseek Harness
"""多 Provider 抽象层的统一数据模型。

把各供应商（GLM / 任意 OpenAI 兼容端点）的请求响应差异收敛到这里：
上层（agent / 工具）只处理 ChatResult / Usage / ToolCall / LLMError，
不再直接接触 SDK 对象或 provider 私有字段。
"""
from dataclasses import dataclass, field


# 错误分类：上层据此决定重试/兜底策略（替代原先对 SDK 异常与 "1210" 字符串的依赖）
class LLMErrorKind:
    MEDIA_INVALID = "media_invalid"    # 媒体输入解析失败（GLM 1210 等）→ 可剥离媒体后重试
    BAD_REQUEST = "bad_request"        # 请求非法（参数/结构错误）→ 不可重试
    AUTH = "auth"                      # 鉴权失败 → 不可重试
    RATE_LIMIT = "rate_limit"          # 限流 → 可重试
    TIMEOUT = "timeout"                # 超时/连接失败 → 可重试
    SERVER = "server"                  # 服务端错误 → 可重试
    UNKNOWN = "unknown"                # 其他 → 由调用方决定
    # 可重试集合（供上层判断）
    RETRYABLE = (RATE_LIMIT, TIMEOUT, SERVER)


class LLMError(Exception):
    """统一的大模型调用异常（含分类、供应商原始错误码与提供方名）。"""

    def __init__(self, kind: str, message: str, *, code: str | int | None = None,
                 provider: str = "", status: int | None = None):
        super().__init__(message)
        self.kind = kind
        self.message = message
        self.code = code
        self.provider = provider
        self.status = status

    def __str__(self) -> str:
        parts = [f"[{self.provider or 'llm'}]", self.kind]
        if self.code is not None:
            parts.append(f"code={self.code}")
        if self.status is not None:
            parts.append(f"http={self.status}")
        return " ".join(parts) + f": {self.message}"


@dataclass
class ToolCall:
    """一次工具调用（arguments 保持 JSON 字符串，与 OpenAI 协议一致）。"""

    id: str
    name: str
    arguments: str = "{}"


@dataclass
class Usage:
    """一次调用的用量（不同 provider 缺字段时按 0 处理）。"""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cached_tokens: int = 0

    def billable_tokens(self, cache_ratio: float = 0.25) -> float:
        """折算为计费 tokens：缓存命中的部分按 cache_ratio 计价（其余按全价）。

        cache_ratio 由模型配置提供（LLM_MODELS 的 cache_credit_ratio）——
        各家缓存折扣差异很大：GLM 命中部分按 0.25 计，DeepSeek 仅按 0.02 计。
        """
        return self.total_tokens - self.cached_tokens * (1 - cache_ratio)


@dataclass
class ChatResult:
    """一次对话调用的统一结果。"""

    text: str = ""
    reasoning: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    usage: Usage = field(default_factory=Usage)
    finish_reason: str = ""
    provider: str = ""
    model: str = ""
    raw: object = None       # 原始响应（排障用，不参与业务逻辑）

    @property
    def has_tool_calls(self) -> bool:
        return bool(self.tool_calls)


def message_to_dict(result: ChatResult) -> dict:
    """把结果还原为可回填上下文的 assistant 消息（OpenAI 协议形态）。

    保留下来的字段与各家 provider 的"原样回传"要求一致：
    有 reasoning 时必须随 tool 结果一并回传，否则模型可能报错或丢失思考连贯性。
    """
    msg: dict = {"role": "assistant", "content": result.text or ""}
    if result.reasoning:
        msg["reasoning_content"] = result.reasoning
    if result.tool_calls:
        msg["tool_calls"] = [
            {"id": tc.id, "type": "function",
             "function": {"name": tc.name, "arguments": tc.arguments}}
            for tc in result.tool_calls
        ]
    return msg
