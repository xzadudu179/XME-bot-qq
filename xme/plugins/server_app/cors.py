"""公开接口的跨域（CORS）策略。

只回放白名单内的 Origin：*.xme.179.life、*.xmebot.com、*.xzadudu179.top（含其子域），
外加 keys.AFDIAN_OAUTH_FRONTEND_ORIGIN 里可选配置的额外来源（留空或仍是 "*" 都不额外放行）。
回放的是解析后的 scheme://host[:port]，不原样反射请求头。

本机调试要放开任意来源时，启动前设环境变量 CORS_ALLOW_ALL=1（只影响这个进程，别在公网开着）；
也可以把 "*" 临时加进 ALLOWED_ORIGIN_PATTERNS，两种写法都只是让匹配器接受任意来源。
"""
import os
import nonebot
from nonebot import log
from quart import Response, request
from urllib.parse import urlsplit

import keys

bot = nonebot.get_bot()  # 在此之前必须已经 init

# 允许跨域的来源，写 *.example.com 表示该域名及其任意子域
ALLOWED_ORIGIN_PATTERNS = ("*.xme.179.life", "*.xmebot.com", "*.xzadudu179.top")
ALLOWED_METHODS = "GET, POST, OPTIONS"
PREFLIGHT_MAX_AGE = 600
# 调试开关：设了它就放行任意来源
ALLOW_ALL_ENV = False


def _load_patterns() -> tuple[str, ...]:
    """固定域名 + keys 里可选的额外来源（留空或 "*" 都不额外放行）；调试开关优先。"""
    if ALLOW_ALL_ENV:
        return ("*",)
    extra = getattr(keys, "AFDIAN_OAUTH_FRONTEND_ORIGIN", "") or ""
    extra = extra.split("://")[-1].rstrip("/")
    if not extra or extra == "*":
        return ALLOWED_ORIGIN_PATTERNS
    return ALLOWED_ORIGIN_PATTERNS + (extra,)


ALLOWED_PATTERNS = _load_patterns()


def allowing_all() -> bool:
    """当前是否处于"放行任意来源"的调试状态。"""
    return "*" in ALLOWED_PATTERNS


def _normalize(origin: str) -> str | None:
    """把 Origin 解析成 scheme://host[:port]；不是 http(s) 或缺主机名则返回 None。"""
    parts = urlsplit(origin)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        return None
    port = f":{parts.port}" if parts.port else ""
    return f"{parts.scheme}://{parts.hostname}{port}"


def allowed_origin(origin: str | None, patterns: tuple[str, ...] = ALLOWED_PATTERNS) -> str | None:
    """Origin 命中白名单时返回可回放的 Origin（规范化后），否则返回 None。

    patterns 里出现 "*" 表示放行任意来源（保留 Origin: null 等非法值不放行）。
    """
    if not origin:
        return None
    normalized = _normalize(origin)
    if normalized is None:
        return None
    host = urlsplit(normalized).hostname
    for pattern in patterns:
        if pattern.strip() == "*":
            return normalized
        base = pattern.lower().removeprefix("*.")
        if host == base or host.endswith(f".{base}"):
            return normalized
    return None


def apply_cors_headers(response: Response, origin: str, requested_headers: str | None = None) -> None:
    """给响应补 CORS 头；已经有 Access-Control-Allow-Origin 的不动（重复头会被浏览器拒绝）。"""
    if "Access-Control-Allow-Origin" in response.headers:
        return
    response.headers["Access-Control-Allow-Origin"] = origin
    response.headers["Access-Control-Allow-Methods"] = ALLOWED_METHODS
    response.headers["Access-Control-Allow-Headers"] = requested_headers or "*"
    response.headers["Access-Control-Max-Age"] = str(PREFLIGHT_MAX_AGE)
    # 同一个 URL 会按 Origin 回不同的头，声明 Vary 免得被前置缓存串味
    vary = response.headers.get("Vary")
    response.headers["Vary"] = f"{vary}, Origin" if vary else "Origin"


@bot.server_app.before_request
async def answer_preflight():
    """白名单来源的预检（OPTIONS）直接 204 应答；其余交给正常路由。"""
    if request.method != "OPTIONS":
        return None
    origin = allowed_origin(request.headers.get("Origin"))
    if origin is None:
        return None
    response = await bot.server_app.make_default_options_response()
    apply_cors_headers(response, origin, request.headers.get("Access-Control-Request-Headers"))
    return response


@bot.server_app.after_request
async def add_cors_headers(response):
    """普通响应补 CORS 头（含 404 等错误响应）。"""
    origin = allowed_origin(request.headers.get("Origin"))
    if origin is not None:
        apply_cors_headers(response, origin, request.headers.get("Access-Control-Request-Headers"))
    return response


if allowing_all():
    log.logger.warning(f"CORS 已放行任意来源（{ALLOW_ALL_ENV}），仅本机调试用，别在公网开着")
