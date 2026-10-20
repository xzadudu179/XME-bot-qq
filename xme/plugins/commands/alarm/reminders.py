"""提醒登记与查询编排：把时间解析结果变成「登记/列表/取消 + 一句回复」，入口共用。

指令与句式预处理都只负责取参、回复、吞消息；校验顺序、容量上限与文案组装
在这里单点维护。
"""
import time
from typing import Optional, Tuple

from nonebot import NoneBot

from character import get_message
from xme.xmetools.bottools import is_friend
from xme.xmetools.msgtools import event_is_text_can_send
from xme.xmetools.timetools import (MIN_REPEAT_MINUTES, MINUTE_STEPS, RepeatRule, TimeError,
                                    TimeResult, format_duration,
                                    format_repeat_rule, format_time_natural,
                                    rule_skips_missing_dates)
from xme.plugins.commands.alarm import __plugin_name__

from .constants import (CLEAR_ALL_KEYWORD, DUPLICATE_TOLERANCE_SECS, MAX_ACTIVE_PER_USER,
                        SUB_DAILY_REPEAT_UNITS,
                        NAME_MAX_CHARS, NATURAL_TIME_THRESHOLD_SECS)
from .timers import AlarmTimer, alarm_timers

# 时间解析失败原因 → 文案键（单点映射）
_TIME_ERROR_KEYS = {
    TimeError.NO_TIME: "bad_time",
    TimeError.BAD_FORMAT: "bad_time",
    TimeError.OUT_OF_RANGE: "time_out_of_range",
    TimeError.ZERO: "time_zero",
    TimeError.UNSUPPORTED_UNIT: "unsupported_unit",
    TimeError.BAD_INTERVAL: "repeat_interval_invalid",
    TimeError.BAD_DATE: "bad_date",
    TimeError.NEED_CLOCK: "need_clock",
    TimeError.NEED_DAY: "need_day",
}


def time_error_text(result: TimeResult) -> str:
    """时间解析失败 → 给用户看的错误文案；解析成功返回空串。"""
    key = _TIME_ERROR_KEYS.get(result.error)
    if not key:
        return ""
    kwargs = {"detail": result.detail}
    if result.error == TimeError.BAD_INTERVAL:
        # 允许的间隔从常量生成，文案里不重复维护
        kwargs["min"] = MIN_REPEAT_MINUTES
        kwargs["steps"] = "/".join(str(step) for step in MINUTE_STEPS)
    return get_message("plugins", __plugin_name__, key, replace_cq_str=True, **kwargs)


def time_display(fire_at: float, seconds: int, repeat: Optional[RepeatRule] = None) -> str:
    """到点时间的展示文案。

    循环计时器直接展示循环规则（「每天9点05分」）；一次性的：剩余超过 1 小时用自然
    语句时间（明天9点05分），否则用时长（5分钟后）。都能接进「我会在{time}提醒你」。
    """
    if repeat is not None:
        return format_repeat_rule(repeat, fire_at)
    if seconds > NATURAL_TIME_THRESHOLD_SECS:
        return format_time_natural(fire_at)
    return f"{format_duration(max(seconds, 0))}后"


async def register_reminder(bot, event, user_id: int, parsed: TimeResult, name: str) -> Tuple[bool, str]:
    """登记计时器，返回 (是否新建成功, 回复文案)。

    失败（时间不合法/没说名字/名字是保留字/名字过长/名字过不了风控/数量达上限）
    返回对应原因，成功返回确认语；同名且规则/到点时间几乎相同（见
    DUPLICATE_TOLERANCE_SECS）视为重复，不再新建，回一句"已经记过"（此时返回
    False，不需要再加未加好友提示）。
    """
    error_text = time_error_text(parsed)
    if error_text:
        return False, error_text
    if not name:
        return False, get_message("plugins", __plugin_name__, "no_name")
    if name.upper() == CLEAR_ALL_KEYWORD:
        return False, get_message("plugins", __plugin_name__, "name_reserved",
                                  name=name, replace_cq_str=True)
    if len(name) > NAME_MAX_CHARS:
        return False, get_message("plugins", __plugin_name__, "name_too_long", max=NAME_MAX_CHARS)
    if not await event_is_text_can_send(bot, event, name):
        return False, get_message("plugins", __plugin_name__, "name_illegal")
    existing = alarm_timers.find_duplicate(user_id=user_id, name=name, fire_at=parsed.fire_at,
                                           tolerance=DUPLICATE_TOLERANCE_SECS,
                                           repeat=parsed.repeat)
    if existing is not None:
        return False, get_message("plugins", __plugin_name__, "already_set", name=name,
                                  time=time_display(existing.fire_at,
                                                    int(existing.fire_at - time.time()),
                                                    existing.repeat),
                                  replace_cq_str=True)
    if (parsed.repeat is not None and parsed.repeat.unit in SUB_DAILY_REPEAT_UNITS
            and not await is_friend(bot, user_id)):
        # 没加好友：只允许"一天一次"以内的循环（到点也发不出去）
        return False, get_message("plugins", __plugin_name__, "repeat_friend_only")
    timer = alarm_timers.add(user_id=user_id, fire_at=parsed.fire_at, name=name,
                             repeat=parsed.repeat)
    if timer is None:
        return False, get_message("plugins", __plugin_name__, "too_many", max=MAX_ACTIVE_PER_USER)
    reply = get_message("plugins", __plugin_name__, "set_ok",
                        time=time_display(parsed.fire_at, parsed.seconds, parsed.repeat),
                        name=name, replace_cq_str=True)
    if parsed.repeat is not None and rule_skips_missing_dates(parsed.repeat):
        # 「每月29号及以上」「每年2月29日」会碰上不存在的日期：设置时就说清会跳过、下一次是哪天
        reply += get_message("plugins", __plugin_name__, "repeat_skip_hint",
                             rule=format_repeat_rule(parsed.repeat, parsed.fire_at),
                             next=format_time_natural(parsed.fire_at))
    return True, reply


def list_reminders(user_id: int) -> str:
    """该用户未到期计时器的列表文案（按到点时间编号）。"""
    timers = alarm_timers.sorted_timers(user_id)
    if not timers:
        return get_message("plugins", __plugin_name__, "list_empty")
    now = time.time()
    lines = [
        get_message("plugins", __plugin_name__,
                    "list_item_paused" if timer.paused else "list_item",
                    index=index, name=timer.name,
                    time=time_display(timer.fire_at, int(timer.fire_at - now), timer.repeat),
                    replace_cq_str=True)
        for index, timer in enumerate(timers, start=1)
    ]
    return "\n".join([get_message("plugins", __plugin_name__, "list_header", count=len(timers)),
                      *lines, get_message("plugins", __plugin_name__, "list_suffix")])


def find_target_timer(user_id: int, arg: str) -> Tuple[Optional[AlarmTimer], str]:
    """按编号（1 起，来自列表）或名字定位该用户的一个计时器。

    返回 (计时器, 出错文案)：定位成功时计时器非空；叫不出/有歧义时返回 (None, 文案)。
    取消/暂停/继续共用这一套编号与重名规则。
    """
    timers = alarm_timers.sorted_timers(user_id)
    if arg.isdecimal():
        index = int(arg)
        if 1 <= index <= len(timers):
            return timers[index - 1], ""
        return None, get_message("plugins", __plugin_name__, "cancel_not_found",
                                 arg=arg, replace_cq_str=True)
    matched = [item for item in timers if item.name == arg]
    if len(matched) > 1:
        return None, get_message("plugins", __plugin_name__, "cancel_ambiguous",
                                 name=arg, replace_cq_str=True)
    if not matched:
        return None, get_message("plugins", __plugin_name__, "cancel_not_found",
                                 arg=arg, replace_cq_str=True)
    return matched[0], ""


def cancel_reminder(user_id: int, arg: str) -> Tuple[bool, str]:
    """按编号（1 起，来自列表）、名字，或保留字 ALL（清空全部）删除该用户的计时器。

    返回 (是否删除成功, 文案)。
    """
    arg = arg.strip()
    if not arg:
        return False, get_message("plugins", __plugin_name__, "cancel_no_arg")
    if arg.upper() == CLEAR_ALL_KEYWORD:
        count = alarm_timers.remove_all(user_id)
        if not count:
            return False, get_message("plugins", __plugin_name__, "list_empty")
        return True, get_message("plugins", __plugin_name__, "clear_all_ok", count=count)
    timer, error_text = find_target_timer(user_id, arg)
    if timer is None:
        return False, error_text
    alarm_timers.remove(timer.id)
    return True, get_message("plugins", __plugin_name__, "cancel_ok", name=timer.name,
                             time=time_display(timer.fire_at,
                                               int(timer.fire_at - time.time()), timer.repeat),
                             replace_cq_str=True)


def toggle_pause_reminder(user_id: int, arg: str) -> Tuple[bool, str]:
    """按编号或名字暂停/继续该用户的循环计时器（同一个指令来回切换），返回 (是否生效, 文案)。

    只对循环计时器有效；跑着的就暂停，暂停中的就继续。
    """
    arg = arg.strip()
    if not arg:
        return False, get_message("plugins", __plugin_name__, "pause_no_arg")
    timer, error_text = find_target_timer(user_id, arg)
    if timer is None:
        return False, error_text
    if timer.repeat is None:
        return False, get_message("plugins", __plugin_name__, "pause_not_repeat",
                                  name=timer.name, replace_cq_str=True)
    resuming = timer.paused
    alarm_timers.set_paused(timer, paused=not resuming)
    if resuming:
        # 回执里给"具体下一次到点"（循环规则名放在"下一次是…"里读不通）
        return True, get_message("plugins", __plugin_name__, "resume_ok", name=timer.name,
                                 time=format_time_natural(timer.fire_at), replace_cq_str=True)
    return True, get_message("plugins", __plugin_name__, "pause_ok", name=timer.name,
                             replace_cq_str=True)


async def not_friend_hint(bot: NoneBot, user_id: int) -> str:
    """非好友时返回「先加好友」提示（好友返回空串；到点提醒只能私聊发送）。"""
    if await is_friend(bot, user_id):
        return ""
    return get_message("plugins", __plugin_name__, "not_friend_hint")
