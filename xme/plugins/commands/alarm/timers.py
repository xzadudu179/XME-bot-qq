"""计时器登记与触发：登记表 + JSON 存档 + apscheduler 一次性任务 + 到点私聊。

句式预处理与 /alarm 指令共用本模块。全部操作运行在事件循环内，无锁；存档读取
失败/损坏按空表处理。重启时未到期的计时器按原时间重新调度，已错过的在启动宽限
（STARTUP_GRACE_SECS）后补响一次。
"""
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import nonebot
from nonebot.log import logger

from character import get_message
from xme.xmetools import jsontools
from xme.xmetools.bottools import is_friend
from xme.xmetools.mailtools import send_bot_email
from xme.xmetools.msgtools import send_to_user
from xme.xmetools.timetools import RepeatRule, next_repeat_occurrence
from xme.plugins.commands.alarm import __plugin_name__

from .constants import MAX_ACTIVE_PER_USER, MISFIRE_GRACE_SECS, STARTUP_GRACE_SECS, STORE_PATH


def _clock_of(timestamp: float) -> int:
    """时间戳 → 当天的秒数（只比较钟点，用于循环计时器的同名去重）。"""
    dt = datetime.fromtimestamp(timestamp)
    return dt.hour * 3600 + dt.minute * 60 + dt.second


def is_duplicate_reminder(timer: "AlarmTimer", name: str, fire_at: float,
                          repeat: Optional[RepeatRule], tolerance: float) -> bool:
    """已有计时器 timer 和一次新请求（同名/到点/规则）算不算"同一件事的重复登记"。

    去重口径的单点定义：循环与非循环互不算重复；循环之间要规则一致、钟点相差不超过
    tolerance 秒；非循环按到点时间相差不超过 tolerance 秒。存放处（find_duplicate）与
    同一条消息里抽出的候选列表（schedule.pick_candidates）都用这一套。
    """
    if timer.name != name:
        return False
    if (timer.repeat is None) != (repeat is None):
        return False
    if repeat is not None:
        if timer.repeat != repeat:
            return False
        if repeat.unit in ("minute", "hour"):
            # 间隔型自带网格（每5分钟/每小时），规则一致就是同一件事
            return True
        return abs(_clock_of(timer.fire_at) - _clock_of(fire_at)) <= tolerance
    return abs(timer.fire_at - fire_at) <= tolerance


@dataclass
class AlarmTimer:
    """一个已登记的计时器。"""
    user_id: int
    name: str
    fire_at: float          # 到点时间戳（time.time() 口径）；循环计时器存的是"下一次"
    created_at: float
    id: str = ""
    repeat: Optional[RepeatRule] = None     # 循环规则，None 表示只响一次
    paused: bool = False                    # 循环计时器被暂停时为 True（不挂调度，随时可继续）

    @classmethod
    def create(cls, user_id: int, fire_at: float, name: str,
               repeat: Optional[RepeatRule] = None) -> "AlarmTimer":
        """按给定的到点时间戳创建一个新计时器（绝对时间直接存，不做秒级换算）。"""
        return cls(user_id=user_id, name=name, fire_at=fire_at,
                   created_at=time.time(), id=uuid.uuid4().hex[:12], repeat=repeat)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "fire_at": self.fire_at,
            "created_at": self.created_at,
            "repeat": self.repeat.to_dict() if self.repeat else None,
            "paused": self.paused,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Optional["AlarmTimer"]:
        """从存档条目还原计时器；缺关键字段/类型不对返回 None（跳过该条）。

        旧存档没有 repeat 字段，按"不循环"处理。
        """
        try:
            timer = cls(
                user_id=int(data["user_id"]),
                name=str(data["name"]),
                fire_at=float(data["fire_at"]),
                created_at=float(data["created_at"]),
                id=str(data["id"]),
                repeat=RepeatRule.from_dict(data["repeat"]) if data.get("repeat") else None,
                paused=bool(data.get("paused") or False),
            )
        except (KeyError, TypeError, ValueError):
            return None
        if not timer.id or not timer.name:
            return None
        return timer


class AlarmTimerBank:
    """未到期计时器的登记表：容量统计、JSON 存档、到点私聊触发。

    存档路径与容量上限由构造参数注入，便于脱离 bot 单独测试；模块单例见文件末尾。
    """

    def __init__(self, store_path: str, max_active: int):
        self.store_path = store_path
        self.max_active = max_active
        self._timers: dict[str, AlarmTimer] = {}

    def load(self) -> int:
        """从存档恢复计时器并挂调度，返回恢复的数量。

        未到期的按原时间响；已错过的（bot 不在线期间到点）延迟 STARTUP_GRACE_SECS
        补响一次——启动阶段消息发不出去，所以不能立刻发送。
        """
        data = jsontools.read_from_path(self.store_path)
        if not isinstance(data, list):
            return 0
        now = time.time()
        skipped = 0
        for item in data:
            timer = AlarmTimer.from_dict(item) if isinstance(item, dict) else None
            if timer is None:
                skipped += 1
                logger.warning(f"跳过损坏的计时器存档条目：{item!r}")
                continue
            self._timers[timer.id] = timer
            if timer.paused:
                continue          # 暂停中的循环计时器不挂调度，等用户继续
            earliest = now + STARTUP_GRACE_SECS if timer.fire_at <= now else None
            self._schedule(timer, earliest)
        if skipped:
            logger.warning(f"共跳过 {skipped} 个损坏的计时器存档条目")
        if self._timers or skipped:
            self._save()
        return len(self._timers)

    def active_count(self, user_id: int) -> int:
        """该用户未到期的计时器数量。"""
        return sum(1 for timer in self._timers.values() if timer.user_id == user_id)

    def sorted_timers(self, user_id: int) -> list[AlarmTimer]:
        """该用户的计时器，按到点时间从早到晚排序（暂停的排在最后）；列表/取消等编号顺序。"""
        return sorted((timer for timer in self._timers.values() if timer.user_id == user_id),
                      key=lambda timer: (timer.paused, timer.fire_at))

    def find_duplicate(self, user_id: int, name: str, fire_at: float, tolerance: float,
                       repeat: Optional[RepeatRule] = None) -> Optional[AlarmTimer]:
        """找同名的已有计时器（重复登记去重用）。

        循环与非循环互不算重复；循环之间要规则一致、钟点相差不超过 tolerance 秒
        （同名「每天9点」隔天再定一次仍算重复）；非循环按到点时间相差不超过 tolerance 秒。
        """
        for timer in self._timers.values():
            if timer.user_id != user_id:
                continue
            if is_duplicate_reminder(timer, name, fire_at, repeat, tolerance):
                return timer
        return None

    def add(self, user_id: int, fire_at: float, name: str,
            repeat: Optional[RepeatRule] = None) -> Optional[AlarmTimer]:
        """登记一个到点时间为 fire_at 的计时器并落盘、挂调度；达容量上限时返回 None。"""
        if self.active_count(user_id) >= self.max_active:
            return None
        timer = AlarmTimer.create(user_id=user_id, fire_at=fire_at, name=name, repeat=repeat)
        self._timers[timer.id] = timer
        self._schedule(timer)
        self._save()
        return timer

    def remove(self, timer_id: str) -> Optional[AlarmTimer]:
        """取消计时器：取出并落盘，同时撤销到点任务；不存在返回 None。"""
        timer = self._take(timer_id)
        if timer is None:
            return None
        if not timer.paused:
            self._unschedule(timer_id)
        return timer

    def remove_all(self, user_id: int) -> int:
        """清掉该用户所有未到期的计时器，返回清除的数量（同时撤销各自的到点任务）。"""
        timers = [timer for timer in self._timers.values() if timer.user_id == user_id]
        if not timers:
            return 0
        for timer in timers:
            del self._timers[timer.id]
        self._save()
        for timer in timers:
            if not timer.paused:
                self._unschedule(timer.id)
        return len(timers)

    def set_paused(self, timer: AlarmTimer, paused: bool) -> AlarmTimer:
        """暂停/继续一个循环计时器：暂停取消调度、继续从"下一个自然触发点"重新挂上。"""
        timer.paused = paused
        if paused:
            self._unschedule(timer.id)
        else:
            fired_dt = datetime.fromtimestamp(timer.fire_at)
            clock = (fired_dt.hour, fired_dt.minute, fired_dt.second)
            timer.fire_at = next_repeat_occurrence(timer.repeat, datetime.now(), clock).timestamp()
            self._schedule(timer)
        self._save()
        return timer

    def _unschedule(self, timer_id: str) -> None:
        """撤销计时器的到点任务（撤销失败只记日志，可能已经到点执行）。"""
        try:
            nonebot.scheduler.remove_job(f"alarm_{timer_id}")
        except Exception:
            logger.warning(f"撤销计时器任务失败（可能已经到点执行）：{timer_id}")

    def _take(self, timer_id: str) -> Optional[AlarmTimer]:
        """把计时器从登记表取出并落盘（到点触发与取消共用）。"""
        timer = self._timers.pop(timer_id, None)
        if timer is None:
            return None
        self._save()
        return timer

    def _schedule(self, timer: AlarmTimer, earliest: Optional[float] = None) -> None:
        """给计时器挂一次性到点任务；earliest 不为空时（错过的计时器）不早于它执行。"""
        run_at = timer.fire_at if earliest is None else max(timer.fire_at, earliest)
        nonebot.scheduler.add_job(
            self._fire, "date",
            run_date=datetime.fromtimestamp(run_at),
            args=[timer.id],
            id=f"alarm_{timer.id}",
            misfire_grace_time=MISFIRE_GRACE_SECS,
            coalesce=True,
            replace_existing=True,
        )

    def _reschedule_repeat(self, timer: AlarmTimer) -> None:
        """循环计时器到点后：把到点时间推到下一次并重新挂调度（先落盘再响）。

        以"原定到点时刻"和"现在"中较晚者为基准，保证每次至少前进一个周期；
        bot 停机期间错过的只补响一次、不会连补。
        """
        fired_dt = datetime.fromtimestamp(timer.fire_at)
        clock = (fired_dt.hour, fired_dt.minute, fired_dt.second)
        next_dt = next_repeat_occurrence(timer.repeat, max(datetime.now(), fired_dt), clock)
        timer.fire_at = next_dt.timestamp()
        self._save()
        self._schedule(timer)

    async def _fire(self, timer_id: str) -> None:
        """到点：先落盘（循环的推进到下一次、一次性的取出移除），再私聊提醒设置者。"""
        timer = self._timers.get(timer_id)
        if timer is None:
            return
        if timer.repeat is None:
            self._take(timer_id)
        else:
            self._reschedule_repeat(timer)
        logger.info(f"计时器到点：user={timer.user_id} name={timer.name!r}"
                    + (f"（{timer.repeat.unit} 循环，下次 {datetime.fromtimestamp(timer.fire_at)}）"
                       if timer.repeat else ""))
        if not await is_friend(nonebot.get_bot(), timer.user_id):
            # 到点时还没加好友：直接跳过这次提醒（也不走邮件兜底）
            logger.info(f"用户 {timer.user_id} 不是好友，跳过发送计时器 {timer.name!r}")
            return
        msg = get_message("plugins", __plugin_name__, "ring", name=timer.name, replace_cq_str=True)
        try:
            await send_to_user(nonebot.get_bot(), timer.user_id, msg, raise_exception=True)
            # raise ValueError("测试")
        except:
            logger.warning("消息发送失败，尝试使用电子邮件发送")
            result = await send_bot_email(f"{timer.user_id}@qq.com", f"计时器 \"{timer.name}\" 提醒", f"{msg}\n\n注意：这是消息发送失败回退的默认结果（发送电子邮件）哦")
            if not result:
                logger.warning("电子邮件发送失败")
            else:
                logger.info("电子邮件发送完成")

    def _save(self) -> None:
        jsontools.save_to_path(self.store_path, [timer.to_dict() for timer in self._timers.values()])


# 进程内单例：与 apscheduler 任务同生命周期，重启后由存档恢复
alarm_timers = AlarmTimerBank(store_path=STORE_PATH, max_active=MAX_ACTIVE_PER_USER)
alarm_timers.load()
