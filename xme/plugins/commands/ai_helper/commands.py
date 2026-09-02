
from pathlib import Path

from . import history


def clear_history(user, **kwargs) -> str:
    # 清空旧的 temp/history 残留（历史遗留，仅清理一次旧的路径）
    cleared_old = 0
    old_path = Path(f"./data/temp/{user.id}/history")
    if old_path.is_dir():
        for item in old_path.iterdir():
            if item.is_file() or item.is_symlink():
                item.unlink()
                cleared_old += 1
    # 清空 AI 上下文存储（data/ai_historys/<用户id>，含各会话的 ai_history 文件与转存文件）
    cleared_ctx = history.clear_all_history(user.id)
    if cleared_ctx == 0 and cleared_old == 0:
        return "历史记录清除失败：没有历史记录"
    return f"历史记录清除成功（清空 {cleared_ctx} 个 AI 会话/转存文件，{cleared_old} 个旧残留）"