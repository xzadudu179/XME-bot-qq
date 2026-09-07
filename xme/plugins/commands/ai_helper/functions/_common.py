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


class ImageToolResult(str):
    """附图片/媒体段的工具结果（str 子类）。

    文本部分照常作为 tool message 返回给模型；image_parts（GLM 多模态 content
    part 列表，可含 image_url/video_url/file 段）由 agent 在本轮工具全部结束后
    合并注入一条 user 消息——仅当前轮模型为视觉模型时注入，省去 view_item 的
    独立视觉调用。str 子类保证所有按字符串处理结果的既有逻辑（压缩、快照、日志）不变。
    """

    def __new__(cls, text: str, image_parts: list):
        obj = super().__new__(cls, text)
        obj.image_parts = list(image_parts)
        return obj

