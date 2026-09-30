"""MCP（Model Context Protocol）客户端：把 MCP server 的工具动态接入 AI 工具列表。

对上层只暴露 MCPClient / get_client / MCPError；传输细节（HTTP / stdio）在 transports。
"""
from .client import MCPClient, get_client
from .types import MCPError

__all__ = ["MCPClient", "get_client", "MCPError"]
