
from pathlib import Path


def clear_history(user, **kwargs) -> str:
    # 同时清空跨会话保留的 history 文件夹
    cleared_files = 0
    hist_path = Path(f"./data/temp/{user.id}/history")
    if hist_path.is_dir():
        for item in hist_path.iterdir():
            if item.is_file() or item.is_symlink():
                item.unlink()
                cleared_files += 1
    u_history = user.ai_history
    if not u_history and cleared_files == 0:
        return "历史记录清除失败：没有历史记录"
    user.ai_history = []
    return f"历史记录清除成功（包含 {cleared_files} 个历史文件）"