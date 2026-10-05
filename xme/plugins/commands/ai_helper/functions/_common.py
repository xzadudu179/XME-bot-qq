# some are made by Deepseek-v4-flash-vison-exp at Deepseek Harness
"""跨分类共享的常量与私有 helper（各分类模块经 from ._common import 使用）。"""
import asyncio

GLM_API_BASE = "https://open.bigmodel.cn/api"

def exception_detail(ex: BaseException) -> str:
    """异常的可读描述：始终带类型名；str() 失败或为空（如 TimeoutError）时退化为类型名/repr。"""
    try:
        msg = str(ex).strip()
    except Exception:
        msg = ""
    return f"{type(ex).__name__}: {msg}" if msg else type(ex).__name__


def render_url_guard(source: str = "", agent=None):
    """渲染类工具（screenshot_page / monitor_element / record_page）的 URL 守卫。

    返回 async (url) -> None（违规抛 ValueError）。传给 CDPBrowser(url_guard=...)
    后由传输层在「请求发出前」（Fetch 拦 file://、setBlockedURLs 拦私网）与
    「导航提交时」（frameNavigated 复检）双层调用；守卫超时按违规处理（fail-closed）。
    """
    from urllib.parse import unquote

    from xme.xmetools.reqtools import assert_public_http_url

    allowed: list[str] = []
    src = str(source or "")
    if src.startswith("file:"):
        # 初始文档所在目录（同目录相对资源视为页面自身的一部分）
        allowed.append(unquote(src.rsplit("/", 1)[0] + "/"))
    if agent is not None:
        for p in (agent.get_temp_path(), agent.get_history_path()):
            try:
                allowed.append(unquote(p.resolve().as_uri() + "/"))
            except Exception:
                pass

    async def guard(url: str) -> None:
        u = unquote(str(url or ""))
        scheme = u.split(":", 1)[0].lower()
        if scheme == "file":
            if any(u.startswith(prefix) for prefix in allowed):
                return
            raise ValueError(f"file:// 访问越出会话目录（{u[:120]}）")
        if scheme in ("http", "https"):
            # DNS 解析是阻塞调用：放线程执行；结果不合规/解析失败都算违规
            await asyncio.to_thread(assert_public_http_url, u)
            return
        raise ValueError(f"不允许的协议 {scheme!r}（渲染只接受 http/https/file）")

    return guard


class ImageToolResult(str):
    """附图片/媒体段的工具结果（str 子类）。
    """

    def __new__(cls, text: str, image_parts: list):
        obj = super().__new__(cls, text)
        obj.image_parts = list(image_parts)
        return obj

