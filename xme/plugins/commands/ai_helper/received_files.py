# 用户私聊文件缓存：记录用户发给 bot 的私聊文件（get_received_files 工具的数据源）。
#
# QQ 私聊文件到达时有两条上报路径，不同协议端（NapCat / SnowLuma 等）行为不一，两条都监听：
# 1. offline_file notice（OneBot v11 标准）：event.file = {id, name, size}，url 为实现端扩展（可能缺失）
# 2. 私聊消息里的 [CQ:file,...] 段：data 含 file_id/file_name/file_size，url 同样可能缺失
# 两路都可能同时上报同一文件，按 (user_id, file_id) 判重；file_id 缺失时按 (name, size) + 时间窗口判重。
#
# 缓存进程内 + 落盘 ./data/received_files.json（元数据只有名称/大小/时间/引用，
# 不含敏感内容；url 会过期，过期后靠 OneBot get_file API 兜底重取，仍失败则明确告知）。
import json
import time
from dataclasses import dataclass, asdict
from pathlib import Path

from nonebot import on_notice, message_preprocessor
from nonebot.log import logger

from . import constants

STORE_PATH = Path("./data/received_files.json")

_received: dict[int, list["ReceivedFile"]] = {}   # user_id → 文件列表（新的在前）
_loaded = False


@dataclass
class ReceivedFile:
    user_id: int
    file_id: str
    name: str
    size: int
    url: str = ""
    time: float = 0.0    # 记录时间戳（time.time()）

    def __post_init__(self):
        if not self.time:
            self.time = time.time()

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ReceivedFile":
        return cls(
            user_id=int(data.get("user_id") or 0),
            file_id=str(data.get("file_id") or ""),
            name=str(data.get("name") or ""),
            size=int(data.get("size") or 0),
            url=str(data.get("url") or ""),
            time=float(data.get("time") or 0),
        )


# ---------- 缓存读写 ----------

def _ensure_loaded() -> None:
    """进程内首次访问时从磁盘恢复（读失败时从空开始，不影响主流程）。"""
    global _loaded
    if _loaded:
        return
    _loaded = True
    try:
        data = json.loads(STORE_PATH.read_text(encoding="utf-8"))
        for user_id, items in data.items():
            _received[int(user_id)] = [ReceivedFile.from_dict(d) for d in items]
    except FileNotFoundError:
        pass
    except Exception:
        logger.exception(f"读取私聊文件缓存失败: {STORE_PATH}")


def _save() -> None:
    try:
        STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
        STORE_PATH.write_text(
            json.dumps({str(u): [f.to_dict() for f in files] for u, files in _received.items()},
                       ensure_ascii=False),
            encoding="utf-8")
    except Exception:
        logger.exception(f"写入私聊文件缓存失败: {STORE_PATH}")


def _is_duplicate(user_id: int, file_id: str, name: str, size: int, now: float) -> bool:
    """双路上报判重：同 user 下 file_id 相同视为同一文件；file_id 缺失时用 name+size+窗口兜底。"""
    window = float(getattr(constants, "RECEIVED_FILES_DEDUPE_WINDOW", 60.0))
    for item in _received.get(user_id, []):
        if file_id and item.file_id:
            if item.file_id == file_id:
                return True
        elif item.name == name and item.size == size and now - item.time <= window:
            return True
    return False


def record_private_file(user_id: int, file_id: str = "", name: str = "",
                        size: int = 0, url: str = "") -> ReceivedFile | None:
    """记录一条用户私聊发来的文件；重复记录返回 None。"""
    user_id = int(user_id or 0)
    name = str(name or "").strip()
    if not user_id or user_id <= 0 or not name:
        return None
    _ensure_loaded()
    now = time.time()
    file_id = str(file_id or "")
    if _is_duplicate(user_id, file_id, name, int(size or 0), now):
        # 双路里的另一路上报：只补齐缺失字段（如 notice 有 url 而消息段没有）
        if file_id:
            for item in _received.get(user_id, []):
                if item.file_id == file_id and not item.url and url:
                    item.url = url
                    _save()
                    break
        return None
    entry = ReceivedFile(user_id=user_id, file_id=file_id, name=name,
                         size=int(size or 0), url=str(url or ""), time=now)
    files = _received.setdefault(user_id, [])
    files.insert(0, entry)   # 新的在前
    per_user = int(getattr(constants, "RECEIVED_FILES_KEEP_PER_USER", 50))
    del files[per_user:]
    keep_total = int(getattr(constants, "RECEIVED_FILES_KEEP_TOTAL", 500))
    all_items = sorted((f for items in _received.values() for f in items),
                       key=lambda f: f.time, reverse=True)
    if len(all_items) > keep_total:
        dropped = all_items[keep_total:]
        dropped_keys = {(f.user_id, f.file_id, f.time) for f in dropped}
        for user_files in _received.values():
            user_files[:] = [f for f in user_files
                             if (f.user_id, f.file_id, f.time) not in dropped_keys]
    _save()
    return entry


def recent_private_files(user_id: int, within_hours: float = 24.0,
                         max_count: int = 5) -> list[ReceivedFile]:
    """取该用户最近 within_hours 小时内发来的文件（新的在前，最多 max_count 条）。"""
    _ensure_loaded()
    cutoff = time.time() - max(0.0, float(within_hours)) * 3600
    items = [f for f in _received.get(int(user_id), []) if f.time >= cutoff]
    items.sort(key=lambda f: f.time, reverse=True)   # 不依赖写入顺序，统一按时间新→旧
    return items[:max(1, int(max_count))]


def clear_state() -> None:
    """清空进程内缓存（测试用）。"""
    _received.clear()
    _sent_files.clear()
    global _loaded
    _loaded = True   # 防止后续操作又从磁盘读回旧数据


# ---------- bot 发出的私聊文件登记（过滤预览点击的回显） ----------
# 用户在 QQ 客户端里点击 bot 发来的文件预览/下载时，协议端会把该文件作为一条
# 来自用户的 [CQ:file] 消息上报（回显）；插入消息通道凭此登记把回显过滤掉，
# 不让它污染 AI 上下文。短 TTL 内存态，不落盘。
SENT_FILE_TTL = 600.0
_sent_files: dict[int, list[tuple[str, float]]] = {}   # user_id → [(文件名, 过期时间)]


def record_sent_file(user_id: int, name: str) -> None:
    """登记 bot 刚向该用户私聊发送的文件名（同名文件在 TTL 内视为回显）。"""
    now = time.time()
    entries = [e for e in _sent_files.get(int(user_id), []) if e[1] > now]
    entries.append((str(name or ""), now + SENT_FILE_TTL))
    _sent_files[int(user_id)] = entries[-50:]


def is_bot_sent_file(user_id: int, name: str) -> bool:
    """该文件名是否为 bot 近期发给该用户的文件（顺带清理过期项）。"""
    now = time.time()
    entries = [e for e in _sent_files.get(int(user_id), []) if e[1] > now]
    _sent_files[int(user_id)] = entries
    return str(name or "") in [e[0] for e in entries]


# ---------- 事件监听 ----------

def _parse_file_notice(event) -> tuple[int, str, str, int, str] | None:
    """解析 offline_file notice；兼容 file 嵌套对象与扁平字段两种实现形态。"""
    user_id = int(getattr(event, "user_id", 0) or 0)
    if not user_id:
        return None
    raw = event.get("file") if hasattr(event, "get") else None
    if raw is None:
        raw = getattr(event, "file", None)
    if isinstance(raw, dict) and raw:
        return (user_id, str(raw.get("id") or raw.get("file_id") or ""),
                str(raw.get("name") or raw.get("file_name") or ""),
                int(raw.get("size") or raw.get("file_size") or 0),
                str(raw.get("url") or ""))
    # 扁平形态：字段直接在事件顶层
    file_id = str(getattr(event, "file_id", "") or "")
    name = str(getattr(event, "file_name", "") or getattr(event, "name", "") or "")
    if file_id or name:
        return (user_id, file_id, name,
                int(getattr(event, "file_size", 0) or getattr(event, "size", 0) or 0),
                str(getattr(event, "url", "") or ""))
    return None


@on_notice('offline_file')
async def _on_offline_file_notice(session):
    event = session.event
    if getattr(event, "group_id", None):
        return
    try:
        parsed = _parse_file_notice(event)
        if parsed is not None:
            record_private_file(*parsed)
    except Exception:
        logger.exception("记录 offline_file 私聊文件失败")


@message_preprocessor
async def _on_private_message(bot, event, plugin_manager):
    """私聊消息里的 [CQ:file] 段（部分协议端把文件作为消息上报而不是 notice）。只旁观，不拦截。"""
    if getattr(event, "group_id", None):
        return
    user_id = int(getattr(event, "user_id", 0) or 0)
    if not user_id or user_id == int(getattr(event, "self_id", 0) or 0):
        return
    try:
        for seg in event.message:
            if not isinstance(seg, dict) or seg.get("type") != "file":
                continue
            data = seg.get("data") or {}
            record_private_file(
                user_id=user_id,
                file_id=str(data.get("file_id") or data.get("file") or ""),
                name=str(data.get("file_name") or data.get("name") or ""),
                size=int(data.get("file_size") or data.get("size") or 0),
                url=str(data.get("url") or ""),
            )
    except Exception:
        logger.exception("记录私聊消息文件段失败")
