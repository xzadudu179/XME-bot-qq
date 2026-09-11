# some are made by Deepseek-v4-flash-vison-exp at Deepseek Harness
"""Provider 协议定义。

上层只依赖本协议与 types 里的统一数据模型；具体传输实现
（openai_client 的 httpx 兼容客户端、Phase 2 可能补的 zai SDK 轮询）
都藏在 provider 内部，差异不外泄。
"""
from typing import Protocol, runtime_checkable

from .types import ChatResult


@runtime_checkable
class LLMProvider(Protocol):
    """一次对话调用能力（含工具与思考开关）。"""

    name: str          # provider 名（配置键，如 "glm"）
    transport: str     # 传输实现标识（如 "openai_http" / "zai_sdk_async"）

    async def chat(self, messages: list, *, model: str, tools: list | None = None,
                   temperature: float | None = None,
                   thinking: bool = False) -> ChatResult:
        """发起一次对话调用：返回统一结果，失败抛 LLMError。"""
        ...

    async def close(self) -> None:
        """释放底层连接资源。"""
        ...
