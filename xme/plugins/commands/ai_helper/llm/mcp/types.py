"""MCP 接入的统一错误与 JSON-RPC 2.0 消息构造。"""
import json

# 客户端声明并沿用的协议版本（Streamable HTTP 传输在握手后以请求头回传）
MCP_PROTOCOL_VERSION = "2025-06-18"


class MCPError(Exception):
    """MCP 调用失败（含 server 名与阶段，供上层日志与降级判断）。"""

    def __init__(self, server: str, phase: str, message: str):
        super().__init__(f"[MCP:{server}] {phase}: {message}")
        self.server = server
        self.phase = phase   # initialize / tools/list / tools/call / transport
        self.message = message


def rpc_request(method: str, params: dict | None = None, req_id: int = 1) -> dict:
    """构造 JSON-RPC 2.0 请求。"""
    payload: dict = {"jsonrpc": "2.0", "id": req_id, "method": method}
    if params is not None:
        payload["params"] = params
    return payload


def rpc_notification(method: str, params: dict | None = None) -> dict:
    """构造 JSON-RPC 2.0 通知（无 id，不期待响应）。"""
    payload: dict = {"jsonrpc": "2.0", "method": method}
    if params is not None:
        payload["params"] = params
    return payload


def encode_message(message: dict) -> str:
    """把一条 JSON-RPC 消息编码为单行 JSON（stdio 传输按行分帧）。"""
    return json.dumps(message, ensure_ascii=False)


def extract_rpc_result(server: str, phase: str, response: dict) -> dict:
    """校验 JSON-RPC 响应并取出 result；error 或畸形响应抛 MCPError。"""
    if not isinstance(response, dict):
        raise MCPError(server, phase, f"响应不是 JSON 对象：{str(response)[:200]}")
    if "error" in response:
        err = response["error"] or {}
        raise MCPError(server, phase, f"JSON-RPC 错误 {err.get('code')}: {err.get('message')}")
    if "result" not in response:
        raise MCPError(server, phase, f"响应缺少 result：{str(response)[:200]}")
    return response["result"]
