from pathlib import Path
import json

# AI 上下文的独立存储目录：data/ai_historys/<用户id>/<会话>.json
# 不再存放在用户的个人数据里，方便以后扩展多会话。
HISTORY_ROOT = Path("./data/ai_historys")
DEFAULT_SESSION = "default"


def _session_path(user_id, session=DEFAULT_SESSION) -> Path:
    return HISTORY_ROOT / str(user_id) / f"{session}.json"


def load_history(user_id, session=DEFAULT_SESSION) -> list[dict]:
    """读取某用户某会话的历史记录。"""
    path = _session_path(user_id, session)
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []


def save_history(user_id, history: list[dict], session=DEFAULT_SESSION) -> None:
    """保存某用户某会话的历史记录。"""
    path = _session_path(user_id, session)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")


def clear_history(user_id, session=DEFAULT_SESSION) -> int:
    """清空某用户某会话的历史，返回删除的文件数（0/1）。"""
    path = _session_path(user_id, session)
    if not path.exists():
        return 0
    path.unlink()
    return 1


def clear_all_history(user_id) -> int:
    """清空某用户的所有 AI 历史（整个 data/ai_historys/<id> 目录），返回删除文件数。"""
    user_dir = HISTORY_ROOT / str(user_id)
    if not user_dir.is_dir():
        return 0
    cleared = 0
    for item in user_dir.iterdir():
        if item.is_file():
            item.unlink()
            cleared += 1
    return cleared
