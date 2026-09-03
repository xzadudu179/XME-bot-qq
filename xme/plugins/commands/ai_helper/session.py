# Made by Deepseek-v4-flash-vison-exp at Deepseek Harness
from pathlib import Path

from xme.xmetools.filetools import is_safe_custom_name
from . import history
from .constants import MAX_SESSIONS, SESSION_NAME_MAX_LEN

# 用户目录下的状态文件（clear_all_history 清理目录时会一并移除）
CURRENT_SESSION_FILE = ".current"   # 当前 AI 会话指针
LOCKED_FILE = ".locked"             # 用户命名过的会话名（每行一个，AI 不可修改）

DEFAULT_SESSION = history.DEFAULT_SESSION


def _user_dir(user_id) -> Path:
    return history.user_dir(user_id)


def _read_locked(user_id) -> set[str]:
    """读取用户命名过（AI 不可修改）的会话名集合。"""
    try:
        return {line.strip() for line in
                (_user_dir(user_id) / LOCKED_FILE).read_text(encoding="utf-8").splitlines()
                if line.strip()}
    except Exception:
        return set()


def _write_locked(user_id, names: set[str]) -> None:
    user_dir = _user_dir(user_id)
    user_dir.mkdir(parents=True, exist_ok=True)
    (user_dir / LOCKED_FILE).write_text("\n".join(sorted(names)), encoding="utf-8")


def _add_locked(user_id, ai_session) -> None:
    names = _read_locked(user_id)
    names.add(ai_session)
    _write_locked(user_id, names)


def _remove_locked(user_id, ai_session) -> None:
    names = _read_locked(user_id)
    if ai_session in names:
        names.discard(ai_session)
        _write_locked(user_id, names)


def _read_current(user_id) -> str:
    """读取用户当前 AI 会话名；未设置/损坏时返回默认会话。"""
    try:
        return (_user_dir(user_id) / CURRENT_SESSION_FILE).read_text(encoding="utf-8").strip() or DEFAULT_SESSION
    except Exception:
        return DEFAULT_SESSION


def _write_current(user_id, ai_session) -> None:
    user_dir = _user_dir(user_id)
    user_dir.mkdir(parents=True, exist_ok=True)
    (user_dir / CURRENT_SESSION_FILE).write_text(ai_session, encoding="utf-8")


class AISession:
    """单个 AI 会话对象：封装会话名、历史存储、转存文件夹、命名锁与当前指针等操作。

    - ai_session：会话名（形参/属性统一叫 ai_session，避免与 bot 指令 session 混淆）
    - 命名锁：用户手动命名过的会话标记为 AI 不可修改（name / new 带名字时会加锁）
    """

    def __init__(self, user_id, ai_session=DEFAULT_SESSION):
        self.user_id = user_id
        self.ai_session = ai_session or DEFAULT_SESSION

    # ---------- 基础属性 ----------

    @property
    def is_default(self) -> bool:
        """是否默认会话。"""
        return self.ai_session == DEFAULT_SESSION

    @property
    def json_path(self) -> Path:
        """历史文件路径：data/ai_historys/<用户id>/<会话>.json"""
        return _user_dir(self.user_id) / f"{self.ai_session}.json"

    @property
    def dir_path(self) -> Path:
        """转存文件目录：data/ai_historys/<用户id>/<会话>/"""
        return history.session_dir(self.user_id, self.ai_session)

    @property
    def count(self) -> int:
        """历史记录条数（摘要条目也算）。"""
        return len(self.load_history())

    @property
    def created_time(self) -> float:
        """建立时间：历史文件和转存文件夹里更早的时间戳。"""
        times = []
        for p in (self.json_path, self.dir_path):
            try:
                if p.exists():
                    times.append(p.stat().st_mtime)
            except OSError:
                pass
        return min(times) if times else 0

    def exists(self) -> bool:
        """会话是否已存在（有历史文件或转存文件夹）。"""
        return self.json_path.exists() or self.dir_path.is_dir()

    def is_locked(self) -> bool:
        """是否用户命名过（AI 不可修改）。"""
        return self.ai_session in _read_locked(self.user_id)

    def lock(self) -> None:
        """标记为 AI 不可修改（用户命名）。"""
        _add_locked(self.user_id, self.ai_session)

    def unlock(self) -> None:
        """取消 AI 不可修改标记。"""
        _remove_locked(self.user_id, self.ai_session)

    # ---------- 历史存取 ----------

    def load_history(self) -> list[dict]:
        return history.load_history(self.user_id, self.ai_session)

    def save_history(self, items: list[dict]) -> None:
        history.save_history(self.user_id, items, self.ai_session)

    def clear(self) -> tuple[int, int]:
        """清空会话内容（历史文件 + 转存文件夹），返回 (删除的历史文件数, 删除的转存文件数)。"""
        return (history.clear_history(self.user_id, self.ai_session),
                history.clear_session_files(self.user_id, self.ai_session))

    # ---------- 生命周期 ----------

    def delete(self) -> int:
        """删除会话（历史文件 + 转存文件夹），返回删除文件数；删除的是当前会话时指针切回默认。"""
        if self.is_default:
            raise ValueError("默认会话不可删除")
        is_current = AISession.current(self.user_id).ai_session == self.ai_session
        cleared = history.clear_history(self.user_id, self.ai_session) + history.clear_session_files(self.user_id, self.ai_session)
        _remove_locked(self.user_id, self.ai_session)
        if is_current:
            _write_current(self.user_id, DEFAULT_SESSION)
        return cleared

    def rename(self, new_name, lock=False) -> bool:
        """重命名会话（历史文件 + 转存文件夹一起移动）。

        lock=True 时新名字标记为 AI 不可修改（用户命名）；若原名已锁定，锁随会话转移到新名。
        默认会话不可重命名（用 promote_default）。
        """
        if self.is_default or not self.is_valid_name(new_name) or new_name == self.ai_session:
            return False
        if not self.exists() or AISession(self.user_id, new_name).exists():
            return False
        was_locked = self.is_locked()
        is_current = AISession.current(self.user_id).ai_session == self.ai_session
        old_name = self.ai_session
        try:
            if self.json_path.exists():
                self.json_path.rename(AISession(self.user_id, new_name).json_path)
            if self.dir_path.exists():
                self.dir_path.rename(AISession(self.user_id, new_name).dir_path)
        except OSError:
            return False
        # 锁随会话走：旧名解锁（若之前锁定），新名按需加锁
        locked = _read_locked(self.user_id)
        locked.discard(old_name)
        if was_locked or lock:
            locked.add(new_name)
        _write_locked(self.user_id, locked)
        if is_current:
            _write_current(self.user_id, new_name)
        self.ai_session = new_name
        return True

    def set_current(self) -> None:
        """把当前会话指针指向本会话。"""
        _write_current(self.user_id, self.ai_session)

    # ---------- 类级操作 ----------

    @staticmethod
    def is_valid_name(name: str) -> bool:
        """校验会话名：安全字符（filetools 单点校验）+ 非默认保留名 + 不以 history_ 开头。最多 20 字"""
        if len(name) > SESSION_NAME_MAX_LEN:
            return False
        return (isinstance(name, str) and is_safe_custom_name(name)
                and name != DEFAULT_SESSION and not name.startswith("history_"))

    @staticmethod
    def next_auto_name(user_id) -> str:
        """生成一个不重复的自动会话名（会话1、会话2...）。"""
        existing = {s.ai_session for s in AISession.all(user_id)}
        index = 1
        while f"会话{index}" in existing:
            index += 1
        return f"会话{index}"

    @classmethod
    def all(cls, user_id) -> list["AISession"]:
        """某用户的所有会话对象；默认会话永远在第一位（序号 1），其余按建立时间排序。"""
        names = {DEFAULT_SESSION}
        user_dir = _user_dir(user_id)
        if user_dir.is_dir():
            for item in user_dir.iterdir():
                if item.is_file() or item.is_symlink():
                    # <会话名>.json 历史文件；.current/.locked 等状态文件不带 .json 后缀，自然跳过
                    if item.suffix == ".json" and item.stem:
                        names.add(item.stem)
                elif item.is_dir():
                    if not item.name.startswith("."):
                        names.add(item.name)
        names.discard(DEFAULT_SESSION)
        others = sorted(names, key=lambda n: cls(user_id, n).created_time)
        return [cls(user_id, DEFAULT_SESSION), *[cls(user_id, n) for n in others]]

    @classmethod
    def current(cls, user_id) -> "AISession":
        """当前会话对象；指针未设置/损坏/指向已删除会话时，回落到默认会话。"""
        name = _read_current(user_id)
        s = cls(user_id, name)
        if not s.is_default and not s.exists():
            return cls(user_id, DEFAULT_SESSION)
        return s

    @classmethod
    def create(cls, user_id, ai_session, lock=False) -> "AISession":
        """创建新会话（空历史文件 + 转存文件夹）；已存在/名字非法/会话数达上限抛 ValueError。"""
        if not cls.is_valid_name(ai_session):
            raise ValueError(f"会话名 {ai_session} 不合法")
        s = cls(user_id, ai_session)
        if s.exists():
            raise ValueError("会话已存在")
        if len(cls.all(user_id)) >= MAX_SESSIONS:
            raise ValueError(f"会话数量已达上限（{MAX_SESSIONS} 个）")
        history.save_history(user_id, [], ai_session)
        s.dir_path.mkdir(parents=True, exist_ok=True)
        if lock:
            s.lock()
        return s

    @classmethod
    def promote_default(cls, user_id, new_name, lock=False) -> "AISession | None":
        """把默认会话提升为命名会话：默认内容（历史+转存文件）整体搬到新会话，默认会话复位为空。

        成功返回新会话对象，目标名非法/已存在返回 None；lock=True 时新会话标记为 AI 不可修改。
        """
        if not cls.is_valid_name(new_name) or cls(user_id, new_name).exists():
            return None
        user_dir = _user_dir(user_id)
        user_dir.mkdir(parents=True, exist_ok=True)
        default = cls(user_id, DEFAULT_SESSION)
        new = cls(user_id, new_name)
        if default.exists():
            try:
                if default.json_path.exists():
                    default.json_path.rename(new.json_path)
                if default.dir_path.exists():
                    default.dir_path.rename(new.dir_path)
            except OSError:
                return None
        else:
            # 默认会话还没有内容，直接创建一个空的新会话
            history.save_history(user_id, [], new_name)
            new.dir_path.mkdir(parents=True, exist_ok=True)
        _write_current(user_id, new_name)
        if lock:
            new.lock()
        return new
