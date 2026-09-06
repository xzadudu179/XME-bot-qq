# some are made by Deepseek-v4-flash-vison-exp at Deepseek Harness
"""跨分类共享的常量与私有 helper（各分类模块经 from ._common import 使用）。"""

GLM_API_BASE = "https://open.bigmodel.cn/api"

def exception_detail(ex: BaseException) -> str:
    """异常的可读描述：始终带类型名；str() 失败或为空（如 TimeoutError）时退化为类型名/repr。"""
    try:
        msg = str(ex).strip()
    except Exception:
        msg = ""
    return f"{type(ex).__name__}: {msg}" if msg else type(ex).__name__

