"""共享会话：多用户共享同一个 AI 会话（群主/成员/加入审批/对话锁）。

存储布局（data/ai_historys/ 下单开 shared 目录，与各用户目录平级）：
    shared/<群号码>/history.json   共享历史（与普通会话完全同格式）
    shared/<群号码>/meta.json      {code, title, owner, admins, created_time,
                                    members:[{user_id, joined_time}], requests:[{user_id, time}], blocked}
    <用户id>/.joined               已加入的群号码（每行一个，顺序即 a 序号 a1、a2...）
    <用户id>/.current_shared       共享模式指针（存在且指向有效会话 ⇒ 当前处于共享模式）

与 AISession 的关系：SharedSession 提供 ai_session/load_history/save_history/
count/dir_path 等同名接口（鸭子类型），agent 层通过 AIHelper.storage 统一读写，
不感知具体类型；两者互不 import（本模块只依赖 history 的路径函数）。

与普通会话的关键差异：目录以群号码命名，"改名"只更新 meta 里的 title 展示字段，
不涉及文件移动（普通会话名字即文件名，改名=移动文件）。
"""
from pathlib import Path

from xme.xmetools import jsontools
from xme.xmetools.timetools import get_time_now

from . import history
from .constants import (
    CURRENT_SHARED_FILE,
    DEFAULT_SHARED_TITLE,
    JOINED_FILE,
    MAX_JOINED_SHARED,
    MAX_SHARED_MEMBERS,
    SESSION_NAME_MAX_LEN,
    SHARED_CODE_MAX_N,
    SHARED_CODE_PREFIX,
    SHARED_CODE_WIDTH,
    SHARED_DIR_NAME,
    SHARED_HISTORY_FILE,
    SHARED_META_FILE,
)

# 对话忙表：{群号码: True}。有人在某共享会话调用 AI 期间其他成员被拒。
# 与 __init__.py 的 curr_sessions 同模式：检查与置位之间无 await，asyncio 单线程下原子。
_busy_codes: dict[str, bool] = {}


def _shared_root() -> Path:
    """共享会话根目录（运行时从 HISTORY_ROOT 派生，便于测试时整体替换）。"""
    return history.HISTORY_ROOT / SHARED_DIR_NAME


def _user_state_file(user_id, name: str) -> Path:
    return history.user_dir(user_id) / name


def is_valid_code(code: str) -> bool:
    """校验群号码格式：AI 前缀 + 纯数字。"""
    return (isinstance(code, str) and code.startswith(SHARED_CODE_PREFIX)
            and code[len(SHARED_CODE_PREFIX):].isdigit())


def normalize_code(code: str) -> str:
    """规整用户输入的群号码：去首尾空白、转大写。"""
    return (code or "").strip().upper()


def acquire_busy(code: str) -> bool:
    """尝试占用某共享会话的对话锁；已被占用返回 False。"""
    if _busy_codes.get(code):
        return False
    _busy_codes[code] = True
    return True


def release_busy(code: str) -> None:
    """释放共享会话的对话锁（未占用时静默）。"""
    _busy_codes.pop(code, None)


class SharedSession:
    """单个共享会话对象：封装群号码、成员/请求/屏蔽名单与共享历史的读写。

    - members[0] 恒为群主；admins 为预留的管理员扩展位（当前恒空）。
    - 所有状态变更方法都是"读 meta → 改 → 整体写回"，落盘前不抛异常
      （写盘失败会向上抛 OSError，由命令层统一兜底）。
    """

    def __init__(self, code: str):
        self.code = normalize_code(code)

    # ---------- 路径与基础属性 ----------

    @property
    def dir_path(self) -> Path:
        """共享会话目录：data/ai_historys/shared/<群号码>/"""
        return _shared_root() / self.code

    @property
    def meta_path(self) -> Path:
        return self.dir_path / SHARED_META_FILE

    @property
    def history_path(self) -> Path:
        return self.dir_path / SHARED_HISTORY_FILE

    @property
    def ai_session(self) -> str:
        """会话标识（与 AISession.ai_session 鸭子类型兼容，这里即群号码）。"""
        return self.code

    @property
    def meta(self) -> dict:
        """读取状态文件；缺失/损坏时返回空 dict（按空会话处理，不抛异常）。"""
        data = jsontools.read_from_path(self.meta_path)
        return data if isinstance(data, dict) else {}

    def _save_meta(self, meta: dict) -> None:
        self.dir_path.mkdir(parents=True, exist_ok=True)
        jsontools.save_to_path(self.meta_path, meta, ensure_ascii=False, indent=2)

    def exists(self) -> bool:
        return self.meta_path.exists()

    @classmethod
    def exists_code(cls, code: str) -> bool:
        return cls(code).exists()

    # ---------- 展示字段（均容忍空 meta） ----------

    @property
    def owner(self):
        return self.meta.get("owner")

    @property
    def title(self) -> str:
        return self.meta.get("title") or DEFAULT_SHARED_TITLE

    @property
    def members(self) -> list[dict]:
        return list(self.meta.get("members") or [])

    @property
    def member_ids(self) -> list:
        return [m.get("user_id") for m in self.members]

    @property
    def requests(self) -> list[dict]:
        return list(self.meta.get("requests") or [])

    @property
    def blocked(self) -> list:
        return list(self.meta.get("blocked") or [])

    @property
    def count(self) -> int:
        """历史记录条数（与 AISession.count 同语义）。"""
        return len(self.load_history())

    # ---------- 成员/请求/屏蔽判定 ----------

    def is_owner(self, user_id) -> bool:
        return user_id == self.owner

    def is_member(self, user_id) -> bool:
        return user_id in self.member_ids

    def is_blocked(self, user_id) -> bool:
        return user_id in self.blocked

    def is_full(self) -> bool:
        return len(self.members) >= MAX_SHARED_MEMBERS

    # ---------- 历史存取（与 AISession 同接口） ----------

    def load_history(self) -> list[dict]:
        data = jsontools.read_from_path(self.history_path)
        return data if isinstance(data, list) else []

    def save_history(self, items: list[dict]) -> None:
        self.dir_path.mkdir(parents=True, exist_ok=True)
        jsontools.save_to_path(self.history_path, items, ensure_ascii=False, indent=2)

    # ---------- 创建 ----------

    @classmethod
    def next_code(cls) -> str | None:
        """下一个群号码（现有最大数字 +1，AI0000 起）；号码空间耗尽返回 None。"""
        max_n = -1
        root = _shared_root()
        if root.is_dir():
            for item in root.iterdir():
                if item.is_dir() and is_valid_code(item.name):
                    max_n = max(max_n, int(item.name[len(SHARED_CODE_PREFIX):]))
        n = max_n + 1
        if n > SHARED_CODE_MAX_N:
            return None
        return f"{SHARED_CODE_PREFIX}{n:0{SHARED_CODE_WIDTH}d}"

    @classmethod
    def create(cls, owner_id, title: str = DEFAULT_SHARED_TITLE,
               history_items: list[dict] | None = None) -> "SharedSession | None":
        """创建共享会话（群主自动成为 1 号成员）；号码空间耗尽返回 None。

        history_items 用于"复制普通会话为共享"场景，直接作为初始历史写入。
        """
        code = cls.next_code()
        if code is None:
            return None
        s = cls(code)
        s._save_meta({
            "code": code,
            "title": (title or "").strip() or DEFAULT_SHARED_TITLE,
            "owner": owner_id,
            "admins": [],  # 预留：管理员扩展位
            "created_time": get_time_now(),
            "members": [{"user_id": owner_id, "joined_time": get_time_now()}],
            "requests": [],
            "blocked": [],
        })
        s.save_history(list(history_items or []))
        return s

    # ---------- 状态变更（读改写回） ----------

    def add_request(self, user_id, time_str: str) -> None:
        """新增/刷新该用户的加入请求（同一用户只保留一条，刷新请求时间）。"""
        meta = self.meta
        requests = [r for r in (meta.get("requests") or []) if r.get("user_id") != user_id]
        requests.append({"user_id": user_id, "time": time_str})
        meta["requests"] = requests
        self._save_meta(meta)

    def latest_request_time(self, user_id) -> str | None:
        """该用户最近一次（待处理）请求的时间；无请求返回 None。"""
        for r in self.requests:
            if r.get("user_id") == user_id:
                return r.get("time")
        return None

    def pop_request(self, index: int) -> dict | None:
        """移除指定序号（1 起）的待处理请求并返回它；序号非法返回 None。"""
        meta = self.meta
        requests = list(meta.get("requests") or [])
        if not 1 <= index <= len(requests):
            return None
        removed = requests.pop(index - 1)
        meta["requests"] = requests
        self._save_meta(meta)
        return removed

    def approve_request(self, index: int) -> dict | None:
        """通过指定序号的请求：请求移入成员列表并返回该请求。

        成员已满或序号非法时不做任何改动、返回 None（满员由调用方提前判定并提示）。
        """
        meta = self.meta
        requests = list(meta.get("requests") or [])
        members = list(meta.get("members") or [])
        if not 1 <= index <= len(requests) or len(members) >= MAX_SHARED_MEMBERS:
            return None
        request = requests.pop(index - 1)
        members.append({"user_id": request.get("user_id"), "joined_time": get_time_now()})
        meta["requests"] = requests
        meta["members"] = members
        self._save_meta(meta)
        return request

    def add_blocked(self, user_id) -> None:
        meta = self.meta
        blocked = list(meta.get("blocked") or [])
        if user_id in blocked:
            return
        blocked.append(user_id)
        meta["blocked"] = blocked
        self._save_meta(meta)

    def remove_member(self, user_id) -> bool:
        """移除成员；不能移除群主，目标不是成员时返回 False。"""
        meta = self.meta
        members = list(meta.get("members") or [])
        if user_id == meta.get("owner"):
            return False
        remaining = [m for m in members if m.get("user_id") != user_id]
        if len(remaining) == len(members):
            return False
        meta["members"] = remaining
        self._save_meta(meta)
        return True

    def rename(self, new_title: str) -> bool:
        """重命名共享会话：只更新 meta 的 title 展示字段，不动目录文件名。

        与普通会话（名字=文件名，改名=移动文件）不同；空标题或超过
        SESSION_NAME_MAX_LEN 返回 False。
        """
        new_title = (new_title or "").strip()
        if not new_title or len(new_title) > SESSION_NAME_MAX_LEN:
            return False
        meta = self.meta
        meta["title"] = new_title
        self._save_meta(meta)
        return True


# ---------- 用户侧状态（.joined / .current_shared） ----------

def joined_codes(user_id) -> list[str]:
    """用户已加入的共享会话群号码列表（文件行序即 a 序号）。"""
    try:
        lines = _user_state_file(user_id, JOINED_FILE).read_text(encoding="utf-8").splitlines()
    except Exception:
        return []
    return [line.strip() for line in lines if line.strip()]


def _write_joined(user_id, codes: list[str]) -> None:
    path = _user_state_file(user_id, JOINED_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(codes), encoding="utf-8")


def add_joined(user_id, code: str) -> bool:
    """把群号码记入用户已加入列表；重复或已达上限返回 False。"""
    codes = joined_codes(user_id)
    if code in codes or len(codes) >= MAX_JOINED_SHARED:
        return False
    codes.append(code)
    _write_joined(user_id, codes)
    return True


def remove_joined(user_id, code: str) -> None:
    """把群号码从用户已加入列表移除（不存在时静默）。"""
    codes = [c for c in joined_codes(user_id) if c != code]
    _write_joined(user_id, codes)


def shared_by_a_index(user_id, index: int) -> SharedSession | None:
    """按 a 序号（1 起）取用户已加入的共享会话；越界或会话已被删除返回 None。"""
    codes = joined_codes(user_id)
    if not 1 <= index <= len(codes):
        return None
    s = SharedSession(codes[index - 1])
    return s if s.exists() else None


def current_shared(user_id) -> SharedSession | None:
    """用户当前所处的共享会话；未处于共享模式、会话已删除或已不是成员时返回 None。"""
    try:
        code = _user_state_file(user_id, CURRENT_SHARED_FILE).read_text(encoding="utf-8").strip()
    except Exception:
        return None
    if not code:
        return None
    s = SharedSession(code)
    if not s.exists() or not s.is_member(user_id):
        return None
    return s


def set_current_shared(user_id, code: str | None) -> None:
    """设置共享模式指针；code=None 表示退出共享模式（删除指针文件）。"""
    path = _user_state_file(user_id, CURRENT_SHARED_FILE)
    if code is None:
        path.unlink(missing_ok=True)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(code, encoding="utf-8")


def clear_current_shared_if(user_id, code: str) -> bool:
    """共享指针正指向 code 时清除它（被踢/退出场景），返回是否清除。"""
    try:
        current = _user_state_file(user_id, CURRENT_SHARED_FILE).read_text(encoding="utf-8").strip()
    except Exception:
        return False
    if current == code:
        set_current_shared(user_id, None)
        return True
    return False


def leave_all(user_id) -> int:
    """把用户从所有共享会话中移除并清空本侧状态（清空数据时联动清理）。

    返回处理过的共享会话数；注意要在外部删除 .joined 之前调用。
    """
    count = 0
    for code in joined_codes(user_id):
        s = SharedSession(code)
        if s.exists():
            s.remove_member(user_id)
            count += 1
    set_current_shared(user_id, None)
    _write_joined(user_id, [])
    return count
