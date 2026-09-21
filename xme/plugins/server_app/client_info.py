"""server_app 各路由共用的访问者信息。

访问日志与真实 IP 解析只在这里实现一份：X-Forwarded-For 经过 CDN/多层代理时
是逗号分隔的转发链，只有第一段是真实客户端。
"""
from nonebot import log
from quart import Request


def get_client_ip(req: Request) -> str:
    """解析访问者真实 IP：优先 X-Forwarded-For 第一段，其次 X-Real-IP，最后 remote_addr。"""
    forwarded = req.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return req.headers.get("X-Real-IP") or req.remote_addr or ""


def log_visit(tag: str, req: Request) -> None:
    """记录一次路由访问（tag 是访问对象，如 "文件"、"文档"）。"""
    log.logger.info(f"bot {tag} 被访问了，访问者 IP: {get_client_ip(req)}")
