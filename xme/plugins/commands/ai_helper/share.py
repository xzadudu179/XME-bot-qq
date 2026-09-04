"""共享会话：多用户共享同一个 AI 会话（群主/成员/加入审批/对话锁）。

存储布局（data/ai_historys/ 下单开 shared 目录，与各用户目录平级）：
    shared/.global_meta.json       全局状态（{"next_code_n": N} 群号码水位，只增不减：
                                   分配过的号码永不复用，防弃用群的旧邀请串到新会话）
    shared/<群号码>/history.json   共享历史（与普通会话完全同格式）
    shared/<群号码>/meta.json      {code, title, owner, admins, created_time,
                                    members:[{user_id, joined_time}], requests:[{user_id, time}], blocked}
    <用户id>/.joined               已加入的共享会话群号码（每行一个，顺序即 a 序号 a1、a2...）

当前会话指针与普通会话共用同一个 .current（统一指针，解析见 session.current_storage）。

与 AISession 的关系：SharedSession 提供 ai_session/load_history/save_history/
count/dir_path 等同名接口（鸭子类型），agent 层通过 AIHelper.storage 统一读写，
不感知具体类型；两者互不 import（本模块只依赖 history 的路径函数）。

与普通会话的关键差异：目录以群号码命名，"改名"只更新 meta 里的 title 展示字段，
不涉及文件移动（普通会话名字即文件名，改名=移动文件）。
"""
import shutil
from pathlib import Path

from xme.xmetools import jsontools
from xme.xmetools.timetools import get_time_now

from . import history
from .constants import (
    DEFAULT_SHARED_TITLE,
    JOINED_FILE,
    MAX_JOINED_SHARED,
    MAX_SHARED_MEMBERS,
    SESSION_NAME_MAX_LEN,
    SHARED_CODE_MAX_N,
    SHARED_CODE_PREFIX,
    SHARED_CODE_WIDTH,
    SHARED_DIR_NAME,
    SHARED_GLOBAL_META_FILE,
    SHARED_HISTORY_FILE,
    SHARED_META_FILE,
)

# 对话忙表：{群号码: True}。有人在某共享会话调用 AI 期间其他成员被拒。
# 与 __init__.py 的 curr_sessions 同模式：检查与置位之间无 await，asyncio 单线程下原子。
_busy_codes: dict[str, bool] = {}


def _shared_root() -> Path:
    """共享会话根目录（运行时从 HISTORY_ROOT 派生，便于测试时整体替换）。"""
    return history.HISTORY_ROOT / SHARED_DIR_NAME


def _watermark_path() -> Path:
    """群号码水位文件：shared/.global_meta.json（{"next_code_n": N}，N 只增不减）。"""
    return _shared_root() / SHARED_GLOBAL_META_FILE


def used_code_watermark() -> int:
    """群号码水位：[0, N) 的号码一律视为已占用（含已删除会话的号，永不复用）。

    文件缺失/损坏/负数时返回 0（退化为纯目录扫描，现存目录仍不会被复用）。
    """
    data = jsontools.read_from_path(_watermark_path())
    n = data.get("next_code_n") if isinstance(data, dict) else None
    return n if isinstance(n, int) and n >= 0 else 0


def _raise_watermark_to(n: int) -> None:
    """把水位抬到 n（只增不减；低于当前水位时静默）。"""
    if n <= used_code_watermark():
        return
    _watermark_path().parent.mkdir(parents=True, exist_ok=True)
    jsontools.save_to_path(_watermark_path(), {"next_code_n": n})


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

    def clear(self) -> tuple[int, int]:
        """清空共享会话内容：历史置空 + 删除转存文件（保留 meta.json/history.json 骨架）。

        会话本身与成员关系保持不变（区别于 delete 的整体删除）。
        返回 (是否有历史 1/0, 删除的转存文件数)；转存子目录按 1 个计。
        """
        had_history = 1 if self.load_history() else 0
        removed = 0
        if self.dir_path.is_dir():
            for item in self.dir_path.iterdir():
                if item in (self.meta_path, self.history_path):
                    continue
                if item.is_file() or item.is_symlink():
                    item.unlink()
                    removed += 1
                elif item.is_dir():
                    shutil.rmtree(item)
                    removed += 1
        if had_history:
            self.save_history([])
        return had_history, removed

    def delete(self) -> int:
        """删除整个共享会话目录（meta/历史/转存文件，requests 名单随 meta 一并消失），
        返回删除的文件数。水位抬到自己之上（号码永不复用；兼容水位上线前创建的会话）。
        调用方负责先取成员/申请者名单并做用户侧清理与通知。"""
        _raise_watermark_to(int(self.code[len(SHARED_CODE_PREFIX):]) + 1)
        if not self.dir_path.is_dir():
            return 0
        removed = sum(1 for _ in self.dir_path.rglob("*") if _.is_file())
        shutil.rmtree(self.dir_path)
        return removed

    # ---------- 创建 ----------

    @classmethod
    def next_code(cls) -> str | None:
        """下一个群号码：从水位线起找第一个不存在目录的号。

        水位线以下的号码一律视为已占用（删除的号永不复用，防旧邀请串群）；
        水位线以上的残留目录（如手动建的）会被跳过并在 create 时收入水位。
        号码空间耗尽返回 None。
        """
        n = used_code_watermark()
        root = _shared_root()
        while n <= SHARED_CODE_MAX_N:
            if not (root / f"{SHARED_CODE_PREFIX}{n:0{SHARED_CODE_WIDTH}d}").is_dir():
                return f"{SHARED_CODE_PREFIX}{n:0{SHARED_CODE_WIDTH}d}"
            n += 1
        return None

    @classmethod
    def create(cls, owner_id, title: str = DEFAULT_SHARED_TITLE,
               history_items: list[dict] | None = None) -> "SharedSession | None":
        """创建共享会话（群主自动成为 1 号成员）；号码空间耗尽返回 None。

        history_items 用于"复制普通会话为共享"场景，直接作为初始历史写入。
        号码分配后把水位抬到其上一位（删除不复用，防旧邀请串群）。
        """
        code = cls.next_code()
        if code is None:
            return None
        _raise_watermark_to(int(code[len(SHARED_CODE_PREFIX):]) + 1)
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


# ---------- 用户侧状态（.joined；当前会话走统一指针，见 session.current_storage） ----------

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


def reset_current_if(user_id, code: str) -> bool:
    """用户当前指针（统一指针）正指向该共享会话时复位为默认会话。

    用于被踢/退出/会话删除后，避免指针悬在失效的群号码上；返回是否复位。
    """
    if history.read_current(user_id) == code:
        history.write_current(user_id, history.DEFAULT_SESSION)
        return True
    return False


def detach_users(code: str, user_ids) -> None:
    """把一批用户与共享会话解除关联：清各自的 .joined 记录与指向该会话的指针。

    用于会话被删除后批量清理（成员与待审申请者）；用户不存在/无记录时静默。
    """
    for uid in user_ids:
        if uid is None:
            continue
        remove_joined(uid, code)
        reset_current_if(uid, code)


def leave_shared(s: SharedSession, user_id) -> bool:
    """把用户退出共享会话：移除成员名单并清理其用户侧状态（.joined 与共享指针）。

    群主不可退出（避免产生无群主的孤儿会话），非成员返回 False；kick 与 leave 共用。
    """
    if not s.remove_member(user_id):
        return False
    remove_joined(user_id, s.code)
    reset_current_if(user_id, s.code)
    return True


def leave_all(user_id) -> int:
    """把用户从所有共享会话中移除并清空本侧状态（清空数据时联动清理）。

    群主身份的会话不移除（避免孤儿会话），仅清普通成员身份。
    返回处理过的共享会话数；注意要在外部删除 .joined 之前调用。
    """
    count = 0
    for code in joined_codes(user_id):
        s = SharedSession(code)
        if s.exists():
            s.remove_member(user_id)
            count += 1
    # 统一指针复位为默认会话（可能正指向某个共享会话）
    history.write_current(user_id, history.DEFAULT_SESSION)
    _write_joined(user_id, [])
    return count
