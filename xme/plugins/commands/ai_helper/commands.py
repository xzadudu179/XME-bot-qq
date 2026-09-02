
from pathlib import Path

from . import history


def clear_history(user, **kwargs) -> str:
    # 清空跨会话保留的 history 文件夹（转存的历史文件）
    cleared_files = 0
    hist_path = Path(f"./data/temp/{user.id}/history")
    if hist_path.is_dir():
        for item in hist_path.iterdir():
            if item.is_file() or item.is_symlink():
                item.unlink()
                cleared_files += 1
    # 清空 AI 上下文存储（data/ai_historys/<用户id>）
    cleared_ctx = history.clear_all_history(user.id)
    if cleared_ctx == 0 and cleared_files == 0:
        return "历史记录清除失败：没有历史记录"
    return f"历史记录清除成功（清空 {cleared_ctx} 个 AI 会话，{cleared_files} 个转存历史文件）"