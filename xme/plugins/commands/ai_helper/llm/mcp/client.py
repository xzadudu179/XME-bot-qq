"""MCP 客户端：握手、tools/list、tools/call，与跨轮复用的 server 管理器。

只依赖传输层的 send()，与传输方式（HTTP / stdio）无关。
"""
import asyncio

from .transports import HttpTransport, StdioTransport
from .types import MCP_PROTOCOL_VERSION, MCPError

_CLIENT_INFO = {"name": "xme-ai-helper", "version": "1.0"}


class MCPClient:
    """单个 MCP server 的客户端：懒握手，会话/进程异常自动重置一次。"""

    def __init__(self, name: str, config: dict, timeout: float = 15.0):
        self.name = name
        self._timeout = timeout
        self._transport = _build_transport(name, config, timeout)
        self._initialized = False
        self._lock = asyncio.Lock()   # 握手与重试互斥，避免并发重复 initialize

    async def _initialize(self) -> None:
        result = await self._transport.send("initialize", {
            "protocolVersion": MCP_PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": _CLIENT_INFO,
        })
        if result is None:
            raise MCPError(self.name, "initialize", "服务器未返回 InitializeResult")
        # 通知服务器握手完成（202/空响应均接受；个别实现直接关流也不影响后续请求）
        try:
            await self._transport.send("notifications/initialized", {}, notify=True)
        except MCPError:
            pass
        self._initialized = True

    async def _ensure_ready(self) -> None:
        async with self._lock:
            if not self._initialized:
                await self._initialize()

    async def list_tools(self) -> list[dict]:
        """返回 server 工具列表（[{name, description, inputSchema}, ...]），失败抛 MCPError。"""
        await self._ensure_ready()
        result = await self._send_rpc("tools/list", {})
        return list(result.get("tools") or [])

    async def call_tool(self, tool_name: str, arguments: dict | None = None) -> str:
        """调用 server 工具，拼接 text content 返回；isError 抛 MCPError（会话仍有效）。"""
        await self._ensure_ready()
        result = await self._send_rpc("tools/call", {
            "name": tool_name, "arguments": arguments or {}})
        if result.get("isError"):
            raise MCPError(self.name, "tools/call", _collect_text(result) or "工具返回错误")
        return _collect_text(result)

    async def _send_rpc(self, method: str, params: dict) -> dict:
        try:
            return await self._transport.send(method, params)
        except MCPError as ex:
            # 会话过期（HTTP 404）/ 进程死亡（stdio）：重置 → 重新握手 → 重试一次；
            # 应用层错误（tools/list、tools/call 阶段）原样抛出，不动会话
            if ex.phase != "transport":
                raise
            self._initialized = False
            self._transport.reset()
            await self._ensure_ready()
            return await self._transport.send(method, params)


def _collect_text(result: dict) -> str:
    """把 tools/call 结果的 content[] 里的 text 段拼接成字符串。"""
    parts = []
    for item in (result.get("content") or []):
        if isinstance(item, dict) and item.get("type") == "text":
            parts.append(str(item.get("text") or ""))
    return "\n".join(parts)


def _build_transport(name: str, config: dict, timeout: float):
    """按配置构建传输层：显式 transport 字段优先，缺省按 url/command 推断。"""
    transport = str(config.get("transport") or ("http" if config.get("url") else "stdio"))
    if transport == "http":
        if not config.get("url"):
            raise MCPError(name, "transport", "http 传输缺少 url")
        return HttpTransport(name, str(config["url"]), token=str(config.get("token") or ""),
                             readonly=bool(config.get("readonly", True)), timeout=timeout)
    command = config.get("command")
    if not command:
        raise MCPError(name, "transport", "stdio 传输缺少 command")
    return StdioTransport(name, list(command), env=config.get("env") or {}, timeout=timeout)


# ---- 进程级管理器：按 server 名缓存 client，跨对话轮复用会话/子进程 ----

_clients: dict[str, MCPClient] = {}
_configs: dict[str, dict] = {}


def get_client(server_name: str, config: dict, timeout: float = 15.0) -> MCPClient:
    """取（或创建）某 server 的客户端；配置变化时丢弃重建。"""
    cached = _clients.get(server_name)
    if cached is not None and _configs.get(server_name) == config:
        return cached
    if cached is not None:
        # 旧配置的 stdio 进程直接杀掉，避免残留
        try:
            cached._transport.reset()
        except Exception:
            pass
    client = MCPClient(server_name, config, timeout=timeout)
    _clients[server_name] = client
    _configs[server_name] = dict(config)
    return client
