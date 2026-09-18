import functools
import socket

import aiohttp
import yarl
from aiohttp.abc import AbstractResolver
# import asyncio
import json
# from xme.xmetools.debugtools import debug_msg
from keys import GLM_API_KEY
from nonebot.log import logger
import os
from config import USE_PROXY, HTTP_PORT

# 统一代理地址（USE_PROXY 时指向本地代理端口）。
# 注意：aiohttp 默认 trust_env=False，不读 HTTP_PROXY/HTTPS_PROXY 环境变量，
# aiohttp 系请求必须显式传 proxy=PROXY_URL 才会走代理；环境变量只对 urllib/yt-dlp 系生效。
PROXY_URL: str | None = f"http://127.0.0.1:{HTTP_PORT}" if USE_PROXY else None
if PROXY_URL:
    logger.info(f"使用代理运行: {PROXY_URL}")
    os.environ["HTTP_PROXY"] = PROXY_URL   # 供 yt-dlp（urllib 系）使用
    os.environ["HTTPS_PROXY"] = PROXY_URL
# 浏览器 UA：aiohttp/裸脚本默认 UA 会被不少站点（W3Schools、B 站等）风控拒绝
DEFAULT_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"


async def get_weather(city: str) -> dict:
    response = await fetch_data(f"https://restapi.amap.com/v3/weather/weatherInfo?key=***&city={city}&extensions=all")
    # print(response)
    json_dict = json.loads(response)
    return json_dict

async def fetch_data_post(url, json, *args, **kwargs):
    try:
        async with aiohttp.ClientSession() as aiosession:
            async with aiosession.post(url, *args, **kwargs, json=json) as response:
                data = await response.json()
                return data
    except Exception as e:
        logger.exception(e)
        raise

@functools.lru_cache(maxsize=1)
def glm_headers() -> dict:
    """GLM 开放平台请求头（Bearer 认证）。缓存避免每次重复构造。"""
    return {
        "Authorization": f"Bearer {GLM_API_KEY}",
        "Content-Type": "application/json",
    }



async def glm_api_request(path: str, method: str = "POST", **payload) -> dict:
    """调用智谱(GLM) 开放平台接口，统一处理 base url、认证头与 request_id。
    payload 参数前面的 _ 会被 strip 掉
    之后新增 GLM 工具接口（网页搜索、文件、知识库等）只需调用本函数并传入 path 与参数：
        result = await glm_api_request("/paas/v4/reader", url="https://...")
    失败时会抛出异常。
    """
    from xme.plugins.commands.ai_helper.functions import GLM_API_BASE
    import uuid
    path = path if path.startswith("/") else "/" + path
    url = GLM_API_BASE + path
    headers = glm_headers()
    payload = {k.lstrip("_"): v for k, v in payload.items()}
    if method.upper() == "GET":
        return await fetch_data(url, raise_error=True, response_type="json", headers=headers, params=payload)
    body = dict(payload)
    body["request_id"] = body.get("request_id", str(uuid.uuid4()))
    return await fetch_data_post(url, json=body, headers=headers)

async def fetch_data(url, response_type="json", raise_error=False, **args):
    async with aiohttp.ClientSession() as aiosession:
        async with aiosession.get(url, **args) as response:
            if raise_error:
                response.raise_for_status()
            match response_type:
                case "json":
                    data = await response.json()

                case "text":
                    data = await response.text()

                case "byte":
                    data = await response.read()
                case _:
                    raise ValueError(
                        "返回类型只能是 json, byte 或 text"
                    )
            return data

def assert_public_http_url(url: str) -> dict[str, list[str]]:
    """SSRF 防护：校验 http(s) URL 的主机不是本机/内网/链路本地/保留地址。

    域名会实际解析 DNS 后逐 IP 检查（防 "localtest.me" 这类解析到 127.0.0.1 的绕过）。
    不合规抛 ValueError；非 http(s) 协议同样抛错。
    返回 {主机: 已校验 IP 列表}，调用方（fetch_file_stream）据此构造钉扎解析器，
    保证连接只连这些 IP——校验与连接各自独立解析 DNS 时，域名可在两次解析间被
    rebinding 到内网地址。重定向由 fetch_file_stream 逐跳复检。
    """
    import ipaddress
    from urllib.parse import urlsplit

    parts = urlsplit(url)
    if parts.scheme not in ("http", "https"):
        raise ValueError("仅支持 http/https 地址")
    host = parts.hostname
    if not host:
        raise ValueError("无效的 url（缺少主机名）")
    try:
        infos = socket.getaddrinfo(host, parts.port or (443 if parts.scheme == "https" else 80),
                                   proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        raise ValueError(f"无法解析主机 {host}")
    allowed: list[str] = []
    for info in infos:
        ip_text = info[4][0]
        if not ipaddress.ip_address(ip_text).is_global:
            raise ValueError(f"禁止访问内网/本机地址（{host} → {ip_text}）")
        if ip_text not in allowed:
            allowed.append(ip_text)
    if not allowed:
        raise ValueError(f"主机 {host} 没有可连接的地址")
    return {host: allowed}


class _PinnedResolver(AbstractResolver):
    """只解析到已校验 IP 的钉扎解析器：连接时的 DNS 查询被替换为查校验结果表。

    表外的主机名一律拒绝解析；IP 列表来自 assert_public_http_url 的返回值，
    校验后域名再怎么变解析结果都不会绕开已校验的地址。
    """

    def __init__(self, allowed: dict[str, list[str]]):
        self._allowed = allowed

    async def resolve(self, host: str, port: int = 0, family: int = socket.AF_INET) -> list[dict]:
        import ipaddress
        ips = self._allowed.get(host)
        if not ips:
            raise ValueError(f"主机 {host} 未经过公网校验，拒绝解析")
        out = []
        for ip_text in ips:
            addr_family = socket.AF_INET6 if ipaddress.ip_address(ip_text).version == 6 \
                else socket.AF_INET
            if family not in (0, socket.AF_UNSPEC, addr_family):
                continue
            out.append({"hostname": host, "host": ip_text, "port": port,
                        "family": addr_family, "proto": socket.IPPROTO_TCP,
                        "flags": socket.AI_NUMERICHOST})
        if not out:
            raise OSError(f"主机 {host} 在该地址族下没有已校验的 IP")
        return out

    async def close(self) -> None:
        pass


async def fetch_file_stream(url: str, *, max_size: int = 20 * 1024 * 1024, timeout: float = 60, headers: dict | None = None, proxy: str | None = PROXY_URL) -> tuple[bytes, str]:
    """流式下载 URL 内容到内存，超出 max_size 立即中止并抛 ValueError。

    与 fetch_data 的区别：逐块读取，可在下载过程中按大小截断，
    不会把超大文件整个读进内存。返回 (内容 bytes, Content-Type 字符串)。
    proxy: 默认取 config 的 PROXY_URL（USE_PROXY 时）；显式传 None 强制直连。
    """
    # SSRF 防护：先校验初始地址；重定向手动逐跳跟随并逐一复检（最多 5 跳），
    # 防止公网地址 302 跳到内网/元数据端点绕过检查。
    # 校验返回的 IP 逐跳登记进 allowed，连接经钉扎解析器只连已校验 IP，
    # 校验后 DNS rebinding 换址无法生效
    current_url = url
    allowed: dict[str, list[str]] = {}
    async with aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(resolver=_PinnedResolver(allowed))) as aiosession:
        merged_headers = {"User-Agent": DEFAULT_UA, **(headers or {})}
        for _hop in range(6):
            allowed.update(assert_public_http_url(current_url))
            async with aiosession.get(current_url, headers=merged_headers, proxy=proxy, allow_redirects=False, timeout=aiohttp.ClientTimeout(total=timeout)) as response:
                if response.status in (301, 302, 303, 307, 308):
                    location = response.headers.get("Location", "")
                    if not location:
                        raise ValueError(f"重定向缺少 Location（{current_url}）")
                    current_url = str(yarl.URL(current_url).join(yarl.URL(location)))
                    continue
                response.raise_for_status()
                content_length = response.headers.get("Content-Length", "")
                if content_length.isdigit() and int(content_length) > max_size:
                    raise ValueError(
                        f"文件大小 {int(content_length) / 1048576:.1f}MiB 超出 {max_size / 1048576:g}MiB 限制")
                chunks = []
                total = 0
                async for chunk in response.content.iter_chunked(64 * 1024):
                    total += len(chunk)
                    if total > max_size:
                        raise ValueError(f"文件超出 {max_size / 1048576:g}MiB 大小限制")
                    chunks.append(chunk)
                return b"".join(chunks), response.headers.get("Content-Type", "")
        raise ValueError("重定向次数过多（>5）")
