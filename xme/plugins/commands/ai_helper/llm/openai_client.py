# some are made by Deepseek-v4-flash-vison-exp at Deepseek Harness
"""OpenAI Chat Completions 协议客户端（httpx 手写，无额外 SDK 依赖）。

一套实现同时服务 GLM 的 OpenAI 兼容端点与任意第三方兼容端点（DeepSeek / Qwen /
vLLM / Ollama / OpenRouter 等），差异只在 base_url、api_key 与模型名。

支持：
- 非流式（一次返回）与流式（SSE 增量，拼装完整结果，供上层写调试日志）；
- 工具调用（含流式下的 tool_calls 分片按 index 拼装）；
- 思考内容（reasoning_content，GLM/DeepSeek 等兼容字段）；
- 用量字段（usage，缺 cached_tokens 时按 0 计，不报错）；
- 错误分类（LLMError.kind，含 GLM 1210 媒体解析失败 → media_invalid）。
"""
import json

import httpx

from .types import ChatResult, LLMError, LLMErrorKind, ToolCall, Usage


# 流式日志的单行上限：无换行的长输出达到该长度也落一次日志，避免长时间不输出
_STREAM_LOG_LINE_MAX = 400


def _map_error(status: int, body: object, provider: str) -> LLMError:
    """把 HTTP 状态与响应体映射为统一错误（含供应商原始错误码）。"""
    code = None
    message = ""
    if isinstance(body, dict):
        err = body.get("error") or {}
        if isinstance(err, dict):
            code = err.get("code")
            message = str(err.get("message") or "")
        elif isinstance(err, str):
            message = err
        message = message or str(body.get("message") or "")
    elif isinstance(body, str):
        message = body
    text = message[:300] or f"HTTP {status}"

    if status in (401, 403):
        kind = LLMErrorKind.AUTH
    elif status == 429:
        kind = LLMErrorKind.RATE_LIMIT
    elif status >= 500:
        kind = LLMErrorKind.SERVER
    elif status == 400:
        # GLM 1210：媒体输入格式/解析错误；其他供应商用关键词兜底识别
        low = f"{code} {message}".lower()
        media_hint = any(k in low for k in
                         ("1210", "图片输入", "image input", "media", "文件解析"))
        kind = LLMErrorKind.MEDIA_INVALID if media_hint else LLMErrorKind.BAD_REQUEST
    else:
        kind = LLMErrorKind.UNKNOWN
    return LLMError(kind, text, code=code, provider=provider, status=status)


def _parse_usage(raw: object) -> Usage:
    """解析 usage（缺字段按 0；cached_tokens 埋在 prompt_tokens_details 里）。"""
    if not isinstance(raw, dict):
        return Usage()
    details = raw.get("prompt_tokens_details") or {}
    return Usage(
        prompt_tokens=int(raw.get("prompt_tokens") or 0),
        completion_tokens=int(raw.get("completion_tokens") or 0),
        total_tokens=int(raw.get("total_tokens") or 0),
        cached_tokens=int((details or {}).get("cached_tokens") or 0),
    )


class OpenAICompatProvider:
    """OpenAI Chat Completions 协议 provider。

    on_delta(kind, text)：流式增量的日志钩子（kind 为 "reasoning"/"content"），
    仅用于后台调试输出，不改变最终返回结果。
    """

    def __init__(self, name: str, base_url: str, api_key: str, *,
                 timeout: float = 300.0, stream: bool = True,
                 temperature: float | None = None,
                 extra_headers: dict | None = None,
                 on_delta=None, transport: str = "openai_http",
                 stream_fallback: bool = True):
        self.name = name
        self.transport = transport
        self.base_url = (base_url or "").rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.stream = stream                     # 默认流式：便于半流式日志
        self.temperature = temperature
        self.extra_headers = dict(extra_headers or {})
        self.on_delta = on_delta
        self.stream_fallback = stream_fallback   # 流式不可用时回退非流式（部分中转端点流式兼容差）
        self._stream_produced = False            # 本次流式是否已产出增量（决定能否安全回退）
        self._stream_buffers: dict[str, str] = {}  # 流式日志的行缓冲（按 reasoning/content 分路）
        self._client: httpx.AsyncClient | None = None

    # ---------- 内部 ----------

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json", **self.extra_headers}

    def _payload(self, messages, model, tools, temperature, thinking, stream) -> dict:
        payload: dict = {"model": model, "messages": messages, "stream": stream}
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        temp = temperature if temperature is not None else self.temperature
        if temp is not None:
            payload["temperature"] = temp
        if thinking:
            # GLM 兼容端点直接接受顶层 thinking（已在兼容端点实测通过）
            payload["thinking"] = {"type": "enabled"}
        return payload

    async def _post(self, payload: dict):
        url = f"{self.base_url}/chat/completions"
        try:
            return await self.client.post(url, headers=self._headers(), json=payload)
        except httpx.TimeoutException as ex:
            raise LLMError(LLMErrorKind.TIMEOUT, str(ex) or "请求超时", provider=self.name) from ex
        except httpx.HTTPError as ex:
            raise LLMError(LLMErrorKind.TIMEOUT, str(ex) or "连接失败", provider=self.name) from ex

    def _emit(self, kind: str, text: str) -> None:
        """立即输出一条增量（不做缓冲；note 类提示与整行输出走这里）。"""
        if self.on_delta and text:
            try:
                self.on_delta(kind, text)
            except Exception:
                pass  # 日志失败绝不影响对话

    def _reset_stream_buffers(self) -> None:
        self._stream_buffers = {"reasoning": "", "content": "", "tool_call": ""}

    def _emit_delta(self, kind: str, text: str) -> None:
        """流式增量的行缓冲输出：把逐 token 的增量按行合并，一行文本落一条日志。

        - 遇到换行 → 输出完整的行（多个 token 合并为一条日志，不再一个 token 一行）；
        - 空字符串 → 该路收尾 flush（把未换行的尾巴输出）；
        - 单行过长（无换行）→ 达到上限也输出一次，避免长行卡住不落日志。
        """
        if kind == "note":
            self._flush_deltas()
            self._emit(kind, text)
            return
        if not text:
            self._flush_delta(kind)
            return
        buf = self._stream_buffers.get(kind, "") + text
        lines = buf.split("\n")
        self._stream_buffers[kind] = lines.pop()   # 最后一段可能不完整，留待下次
        for line in lines:
            self._emit(kind, line)
        if len(self._stream_buffers[kind]) >= _STREAM_LOG_LINE_MAX:
            self._emit(kind, self._stream_buffers[kind])
            self._stream_buffers[kind] = ""

    def _flush_delta(self, kind: str) -> None:
        tail = self._stream_buffers.get(kind, "")
        if tail:
            self._emit(kind, tail)
            self._stream_buffers[kind] = ""

    def _flush_deltas(self) -> None:
        for kind in list(self._stream_buffers):
            self._flush_delta(kind)

    # ---------- 对外 ----------

    async def chat(self, messages, *, model, tools=None, temperature=None,
                   thinking=False, on_tick=None) -> ChatResult:
        """发起一次对话调用，返回统一结果。失败抛 LLMError。

        on_tick：流式读块期间周期性回调（每若干块一次），供上层检查
        "是否有插入消息/是否需要中断"——回调抛出的异常会原样穿透，用于打断当前生成。
        """
        use_stream = self.stream
        self._reset_stream_buffers()
        payload = self._payload(messages, model, tools, temperature, thinking, use_stream)
        if not use_stream:
            return await self._chat_nonstream(payload, model)

        # 真流式：必须用 client.stream，否则 httpx 会缓冲整个响应
        url = f"{self.base_url}/chat/completions"
        err: LLMError | None = None
        try:
            async with self.client.stream("POST", url, headers=self._headers(),
                                          json=payload) as response:
                if response.status_code >= 400:
                    raw = await response.aread()
                    try:
                        body = json.loads(raw)
                    except Exception:
                        body = raw.decode("utf-8", "replace")
                    raise _map_error(response.status_code, body, self.name)
                return await self._read_stream(response, model, on_tick)
        except httpx.TimeoutException as ex:
            err = LLMError(LLMErrorKind.TIMEOUT, str(ex) or "请求超时", provider=self.name)
        except httpx.HTTPError as ex:
            err = LLMError(LLMErrorKind.TIMEOUT, str(ex) or "连接失败", provider=self.name)
        # 流式失败且尚未产出任何增量 → 回退非流式重试一次
        # （部分第三方/中转端点流式兼容性差；已产出增量则不回退，避免重复生成与计费）
        if err is not None and self.stream_fallback and not self._stream_produced:
            self._emit("note", f"流式失败（{err.message[:80]}），回退非流式重试")
            return await self._chat_nonstream(payload, model)
        raise err

    async def _chat_nonstream(self, payload: dict, model: str) -> ChatResult:
        """非流式调用（也是流式失败后的回退路径）。"""
        body = dict(payload)
        body["stream"] = False
        response = await self._post(body)
        if response.status_code >= 400:
            try:
                parsed = response.json()
            except Exception:
                parsed = response.text
            raise _map_error(response.status_code, parsed, self.name)
        try:
            data = response.json()
        except Exception as ex:
            raise LLMError(LLMErrorKind.UNKNOWN, f"响应不是合法 JSON：{ex}",
                           provider=self.name, status=response.status_code) from ex
        return self._parse_completion(data, model)

    # ---------- 非流式 ----------

    def _parse_completion(self, data: dict, model: str) -> ChatResult:
        choices = data.get("choices") or [{}]
        message = (choices[0] or {}).get("message") or {}
        tool_calls = []
        for tc in message.get("tool_calls") or []:
            fn = tc.get("function") or {}
            tool_calls.append(ToolCall(id=str(tc.get("id") or ""), name=str(fn.get("name") or ""),
                                       arguments=str(fn.get("arguments") or "{}")))
        return ChatResult(
            text=str(message.get("content") or ""),
            reasoning=str(message.get("reasoning_content") or ""),
            tool_calls=tool_calls,
            usage=_parse_usage(data.get("usage")),
            finish_reason=str((choices[0] or {}).get("finish_reason") or ""),
            provider=self.name, model=model, raw=data,
        )

    # ---------- 流式（SSE 增量拼装）----------

    async def _read_stream(self, response, model: str, on_tick=None) -> ChatResult:
        """读取 SSE 流：增量回调日志，最终拼装完整 ChatResult（含工具分片）。

        on_tick 每若干块回调一次，供上层检查插入队列并打断（异常原样穿透）。
        """
        text_parts: list[str] = []
        reasoning_parts: list[str] = []
        calls: dict[int, dict] = {}
        usage = Usage()
        self._stream_produced = False   # 是否已产出增量（决定流式失败能否安全回退）
        finish_reason = ""
        first_content = False
        first_reasoning = False
        ticks = 0
        try:
            async for line in response.aiter_lines():
                if not line.startswith("data:"):
                    continue
                chunk = line[5:].strip()
                if not chunk:
                    continue
                if chunk == "[DONE]":
                    break
                try:
                    data = json.loads(chunk)
                except json.JSONDecodeError:
                    continue
                for choice in data.get("choices") or []:
                    delta = choice.get("delta") or {}
                    reasoning = delta.get("reasoning_content")
                    if reasoning:
                        self._stream_produced = True
                        if not first_reasoning:
                            first_reasoning = True
                            self._emit_delta("reasoning", "[思考] ")
                        reasoning_parts.append(reasoning)
                        self._emit_delta("reasoning", reasoning)
                    content = delta.get("content")
                    if content:
                        self._stream_produced = True
                        if not first_content:
                            first_content = True
                            self._emit_delta("content", "[回复] ")
                        text_parts.append(content)
                        self._emit_delta("content", content)
                    for tc in delta.get("tool_calls") or []:
                        self._stream_produced = True
                        idx = int(tc.get("index") or 0)
                        slot = calls.setdefault(idx, {"id": "", "name": "", "arguments": ""})
                        if tc.get("id"):
                            slot["id"] = str(tc["id"])
                        fn = tc.get("function") or {}
                        if fn.get("name"):
                            slot["name"] += str(fn["name"])
                        if fn.get("arguments"):
                            slot["arguments"] += str(fn["arguments"])
                        self._emit_delta("tool_call", json.dumps(tc, ensure_ascii=False))
                    if choice.get("finish_reason"):
                        finish_reason = str(choice["finish_reason"])
                if data.get("usage"):
                    usage = _parse_usage(data.get("usage"))
                ticks += 1
                if on_tick is not None and ticks % 5 == 0:
                    on_tick()   # 上层可能抛打断异常：原样穿透，交由调用方处理
        finally:
            # 收尾 flush：把三路未换行的尾巴也落成日志
            self._emit_delta("reasoning", "")
            self._emit_delta("content", "")
            self._emit_delta("tool_call", "")
        tool_calls = [
            ToolCall(id=v["id"] or f"call_{i}", name=v["name"], arguments=v["arguments"] or "{}")
            for i, v in sorted(calls.items())
        ]
        return ChatResult(
            text="".join(text_parts), reasoning="".join(reasoning_parts),
            tool_calls=tool_calls, usage=usage, finish_reason=finish_reason,
            provider=self.name, model=model, raw=None,
        )
