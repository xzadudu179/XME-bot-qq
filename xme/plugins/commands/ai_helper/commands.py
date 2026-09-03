
from pathlib import Path

from . import history


def clear_history(user, **kwargs) -> str:
    # 清空当前会话的历史记录文件（data/ai_historys/<用户id>/<会话>.json）
    cleared_hist = history.clear_history(user.id)
    # 清空当前会话 history 文件夹里的 AI 转存文件（data/ai_historys/<用户id>/<会话>/）
    cleared_files = history.clear_session_files(user.id)
    if cleared_hist == 0 and cleared_files == 0:
        return "历史记录清除失败：没有历史记录"
    return f"历史记录清除成功（包含 {cleared_files} 个文件）"