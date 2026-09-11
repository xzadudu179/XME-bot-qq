# some are made by Deepseek-v4-flash-vison-exp at Deepseek Harness
"""多 Provider 抽象层：统一 OpenAI Chat Completions 协议。

- types.py          统一数据模型（ChatResult / Usage / ToolCall / LLMError）
- base.py           provider 协议
- openai_client.py  httpx 实现的兼容客户端（流式 + 工具分片 + 错误分类）
- registry.py       provider 注册表 / 模型目录 / 能力配置（配置单点）

上层（agent / 工具）只依赖本包导出的符号，不直接接触任何供应商 SDK。
"""
from .types import (  # noqa: F401
    ChatResult, LLMError, LLMErrorKind, ToolCall, Usage, message_to_dict,
)
from .openai_client import OpenAICompatProvider  # noqa: F401
from .registry import (  # noqa: F401
    close_all, default_alias, get_capability, get_provider,
    list_model_aliases, resolve_model,
)
