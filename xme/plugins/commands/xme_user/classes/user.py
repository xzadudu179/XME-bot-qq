from character import get_message
coin_name = get_message("user", "coin_name")
coin_pronoun = get_message("user", "coin_pronoun")

import time  # noqa: E402
from datetime import datetime # noqa: E402
from xme.xmetools import timetools # noqa: E402
from xme.xmetools import dicttools # noqa: E402
from .achievements import get_achievements, has_achievement # noqa: E402
from nonebot.session import BaseSession # noqa: E402
from functools import wraps # noqa: E402
from aiocqhttp import ActionFailed # noqa: E402
import json # noqa: E402
from types import FunctionType # noqa: E402
from xme.xmetools.dicttools import get_value # noqa: E402
from xme.xmetools.msgtools import send_to_superusers # noqa: E402
from nonebot import get_bot # noqa: E402
# from ..tools.map_tools import ImageDraw, draw_text_on_image, mark_point # noqa: E402
import inspect # noqa: E402
import asyncio # noqa: E402
# from xme.xmetools.imgtools import hash_image # noqa: E402
import math # noqa: E402
from xme.xmetools.msgtools import send_session_msg # noqa: E402
from .inventory import Inventory # noqa: E402
from xme.xmetools.debugtools import debug_msg # noqa: E402
from nonebot.log import logger # noqa: E402
# from .xme_map import get_galaxymap # noqa: E402
from xme.xmetools.dbtools import DATABASE, adapt_value, add, diff_json, merge_patch # noqa: E402


# flush() 里的「无变化」哨兵：与合法值 None 区分开
_UNCHANGED = object()


def _parsed(raw):
    """把库里的原始值解析成 Python 结构用于比较（JSON 列是字符串；解析失败原样返回）。"""
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except ValueError:
            return raw
    return raw


def _is_number(value) -> bool:
    """是否为可参与增减的数值（bool 排除在外，它入库后是 int 但不该按增量处理）。"""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


# def is_galaxy_loaded():
#     if get_galaxymap():
#         return True
#     return False

# def is_galaxy_initing():
#     return galaxy_initing

class User:
    # 增量语义的数值列：flush 写回的是「本对象相对加载时的净变化」（col = col + ?），
    # 并发下各自的金币/好感度增减会正确叠加；其余列一律绝对写，
    # 「绝对赋值」的意图（如管理员把金币清零）由调用方用 replace_field 声明
    _DELTA_COLUMNS = ("coins", "xme_favorability")

    def form_dict(data: dict):
        return load_from_dict(data, id=data["user_id"])

    @classmethod
    def get_table_name(cls):
        return User.__name__

    async def try_spend(self, session: BaseSession, count, out_of_range_zero=False, no_coin_message="", spent_message=""):
        if count < 0:
            raise ValueError(f"花费的{coin_name}不能小于 0")
        if self.coins < count:
            await send_session_msg(session, (get_message("user", "no_coin", count=count) if not no_coin_message else no_coin_message.format(count=count)))
            return False
        r, spend = self.spend_coins(count, out_of_range_zero)
        if r:
            await send_session_msg(session, (get_message("user", "spent_coin", count=spend) if not spent_message else spent_message.format(count=spend)))
            return True
        return False

    async def get_coins(self, session: BaseSession, count, _get_message=""):
        count = int(count)
        if count < 0:
            raise ValueError(f"获得的{coin_name}不能小于 0")
        # if self.coins < count:
        #     await send_session_msg(session, (get_message("user", "no_coin", count=count) if not message else message))
        #     return False
        r = self.add_coins(count)
        if r:
            await send_session_msg(session, (get_message("user", "get_coin", count=count) if not _get_message else _get_message))
            return True
        return False

    def record_call(self):
        self.last_call_time = time.time()
        DATABASE.update_db(obj=self, id=self.db_id, last_call_time=self.last_call_time)

    def update(self, *objects):
        # updates = {o: getattr(self, o) for o in objects}
        updates = {}
        for o in objects:
            attr = getattr(self, o)
            if isinstance(attr, dict):
                attr = json.dumps(attr)
            updates[o] = attr
        DATABASE.update_db(obj=self, id=self.db_id, **updates)

    def __init__(
            self,
            user_id: int,
            db_id: int = -1,
            coins: int = 0,
            inventory: Inventory | None = None,
            talked_to_bot: list | None = None,
            desc: str = "",
            afdian_id = "",
            xme_favorability=0,
            counters: dict | None = None,
            # timers: dict = {},
            plugin_datas: dict | None = None, # 插件数据，比如 weather 保存用户位置之类的
            achievements: list | None = None,
            last_call_time: float | None = None,
        ):
        self.db_id: int = db_id
        self.id: int = user_id
        # 加载时的原始行值（由 DATABASE.load_class 注入）：flush 据此只写变化的部分
        self._loaded_row: dict = {}
        # 执行中的限流占位（try_use_limit 登记、命令结束时注销）：命令内部读
        # get_limit_info 要把它扣掉，剩余次数的口径才与占位之前一致
        self._limit_pending: dict = {}
        self.desc: str = desc
        self.afdian_id: str = afdian_id
        # avoid shared mutable defaults
        self.inventory: Inventory = inventory if inventory is not None else Inventory()
        self.coins: int = coins
        self.xme_favorability: int = xme_favorability
        self.talked_to_bot: list = talked_to_bot if talked_to_bot is not None else []
        self.counters: dict = counters if counters is not None else {}
        self.plugin_datas: dict = plugin_datas if plugin_datas is not None else {}
        # 上次调用漠月的时间
        self.last_call_time: float = last_call_time if last_call_time is not None else 0
        # self.timers = timers
        # 注册时间
        # datas = self.plugin_datas.get("datas", {})
        # reg_time = datas.get("register_time", -1)

        self.achievements: list = achievements if achievements is not None else []
        # 用户所在天体
        # debug_msg("dbid", self.db_id)
        # self.celestial_uid = celestial_uid
        # self.celestial = None
        self.get_reg_time()
        # if reg_time == -1:
        #     self.plugin_datas["datas"] = {}
        #     self.plugin_datas["datas"]["register_time"] = time.time()
        #     self.save()
        # self.reg_time = self.plugin_datas["datas"]["register_time"]

    def get_reg_time(self):
        time_now = time.time()
        v: float | None = dicttools.get_value("datas", "register_time", search_dict=self.plugin_datas)
        if v is None:
            dicttools.set_value("datas", "register_time", search_dict=self.plugin_datas, set_method=lambda _: time_now)
            # self.reg_time = time_now
            self.save()
            return time_now
        return v


    def get_achievement(self, achievement_name) -> dict | bool:
        # debug_msg("achievement_name:", achievement_name)
        achi = get_achievements().get(achievement_name, False)
        if not achi:
            raise ValueError(f"无该成就名 \"{achievement_name}\"")
        for a in self.achievements:
            if achievement_name in a["name"]:
                return a
        return None

    async def achieve_achievement(self, session: BaseSession, achievement_name: str, achievement_message: str | None = None):
        """达成成就

        Args:
            user (User): 用户
            achievement_name (str): 成就名
        """
        achi = get_achievements().get(achievement_name, False)
        if not achi:
            raise ValueError(f"无该成就名 \"{achievement_name}\"")
        if achievement_name in [a["name"] for a in self.achievements]:
            # 已经有成就就不管了
            debug_msg("已达成成就，不执行")
            return
        self.achievements.append({
            "name": achievement_name,
            "achieve_time": timetools.get_time_now(),
            "from": str(session.event.group_id) if session.event.group_id is not None else "私聊"
        })
        self.add_coins(achi["award"])
        if achievement_message is None:
            if not achi["hidden"]:
                achievement_message = get_message("config", "achievement_message", achievement=achievement_name, award=achi["award"])
            else:
                achievement_message = get_message("config", "hidden_achievement_message", achievement=achievement_name, award=achi["award"])
        try:
            await send_to_superusers(session.bot, f"用户 {(await session.bot.api.get_stranger_info(user_id=self.id))['nickname']} ({self.id}) 在 {(await get_bot().api.get_group_info(group_id=session.event.group_id))['group_name']} 得到了一个成就 \"{achievement_name}\"")
        except ActionFailed:
            pass
        if self.id != -1:
            debug_msg("更新database")
            rows = DATABASE.update_db(obj=self, id=self.db_id, coins=self.coins, achievements=json.dumps(self.achievements, ensure_ascii=False))
            debug_msg("受影响的行数:", rows)
        # 发送失败要有上限与退避：bot 被禁言/风控时 ActionFailed 会持续快速失败，
        # 无上限重试会永久挂起该会话并狂刷 OneBot API
        for attempt in range(3):
            try:
                await send_session_msg(session, achievement_message)
                break
            except ActionFailed:
                if attempt < 2:
                    await asyncio.sleep(2)
        else:
            logger.warning(f"成就 {achievement_name} 的通知消息发送失败（已重试 3 次），放弃")

    def __str__(self):
        # debug_msg("self.get_reg_time()", self.get_reg_time())
        try:
            # last_sign_time = time_tools.int_to_days(int(self.counters['sign']["time"]))
            last_sign_time = timetools.int_to_date(int(timetools.get_valuetime(self.counters['sign']["time"], timetools.TimeUnit.DAY)))
            sign_message = get_message("user", "sign_message", last_sign_time=last_sign_time)
        except Exception:
            sign_message = get_message("user", "no_sign")
        _, rank_ratio, _ = get_user_rank(self.id)
        return str(get_message("user", "user_info_str",
            id=str(self.id),
            reg_time=datetime.strftime(datetime.fromtimestamp(self.get_reg_time()), format=r"%Y-%m-%d %H:%M:%S"),
            coins_count=self.coins,
            achievements_count=len([a for a in self.achievements if has_achievement(a.get("name", ""))]),
            get_achievements_total=len(get_achievements().items()),
            sign_message=sign_message,
            rank_ratio=f"{rank_ratio:.2f}",
            space=self.inventory.get_space_left(),
            desc=self.desc + "\n----------\n" if self.desc else ""
        ))

    def add_favorability(self, count):
        """增加好感度

        Args:
            count (int): 好感度值，可为负数
        """
        if self.xme_favorability + count > 100:
            self.xme_favorability = 100
        elif self.xme_favorability + count < -100:
            self.xme_favorability = -100
        else:
            self.xme_favorability += count

    def get_custom_setting(self, *keys, default="default"):
        return dicttools.get_value("custom", *keys, search_dict=self.plugin_datas, default=default)

    def spend_coins(self, amount: int, out_of_range_zero: bool= False) -> tuple[bool, int]:
        """尝试花费星币

        Args:
            amount (int): 花费数量
            out_of_range_zero (bool, optional): 是否如果付不起，就归零. Defaults to False.

        Returns:
            tuple[bool, int]: 是否花费成功, 当前剩余星币
        """
        # out of range zero 如果付不起就算扣到 0
        amount = int(amount)
        if amount > self.coins and not out_of_range_zero:
            return (False, 0)
        coins_now = self.coins
        self.coins -= amount
        if self.coins < 0:
            self.coins = 0
        return (True, coins_now - self.coins)

    def to_dict(self) -> dict:
        return {
            "id": self.db_id,
            "user_id": self.id,
            "coins": self.coins,
            "counters": self.counters,
            # "timers": self.timers,
            "afdian_id": self.afdian_id,
            "xme_favorability": self.xme_favorability,
            "desc": self.desc,
            "plugin_datas": self.plugin_datas,
            "inventory": self.inventory.__list__(),
            "talked_to_bot": self.talked_to_bot,
            "achievements": self.achievements,
            "last_call_time": self.last_call_time,
        }

    def __dict__(self):
        return self.to_dict()

    def add_coins(self, amount: int) -> bool:
        amount = int(amount)
        debug_msg("amount", amount)
        if amount < 0:
            return False
        self.coins += amount
        return True

    def exec_query(query, params=(), dict_data=True):
        # DATABASE.create_class_table(User(0))
        return DATABASE.exec_query(query=query, params=params, dict_data=dict_data)

    @staticmethod
    def get_users() -> list[dict]:
        # return jsontools.read_from_path(config.USER_PATH)['users']
        return [load_dict_user(u) for u in User.exec_query(f"SELECT * FROM {User.get_table_name()}")]

    @staticmethod
    def load(id: int, create_default_user=True):
        c: User = DATABASE.load_class(select_keys=(id,), query='SELECT * FROM {table_name} WHERE user_id = ?', cl=User)
        if c is None and create_default_user:
            debug_msg("创建一个新用户")
            return User(user_id=id)
        elif c is not None:
            c.get_reg_time()
        return c

    @staticmethod
    def load_by_afdian_id(afdian_id: str, create_default_user=False):
        """按爱发电用户 id 加载绑定的用户，未绑定时默认返回 None。"""
        if not afdian_id:
            return None
        c: User = DATABASE.load_class(select_keys=(afdian_id,), query='SELECT * FROM {table_name} WHERE afdian_id = ?', cl=User)
        if c is None and create_default_user:
            return User(user_id=-1)
        return c

    def save(self):
        """整行写入（INSERT OR REPLACE，包含全部列）——会把并发写入的列一起盖掉。

        只在「新建用户」或确实要整行覆盖时使用；日常收尾请用 flush()。
        写完把加载基线一并刷新成刚写入的行，否则后续 flush() 会拿「加载时的旧值」
        当参照：增量列（coins 等）被重复叠加，值为旧值的 JSON 子路径被漏写。
        """
        self.db_id = DATABASE.save_to_db(obj=self)
        self._loaded_row = {k: adapt_value(v) for k, v in self.to_dict().items()}

    def replace_field(self, *columns) -> None:
        """声明这些列要按绝对值写回（覆盖并发写入），供「绝对赋值」语义使用。

        例：管理员把金币清零（把金币设成 0 而不是「减去当前值」）时，光改内存值
        无法与增量区分，需显式声明为整列替换。
        """
        if self.db_id == -1:
            return
        current = self.to_dict()
        updates = {c: adapt_value(current[c]) for c in columns if c in current}
        if updates:
            DATABASE.update_db(obj=self, id=self.db_id, **updates)
            self._loaded_row.update(updates)

    def flush(self) -> int:
        """把本对象相对加载时的改动写回数据库：只写变化的列、JSON 列只写变化的子路径。

        与 save() 的区别（save 是整行 INSERT OR REPLACE，会把并发写入盖掉）：
        - 未变化的列完全不写；
        - 数值增量列（_DELTA_COLUMNS）写 ``col = col + 净变化``，并发增减各自生效
          （本对象读到时是 100、别人加到 200，本对象 +100 → 结果 300）；
        - JSON 列按最小变化子路径用 json_set / json_remove / json_insert 局部更新，
          plugin_datas 下各插件的数据、counters 下各计数器的键互不覆盖；
        - 其余列变化时整列绝对写。

        未入库（db_id 为 -1，如新建用户）或没有加载基线（手工构造）的对象回落到
        save()；返回本次写入的列数。
        """
        if self.db_id == -1 or not self._loaded_row:
            self.save()
            return 1
        updates: dict = {}
        baseline = dict(self._loaded_row)
        for column, current in self.to_dict().items():
            if column in ("id", "user_id") or column not in self._loaded_row:
                continue
            current_raw = adapt_value(current)
            value = self._column_update(column, self._loaded_row[column], current_raw)
            if value is _UNCHANGED:
                continue
            updates[column] = value
            # 基线跟着更新：下一次 flush 只写「这次之后」的新变化，
            # 增量列也不会把同一笔变化重复写第二遍
            baseline[column] = current_raw
        if updates:
            DATABASE.update_db(obj=self, id=self.db_id, **updates)
            self._loaded_row = baseline
        return len(updates)

    def _column_update(self, column: str, loaded_raw, current_raw):
        """算出单列的更新内容：_UNCHANGED / ColumnExpr（表达式）/ 绝对值。"""
        loaded, current = _parsed(loaded_raw), _parsed(current_raw)
        if loaded == current:
            return _UNCHANGED
        if column in self._DELTA_COLUMNS and _is_number(loaded) and _is_number(current):
            return add(current - loaded)
        # JSON 结构尽量只写变化的子路径；无法局部化（类型变了等）则整列绝对写
        expr = diff_json(loaded, current)
        return expr if expr is not None else current_raw


def try_load(id):
    u = User.load(id)
    if u is None:
        logger.info("没有用户，正在尝试创建新用户。")
        u = User(id)
    return u

def _read_counter(user: User, name: str) -> dict:
    """从库里读某计数器的最新值，没有该计数器时返回空 dict。

    限流判定必须基于库里的最新值：同一用户的两次调用各自持有独立的 User 对象，
    对象里的 counters 只是加载时的快照，拿快照判定会让并发调用双双通过。
    """
    rows = User.exec_query(
        f"SELECT counters FROM {User.get_table_name()} WHERE user_id = ?",
        (user.id,), dict_data=True)
    for row in rows:
        counters = _parsed(row.get("counters"))
        counter = counters.get(name) if isinstance(counters, dict) else None
        if isinstance(counter, dict):
            return counter
    return {}


def _limit_decision(counter: dict, interval: float | int, count_limit: int,
                    unit: timetools.TimeUnit, floor_float: bool) -> tuple[bool, dict | None]:
    """判定某计数器的限流状态（纯函数，不写库）。

    Args:
        counter (dict): 计数器当前值 {"time": 上次计时, "count": 已用次数}

    Returns:
        tuple[bool, dict | None]: (是否已达上限, 时间已过期时该重置成的计数器；否则 None)
    """
    time_now = timetools.get_valuetime(timetools.timenow(), unit)
    if floor_float:
        time_now = math.floor(time_now)
    stored_time = counter.get("time", 0) or 0
    count = counter.get("count", 0) or 0
    if time_now - timetools.get_valuetime(stored_time, unit) < interval:
        debug_msg("时间受限制")
        return count >= count_limit, None
    debug_msg("时间过了 刷新")
    reset_time = timetools.timenow()
    return False, {"time": math.floor(reset_time) if floor_float else reset_time, "count": 0}


def _write_counter(user: User, name: str, counter: dict) -> None:
    """把某计数器写回库，并同步到内存对象。

    限流状态不等命令收尾的 flush：中途的整行 save() 会带着旧计数把它盖掉。
    只写这一个子键（merge-patch），同一列里其它计数器不受影响。
    """
    user.counters[name] = dict(counter)
    if user.db_id == -1:
        # 尚未入库（新用户）：随收尾的 save()/flush() 一起落库
        return
    DATABASE.update_db(obj=user, id=user.db_id,
                       counters=merge_patch({name: dict(counter)}))
    if user._loaded_row:
        # 差异基线跟着这次写库走：该计数器在收尾 flush 里不再算「有变化」，
        # 免得被内存快照以绝对值覆盖回去
        baseline = _parsed(user._loaded_row.get("counters"))
        if isinstance(baseline, dict):
            baseline[name] = dict(counter)
            user._loaded_row["counters"] = adapt_value(baseline)


def _mark_limit_pending(user: User, name: str, delta: int = 1) -> None:
    """登记 / 注销本对象上某计数器的「执行中占位」（delta 为 -1 即注销）"""
    pending = user._limit_pending.get(name, 0) + delta
    if pending > 0:
        user._limit_pending[name] = pending
    else:
        user._limit_pending.pop(name, None)


def reset_limit(user: User, name: str, floor_float: bool = True,
                count_add=False):
    """重置计数器：计时归位、计数清零（count_add 为真时清零后再计一次），并写回库。

    Args:
        user (User): 用户
        name (str): 时间限制名
        floor_float (bool, optional): 是否向下取整. Defaults to True.
        count_add (bool, optional): 清零后是否再计一次. Defaults to False.
    """
    time_now = timetools.timenow()
    time_now = time_now if not floor_float else math.floor(time_now)
    _write_counter(user, name, {"time": time_now, "count": 1 if count_add else 0})


def limit_count_tick(user: User, name: str, count=1):
    """给计数器加计数并写回库（count 可为小数，按库里最新值累加）

    Args:
        user (User): 用户
        name (str): 时间限制名
        count (int): 次数. Defaults to 1.
    """
    counter = _read_counter(user, name)
    counter["count"] = (counter.get("count", 0) or 0) + count
    _write_counter(user, name, counter)


def detect_limit(user: User, name: str, interval: float | int, count_limit: int = 1,
                   unit: timetools.TimeUnit = timetools.TimeUnit.DAY, floor_float: bool = True) -> bool:
    """是否已达限制；时间过期时顺手把计数器重置写回

    Args:
        user (User): 用户
        name (str): 时间限制名
        interval (float | int): 限制时间
        count_limit: 限制时间内限制次数 Defaults to 1.
        unit (date_tools.TimeUnit, optional): 时间单位. Defaults to date_tools.TimeUnit.DAY.
        floor_float (bool, optional): 是否向下取整. Defaults to True.

    Returns:
        bool: 是否已受限（True 表示应拦截）
    """
    counter = _read_counter(user, name)
    blocked, reset_value = _limit_decision(counter, interval, count_limit, unit, floor_float)
    if reset_value is not None:
        _write_counter(user, name, reset_value)
    return blocked


def try_use_limit(user: User, name: str, interval: float | int, count_limit: int = 1,
                  unit: timetools.TimeUnit = timetools.TimeUnit.DAY,
                  floor_float: bool = True) -> dict | None:
    """占用一次配额：成功返回占用前的计数器快照（供 release_limit 回滚），已达上限返回 None。

    判定与写库在同步代码里一口气做完（其间不 await），同一进程内同一用户的并发调用
    因此不会双双通过；配额在命令执行前就占住，命令失败的场景由调用方回滚。
    """
    counter = _read_counter(user, name)
    blocked, reset_value = _limit_decision(counter, interval, count_limit, unit, floor_float)
    if blocked:
        return None
    base = reset_value if reset_value is not None else counter
    _write_counter(user, name, {
        "time": base.get("time", 0) or 0,
        "count": (base.get("count", 0) or 0) + 1,
    })
    _mark_limit_pending(user, name)
    return counter


def release_limit(user: User, name: str, snapshot: dict) -> None:
    """回滚一次配额占用（命令未成功时不消耗次数）。snapshot 为 try_use_limit 的返回值。"""
    _write_counter(user, name, {
        "time": snapshot.get("time", 0) or 0,
        "count": snapshot.get("count", 0) or 0,
    })
    _mark_limit_pending(user, name, -1)


def get_limit_info(user, name):
    """返回限制情况

    Args:
        user (User): 用户
        name (str): 时间限制名

    Returns:
        tuple(int | float, int): (当前记录时间, 当前记录次数)
        次数已扣掉本命令执行中的占位，取值与命令开始前一模一样（lottery、
        guess_num 都按「限流器还没给本次计数」的口径算剩余次数）。
    """
    return (
        get_value(name, "time", search_dict=user.counters, default=0),
        get_value(name, "count", search_dict=user.counters, default=0) - user._limit_pending.get(name, 0)
    )
    # return (user.counters[name]["time"], user.counters[name]["count"])


def limit(limit_name: str,
          interval: float | int,
          limit_message: str,
          count_limit: int = 1,
          unit: timetools.TimeUnit = timetools.TimeUnit.DAY,
          floor_float: bool = True,
          fails=lambda x: not x,
          limit_func=None, ):
    """对函数进行限制时间内只能执行数次

    Args:
        limit_name (str): 限制名
        interval (float | int): 多少时间单位后刷新限制
        limit_message (str): 限制时返回的消息
        count_limit (int, optional): 时间内限制次数. Defaults to 1.
        unit (time_tools.TimeUnit, optional): 时间单位. Defaults to time_tools.TimeUnit.DAY.
        floor_float (bool, optional): 是否向下取整时间. Defaults to True.
        fails (func, optional): 函数返回什么会被判定为失败. Defaults to lambda x: not x.
        limit_func (func, optional): 自定义限制时返回的函数. Defaults to None.
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(session, user: User, *args, **kwargs):
            # debug_msg(user.counters)
            # 配额在命令执行前占住：判定与占用都在同步代码内完成，并发调用不会双双通过
            snapshot = try_use_limit(user=user, name=limit_name, interval=interval,
                                     count_limit=count_limit, unit=unit, floor_float=floor_float)
            if snapshot is None:
                if not limit_func:
                    return await send_session_msg(session, limit_message)
                # 有自定义函数传入情况
                elif inspect.iscoroutinefunction(limit_func):
                    return await limit_func(func, session, user, *args, **kwargs)
                else:
                    return limit_func(func, session, user, *args, **kwargs)
            try:
                result = await func(session, user, *args, **kwargs)
            except Exception:
                # 命令抛异常同样不消耗配额
                release_limit(user, limit_name, snapshot)
                raise
            if not fails(result):
                debug_msg("保存用户数据, 增加计数")
                debug_msg("coins", user.coins)
                # 计数器已随占用写库，这里落的是命令本身对用户的改动：
                # flush 只写变化的列 / JSON 子路径，不做整行覆盖（整行 save 会盖掉
                # 期间的并发写入，例如 AI 结算的 credits / 其它指令的金币）
                user.flush()
                # 命令结束，注销占位标记（之后 get_limit_info 才把本次计入）
                _mark_limit_pending(user, limit_name, -1)
            else:
                # 命令没成功，把占住的配额还回去
                release_limit(user, limit_name, snapshot)
            if isinstance(result, str):
                await send_session_msg(session, result)
            return result

        return wrapper

    return decorator

def custom_limit(limit_name: str | FunctionType,
          interval: float | int,
          count_limit: int = 1,
          unit: timetools.TimeUnit = timetools.TimeUnit.DAY,
          floor_float: bool = True,):
    """对函数进行限制时间内只能执行数次，其中判断限制和增加计数由函数自己决定

    Args:
        limit_name (str | FunctionType): 限制名
        interval (float | int): 多少时间单位后刷新限制
        limit_message (str): 限制时返回的消息
        count_limit (int, optional): 时间内限制次数. Defaults to 1.
        unit (time_tools.TimeUnit, optional): 时间单位. Defaults to time_tools.TimeUnit.DAY.
        floor_float (bool, optional): 是否向下取整时间. Defaults to True.
        limit_func (func, optional): 自定义限制时返回的函数. Defaults to None.
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(session, user: User, *args, **kwargs):
            if inspect.isfunction(limit_name):
                name = limit_name(session, user, *args, **kwargs)
            else:
                name = limit_name
            def count_tick(count=1):
                debug_msg("保存用户数据, 增加计数")
                limit_count_tick(user, name, count)
                # 同 custom_limit 收尾：只写变化的计数器子路径
                user.flush()
            def check_invalid():
                if detect_limit(user=user, name=name, interval=interval, count_limit=count_limit, unit=unit,
                              floor_float=floor_float):
                    # 已受限
                    debug_msg("受到限制")
                    return True
                # 未受限
                debug_msg("无限制")
                return False
            result = await func(session, user, check_invalid, count_tick, *args, **kwargs)
            debug_msg(f"result: {result}")
            return result

        return wrapper

    return decorator

def get_user_rank(user):
    """获取指定用户 id 的金币排名百分比以及数量和位置

    Args:
        user (int): 用户 id

    Returns:
        tuple: 金币数量, 排名比例
    """
    rank_items = get_rank('coins', excluding_zero=True)
    sender_coins_count = None
    sender_index = None
    for index, item in enumerate(rank_items):
        if int(item[0]) != user:
            continue
        debug_msg("匹配到了")
        sender_coins_count = item[1]
        sender_index = index
    rank_ratio = 0
    if sender_coins_count is not None:
        rank_ratio = (len(rank_items[sender_index:]) - 1)/ (len(rank_items) - 1) * 100 if len(rank_items[sender_index:]) > 1 else 100
    return sender_coins_count, rank_ratio, sender_index


def get_rank(*rank_item_key, key=None, excluding_zero=False):
    """获取用户某项内容排名

    Args:
        key (Callable[_T, SupportsRichComparison], optional): 排名方法. Defaults to None.

    Returns:
        list[tuple]: 用户: 键对应值
    """
    rank = {}
    # users: dict = jsontools.read_from_path(config.USER_PATH)['users']
    users = User.get_users()
    for v in users:
        # debug_msg(f"item: {v}")
        value = dicttools.get_value(*rank_item_key, search_dict=v)
        if value is None:
            continue
        rank[v["user_id"]] = value
    if excluding_zero:
        rank_values = [r for r in rank.items() if r[1] > 0]
    else:
        rank_values = [r for r in rank.items()]
    # debug_msg(rank_values)
    rank_values.sort(reverse=True, key=lambda x: key(x[1]) if key else x[1])
    # debug_msg(rank)
    return rank_values


def using_user(save_data=False, id=0):
    def decorator(func):
        @wraps(func)
        async def wrapper(session, *args, **kwargs):
            user_id = id
            if not id:
                user_id = session.event.user_id
            debug_msg(user_id)
            user = try_load(user_id)
            result = await func(session, user, *args, **kwargs)
            # debug_msg(f"result: {result}")
            if save_data and result:
                debug_msg("保存用户数据中")
                # 只写本命令真正改动的列/子路径，避免整行覆盖并发写入
                user.flush()
            return result

        return wrapper

    return decorator

def load_dict_user(data: dict):
    inventory_data = None
    # debug_msg(celestial)
    plugin_datas = {}
    counters = {}
    achievements = []
    talked_to_bot = []
    try:
        inventory_data = json.loads(data.get('inventory', None))
        plugin_datas = json.loads(data.get('plugin_datas', "{}"))
        counters = json.loads(data.get('counters', "{}"))
        achievements = data.get('achievements', "[]")
        if achievements is None:
            achievements = "[]"
        achievements = json.loads(achievements)
        talked_to_bot = json.loads(data.get('talked_to_bot', "[]"))
    except Exception as ex:
        logger.error(f"加载用户 {data.get('user_id', '未知')} id:{data.get('id', -1)} 出错")
        raise ex
    # debug_msg(counters)
    # Do NOT instantiate Inventory objects here during bulk loads to avoid
    # creating many InvItem instances which can increase GC pressure.
    # Keep raw inventory data and construct Inventory objects only when
    # loading a single user via load_from_dict.
    inventory = inventory_data
    # debug_msg(data)
    # celestial = data.get('celestial', None)

    return {
            "id": data.get('id', -1),
            "user_id": data["user_id"],
            "coins": data.get('coins', 0),
            "counters": counters,
            "afdian_id": data.get('afdian_id', ""),
            "xme_favorability": data.get('xme_favorability', 0),
            "desc": data.get('desc', ""),
            "plugin_datas": plugin_datas,
            "achievements": achievements,
            "inventory": inventory,
            "talked_to_bot": talked_to_bot,
            # "celestial": celestial,
            "last_call_time": data.get('last_call_time', 0),
    }

def load_from_dict(data: dict, id: int) -> User:
    inventory_data = json.loads(data.get('inventory', None))
    inventory = Inventory()
    # debug_msg(inventory_data)
    if inventory_data:
        inventory = Inventory.get_inventory(inventory_data)
    # debug_msg(data)
    # celestial = data.get('celestial', None)
    # debug_msg("celestial", celestial)
    # debug_msg(celestial)
    counters = json.loads(data.get('counters', "{}"))
    # timers = json.loads(data.get('timers', "{}"))
    # debug_msg(counters)
    achis = data.get('achievements', "[]")
    plugin_datas = json.loads(data.get('plugin_datas', "{}"))
    if not achis:
        achis = "[]"
    user = User(
        db_id=data.get('id', -1),
        user_id=id,
        coins=data.get('coins', 0),
        inventory=inventory,
        afdian_id= data.get("afdian_id", ''),
        talked_to_bot=json.loads(data.get('talked_to_bot', "[]")),
        desc=data.get('desc', ""),
        plugin_datas=plugin_datas,
        achievements=json.loads(achis),
        xme_favorability=data.get('xme_favorability', 0),
        counters=counters,
        # timers=timers,
        last_call_time=data.get('last_call_time', 0)
    )
    # user.counters = data.get('counters', {})
    # user.xme_favorability = data.get('xme_favorability', 0)
    # user.desc = data.get('desc', "")
    return user