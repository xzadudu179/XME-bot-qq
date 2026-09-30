"""MCP 传输层：Streamable HTTP 与 stdio 本地进程两种实现的统一请求接口。

两者都只暴露 `send(method, params, notify)`：发送一条 JSON-RPC 请求/通知并返回
响应的 result（通知返回 None）。会话/进程生命周期由各自实现内部维护。
"""
import asyncio
import json
from collections import deque

import httpx

from .types import (
    MCP_PROTOCOL_VERSION, MCPError, encode_message, extract_rpc_result,
    rpc_notification, rpc_request,
)

# Streamable HTTP 规范要求 Accept 同时声明两种类型（服务器二选一返回）
_HTTP_ACCEPT = "application/json, text/event-stream"


class HttpTransport:
    """远程 HTTP MCP server（Streamable HTTP）：GitHub 远程 server 等。

    维护 initialize 协商出的 Mcp-Session-Id 与协议版本头；服务器返回 404
    表示会话过期，清空会话状态（上层 client 捕获后重新 initialize）。
    """

    def __init__(self, name: str, url: str, token: str = "", readonly: bool = False,
                 timeout: float = 15.0):
        self.name = name
        self.url = url
        self._token = token or ""
        self._readonly = bool(readonly)
        self._timeout = timeout
        self._session_id: str | None = None
        self._client: httpx.AsyncClient | None = None

    def _headers(self) -> dict:
        headers = {"Accept": _HTTP_ACCEPT, "Content-Type": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        if self._session_id:
            headers["Mcp-Session-Id"] = self._session_id
            headers["MCP-Protocol-Version"] = MCP_PROTOCOL_VERSION
        if self._readonly:
            headers["X-MCP-Readonly"] = "true"
        return headers

    def reset(self) -> None:
        """丢弃会话状态（404/异常后由上层重新 initialize）。"""
        self._session_id = None

    async def send(self, method: str, params: dict | None = None, notify: bool = False) -> dict | None:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self._timeout)
        try:
            payload = rpc_notification(method, params) if notify else rpc_request(method, params)
            response = await self._client.post(self.url, json=payload, headers=self._headers())
        except httpx.HTTPError as ex:
            raise MCPError(self.name, "transport", f"请求失败：{type(ex).__name__}: {ex}") from ex
        if response.status_code == 404 and self._session_id:
            # 会话过期：清空会话头，让上层重新 initialize
            self._session_id = None
            raise MCPError(self.name, "transport", "会话已过期（404）")
        if response.status_code in (202, 204):
            return None
        if response.status_code >= 400:
            raise MCPError(self.name, "transport",
                           f"HTTP {response.status_code}: {response.text[:200]}")
        new_session = response.headers.get("Mcp-Session-Id")
        if new_session:
            self._session_id = new_session
        content_type = response.headers.get("Content-Type", "")
        if "text/event-stream" in content_type:
            return self._parse_sse(self.name, response.text, method)
        try:
            body = response.json()
        except Exception as ex:
            raise MCPError(self.name, "transport", f"响应不是合法 JSON：{ex}") from ex
        if notify:
            return None
        return extract_rpc_result(self.name, method, body)

    @staticmethod
    def _parse_sse(server: str, text: str, method: str) -> dict | None:
        """从 SSE 文本里取出第一条 JSON-RPC 响应（有 id 的即为本请求结果）。"""
        for line in text.splitlines():
            line = line.strip()
            if not line.startswith("data:"):
                continue
            chunk = line[5:].strip()
            if not chunk or chunk == "[DONE]":
                continue
            try:
                data = json.loads(chunk)
            except json.JSONDecodeError:
                continue
            if isinstance(data, dict) and "id" in data:
                return extract_rpc_result(server, method, data)
        raise MCPError(server, method, "SSE 响应中没有 JSON-RPC result")


class StdioTransport:
    """本地 stdio MCP server（blender-mcp / filesystem 等）：子进程按行收发 JSON-RPC。

    进程常驻跨轮复用；死亡后由上层 client 重启。读侧收敛到后台任务，
    按 id 匹配响应，其余消息（ server 主动通知/日志）忽略。
    """

    def __init__(self, name: str, command: list[str], env: dict | None = None,
                 timeout: float = 30.0):
        self.name = name
        self.command = [str(c) for c in command]
        self._env = {k: str(v) for k, v in (env or {}).items()}
        self._timeout = timeout
        self._proc: asyncio.subprocess.Process | None = None
        self._pending: dict[int, asyncio.Future] = {}
        self._next_id = 1
        self._reader_task: asyncio.Task | None = None
        self._stderr_task: asyncio.Task | None = None
        self._stderr_tail: deque[str] = deque(maxlen=20)
        self._send_lock = asyncio.Lock()   # 单 socket server 内部多为串行：发送逐条排队

    async def _ensure_process(self) -> None:
        import os
        if self._proc is not None:
            if self._proc.returncode is not None:
                # 已退出：报 transport 错，由上层 reset（清 _proc）后重新握手
                raise MCPError(self.name, "transport",
                               f"server 进程已退出（码 {self._proc.returncode}）；"
                               f"stderr 尾部: {' | '.join(self._stderr_tail)[-200:]}")
            return
        self._pending.clear()
        self._stderr_tail.clear()
        try:
            self._proc = await asyncio.create_subprocess_exec(
                *self.command,
                stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**os.environ, **self._env})
        except OSError as ex:
            raise MCPError(self.name, "transport",
                           f"无法启动 {self.command[:2]}：{ex}") from ex
        self._reader_task = asyncio.create_task(self._read_loop())
        self._stderr_task = asyncio.create_task(self._drain_stderr())

    async def _drain_stderr(self) -> None:
        """持续排空 stderr 进环形缓冲（不排空会写满管道缓冲把子进程卡死）。"""
        assert self._proc is not None and self._proc.stderr is not None
        async for raw in self._proc.stderr:
            self._stderr_tail.append(raw.decode("utf-8", "replace").rstrip())

    async def _read_loop(self) -> None:
        assert self._proc is not None and self._proc.stdout is not None
        async for raw in self._proc.stdout:
            line = raw.decode("utf-8", "replace").strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(data, dict) or "id" not in data:
                continue   # server 主动通知/日志：忽略
            fut = self._pending.pop(data.get("id"), None)
            if fut is not None and not fut.done():
                fut.set_result(data)
        # stdout 结束 = 进程退出：唤醒所有等待者，报错交上层处理
        for fut in self._pending.values():
            if not fut.done():
                fut.set_exception(MCPError(
                    self.name, "transport",
                    f"server 进程已退出（码 {self._proc.returncode}）；"
                    f"stderr 尾部: {' | '.join(self._stderr_tail)[-200:]}"))
        self._pending.clear()

    async def send(self, method: str, params: dict | None = None, notify: bool = False) -> dict | None:
        async with self._send_lock:
            await self._ensure_process()
            assert self._proc is not None and self._proc.stdin is not None
            if notify:
                self._proc.stdin.write((encode_message(
                    {"jsonrpc": "2.0", "method": method, "params": params or {}}) + "\n").encode())
                await self._proc.stdin.drain()
                return None
            req_id = self._next_id
            self._next_id += 1
            fut: asyncio.Future = asyncio.get_running_loop().create_future()
            self._pending[req_id] = fut
            self._proc.stdin.write((encode_message(
                rpc_request(method, params, req_id)) + "\n").encode())
            await self._proc.stdin.drain()
            try:
                response = await asyncio.wait_for(fut, timeout=self._timeout)
            except asyncio.TimeoutError:
                self._pending.pop(req_id, None)
                raise MCPError(self.name, method if method.startswith("tools/") else "transport",
                               f"请求超时（>{self._timeout:.0f}s）")
            return extract_rpc_result(self.name, method, response)

    def reset(self) -> None:
        """杀掉当前进程并清空状态（下次 send 重新启动 + 上层重新握手）。"""
        if self._reader_task is not None:
            self._reader_task.cancel()
            self._reader_task = None
        if self._stderr_task is not None:
            self._stderr_task.cancel()
            self._stderr_task = None
        if self._proc is not None and self._proc.returncode is None:
            try:
                self._proc.kill()
            except ProcessLookupError:
                pass
        self._proc = None
        self._pending.clear()
