from pathlib import Path
import json

# AI 上下文的独立存储目录：data/ai_historys/<用户id>/<会话>.json
# 不再存放在用户的个人数据里，方便以后扩展多会话。
HISTORY_ROOT = Path("./data/ai_historys")
DEFAULT_SESSION = "default"


def _session_path(user_id, ai_session=DEFAULT_SESSION) -> Path:
    return HISTORY_ROOT / str(user_id) / f"{ai_session}.json"


def session_dir(user_id, ai_session=DEFAULT_SESSION) -> Path:
    """某个会话的 AI 文件存放目录（save_to_history 等工具的默认落盘位置）。

    与历史文件同名：data/ai_historys/<用户id>/<会话>/
    """
    return HISTORY_ROOT / str(user_id) / ai_session


def load_history(user_id, ai_session=DEFAULT_SESSION) -> list[dict]:
    """读取某用户某会话的历史记录。"""
    path = _session_path(user_id, ai_session)
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []


def save_history(user_id, history: list[dict], ai_session=DEFAULT_SESSION) -> None:
    """保存某用户某会话的历史记录。"""
    path = _session_path(user_id, ai_session)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")


def clear_history(user_id, ai_session=DEFAULT_SESSION) -> int:
    """清空某用户某会话的历史记录文件（data/ai_historys/<用户id>/<会话>.json），返回删除的文件数（0/1）。"""
    path = _session_path(user_id, ai_session)
    if not path.exists():
        return 0
    path.unlink()
    return 1


def clear_session_files(user_id, ai_session=DEFAULT_SESSION) -> int:
    """清空某用户当前会话的 history 文件夹里的所有 AI 转存文件，返回删除的文件数。"""
    dir_path = session_dir(user_id, ai_session)
    if not dir_path.is_dir():
        return 0
    removed = 0
    for item in dir_path.iterdir():
        if item.is_file() or item.is_symlink():
            item.unlink()
            removed += 1
    try:
        dir_path.rmdir()  # 空文件夹一并删除
    except OSError:
        pass
    return removed


def clear_all_history(user_id) -> int:
    """清空某用户的所有 AI 历史（data/ai_historys/<id> 目录，含各会话子文件夹），返回删除文件数。"""
    user_dir = HISTORY_ROOT / str(user_id)
    if not user_dir.is_dir():
        return 0
    # 会话名来源：<会话>.json 历史文件、<会话>/ 文件夹，去重后逐个复用单会话清理逻辑
    sessions: set[str] = set()
    for item in user_dir.iterdir():
        if item.is_file() or item.is_symlink():
            if item.suffix == ".json":
                sessions.add(item.stem)
        elif item.is_dir():
            sessions.add(item.name)
    cleared = 0
    for session in sessions:
        cleared += clear_history(user_id, session)
        cleared += clear_session_files(user_id, session)
    # 清理目录下可能残留的其它游离文件（防漏删，等价于旧实现删除所有顶层文件）
    for item in user_dir.iterdir():
        if item.is_file() or item.is_symlink():
            item.unlink()
            cleared += 1
    try:
        user_dir.rmdir()  # 所有内容已删，用户目录一并移除
    except OSError:
        pass
    return cleared


def is_summary(entry) -> bool:
    """判断一条历史记录是否为摘要条目（携带 summary 键）。"""
    return isinstance(entry, dict) and "summary" in entry


def split(history: list[dict]) -> tuple[str | None, list[str], list[dict]]:
    """从历史列表里分离出摘要与普通记录。

    返回 (摘要文本或 None, 摘要携带的技能名列表, 普通记录列表)。
    """
    summary = None
    summary_skills: list[str] = []
    normals = []
    for it in history:
        if is_summary(it):
            summary = it.get("summary")
            summary_skills = list(it.get("skills", []) or [])
        else:
            normals.append(it)
    return summary, summary_skills, normals


def merge(summary: str | None, normals: list[dict], summary_time: str = "", skills: list[str] | None = None) -> list[dict]:
    """把摘要 + 普通记录合并回历史列表（摘要放在最前）。

    skills 为摘要附带的使用过的技能名（压缩后依然保留，供 get_history 注入给 AI）。
    """
    result = []
    if summary:
        result.append({
            "summary": summary,
            "time": summary_time,
            "skills": list(skills or []),
        })
    result.extend(normals)
    return result


def count_normals(history: list[dict]) -> int:
    """统计普通（非摘要）记录的条数。"""
    return sum(1 for it in history if not is_summary(it))
