from pathlib import Path
import json

# AI 上下文的独立存储目录：data/ai_historys/<用户id>/<会话>.json
# 不再存放在用户的个人数据里，方便以后扩展多会话。
HISTORY_ROOT = Path("./data/ai_historys")
DEFAULT_SESSION = "default"


def _session_path(user_id, session=DEFAULT_SESSION) -> Path:
    return HISTORY_ROOT / str(user_id) / f"{session}.json"


def session_dir(user_id, session=DEFAULT_SESSION) -> Path:
    """某个会话的 AI 文件存放目录（save_to_history 等工具的默认落盘位置）。

    与历史文件同名：data/ai_historys/<用户id>/<会话>/
    """
    return HISTORY_ROOT / str(user_id) / session


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
    """清空某用户的所有 AI 历史（data/ai_historys/<id> 目录，含各会话子文件夹），返回删除文件数。"""
    user_dir = HISTORY_ROOT / str(user_id)
    if not user_dir.is_dir():
        return 0
    cleared = 0
    for item in user_dir.iterdir():
        if item.is_file() or item.is_symlink():
            item.unlink()
            cleared += 1
        elif item.is_dir():
            # 会话文件夹（如 default/）里的 AI 转存文件
            for sub in item.iterdir():
                if sub.is_file() or sub.is_symlink():
                    sub.unlink()
                    cleared += 1
            try:
                item.rmdir()
            except OSError:
                pass
    return cleared


def is_summary(entry) -> bool:
    """判断一条历史记录是否为摘要条目（携带 summary 键）。"""
    return isinstance(entry, dict) and "summary" in entry


def split(history: list[dict]) -> tuple[str | None, list[dict]]:
    """从历史列表里分离出摘要与普通记录。返回 (摘要文本或 None, 普通记录列表)。"""
    summary = None
    normals = []
    for it in history:
        if is_summary(it):
            summary = it.get("summary")
        else:
            normals.append(it)
    return summary, normals


def merge(summary: str | None, normals: list[dict], summary_time: str = "") -> list[dict]:
    """把摘要 + 普通记录合并回历史列表（摘要放在最前）。"""
    result = []
    if summary:
        result.append({"summary": summary, "time": summary_time})
    result.extend(normals)
    return result


def count_normals(history: list[dict]) -> int:
    """统计普通（非摘要）记录的条数。"""
    return sum(1 for it in history if not is_summary(it))
