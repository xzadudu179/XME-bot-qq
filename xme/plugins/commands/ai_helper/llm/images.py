# some are made by Deepseek-v4-flash-vison-exp at Deepseek Harness
"""图片生成抽象层：OpenAI 兼容 /images/generations 协议（火山方舟 / OpenAI / 智谱同形）。

与 chat 的 OpenAICompatProvider 平级：一套实现服务所有"OpenAI images 形状"的
供应商，差异只在 base_url、api_key 与模型 ID。质量档位由 LLM_CAPABILITIES
["image_gen"] 的 models 映射表达——Seedream 这类没有 quality 字段的模型直接
按档位选模型（normal→lite、hd→pro），gpt-image 这类单模型用 quality_map 映射字段。

结果以 url 为主载体（response_format=url，**不预下载**——下载/编码由调用方
的动作决定）；仅当供应商只回 b64_json（如 gpt-image-1）时存 b64_images。
"""
import base64
from dataclasses import dataclass, field

import httpx

from .openai_client import ai_log, map_openai_error
from .types import LLMError, LLMErrorKind, Usage


@dataclass
class ImageResult:
    """一次图片生成的统一结果：urls 与 b64_images 至少其一非空。"""

    urls: list[str] = field(default_factory=list)          # 供应商原始直链（可能有时效）
    b64_images: list[bytes] = field(default_factory=list)  # 仅供应商不回 url 时有值
    download_headers: dict = field(default_factory=dict)   # 下载 urls 所需的头（如 GLM 直链要 Bearer）
    usage: Usage = field(default_factory=Usage)
    model: str = ""
    provider: str = ""


def _image_data_url(data: bytes) -> str:
    """参考图字节 → data URL（兼容端点的 image 字段接受 url 或 data 形式）。"""
    if data[:3] == b"\xff\xd8\xff":
        kind = "jpeg"
    elif data[:6] in (b"GIF87a", b"GIF89a"):
        kind = "gif"
    elif data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        kind = "webp"
    else:
        kind = "png"   # PNG 及未知格式兜底（端点解码失败会给出明确错误）
    return f"data:image/{kind};base64,{base64.b64encode(data).decode()}"


class OpenAIImagesProvider:
    """OpenAI /images/generations 协议的图片生成 provider（httpx 手写，无 SDK）。"""

    def __init__(self, name: str, base_url: str, api_key: str, *,
                 timeout: float = 120.0, extra_headers: dict | None = None):
        self.name = name
        self.base_url = (base_url or "").rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.extra_headers = dict(extra_headers or {})
        self._client: httpx.AsyncClient | None = None

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

    def _download_headers(self) -> dict:
        """下载自家直链所需的头。密钥不能无脑附带（直链可能指向第三方 CDN）：
        仅 GLM 官方域名的生成结果沿用"带认证头下载"的既有行为，其余不带。"""
        if "bigmodel.cn" in self.base_url:
            return {"Authorization": f"Bearer {self.api_key}"}
        return {}

    async def generate(self, prompt: str, *, model: str, size: str = "",
                       quality: str = "", images: list[bytes] | None = None,
                       extra_body: dict | None = None,
                       timeout: float | None = None) -> ImageResult:
        """发起一次图片生成，返回统一结果；失败抛 LLMError。

        images：参考图字节（图生图/多图融合），单张填字符串字段、多张填数组；
        size/quality 留空不传；extra_body：能力配置的额外请求字段（如 watermark）。
        """
        body: dict = {"model": model, "prompt": prompt, "response_format": "url"}
        if size:
            body["size"] = size
        if quality:
            body["quality"] = quality
        if images:
            data_urls = [_image_data_url(d) for d in images]
            body["image"] = data_urls[0] if len(data_urls) == 1 else data_urls
        body.update(extra_body or {})
        try:
            response = await self.client.post(
                f"{self.base_url}/images/generations", headers=self._headers(),
                json=body, timeout=timeout)
        except httpx.TimeoutException as ex:
            raise LLMError(LLMErrorKind.TIMEOUT, str(ex) or "请求超时", provider=self.name) from ex
        except httpx.HTTPError as ex:
            raise LLMError(LLMErrorKind.TIMEOUT, str(ex) or "连接失败", provider=self.name) from ex
        if response.status_code >= 400:
            try:
                parsed = response.json()
            except Exception:
                parsed = response.text
            err = map_openai_error(response.status_code, parsed, self.name)
            ai_log(f"图片生成失败 [{self.name}/{model}] {err}")
            raise err
        try:
            data = response.json()
        except Exception as ex:
            raise LLMError(LLMErrorKind.UNKNOWN, f"响应不是合法 JSON：{ex}",
                           provider=self.name, status=response.status_code) from ex
        urls: list[str] = []
        b64_images: list[bytes] = []
        for item in data.get("data") or []:
            if not isinstance(item, dict):
                continue
            if item.get("url"):
                urls.append(str(item["url"]))
            elif item.get("b64_json"):
                b64_images.append(base64.b64decode(item["b64_json"]))
        if not urls and not b64_images:
            raise LLMError(LLMErrorKind.UNKNOWN,
                           f"响应里没有图片数据：{str(data)[:200]}",
                           provider=self.name, status=response.status_code)
        usage_raw = data.get("usage") or {}
        usage = Usage(
            prompt_tokens=int(usage_raw.get("prompt_tokens") or 0),
            completion_tokens=int(usage_raw.get("output_tokens")
                                  or usage_raw.get("completion_tokens") or 0),
            total_tokens=int(usage_raw.get("total_tokens") or 0),
        )
        return ImageResult(urls=urls, b64_images=b64_images,
                           download_headers=self._download_headers(),
                           usage=usage, model=str(data.get("model") or model),
                           provider=self.name)
