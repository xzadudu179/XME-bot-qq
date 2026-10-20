from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from enum import Enum
import pytz
import re
import time
import math
import time
import random
from enum import Enum
from typing import Dict, Any, Optional
import time
import random
from xme.xmetools import jsontools
from xme.xmetools.texttools import no_except_cn2an
import os
from enum import Enum
from typing import Dict, Any, Optional, Tuple, Union

# 季节相关代码
class MacroSeason(Enum):
    """季节状态"""
    DROUGHT = "旱季"
    TRANSITION_TO_RAIN = "降水过渡期"
    RAIN = "雨季"
    TRANSITION_TO_DROUGHT = "升温过渡期"


class MicroSeason(Enum):
    """天象"""
    DUAL_SUN = "凌空期"
    BLOOD_SUN = "血日期"
    WHITE_SUN = "白日期"


class MicroPhase(Enum):
    """时间周期"""
    DUAL_1 = 1        # 血日前的凌空期
    BLOOD = 2         # 血日期
    DUAL_2 = 3        # 白日前的凌空期
    WHITE = 4         # 白日期


# 内部相位到对外展示状态的映射
MICRO_DISPLAY_MAP = {
    MicroPhase.DUAL_1: MicroSeason.DUAL_SUN,
    MicroPhase.BLOOD: MicroSeason.BLOOD_SUN,
    MicroPhase.DUAL_2: MicroSeason.DUAL_SUN,
    MicroPhase.WHITE: MicroSeason.WHITE_SUN,
}
class TeliaClock:
    def __init__(self, config: Dict[str, Any], local_path: str):
        """初始化星球时钟

        Args:
            config (Dict[str, Any]): 配置文件
            local_path (str): 本地保存路径
        """
        self.config = config
        self.local_path = local_path
        # 未找到返回 None
        saved_state = jsontools.read_from_path(local_path)
        if saved_state:
            # 从存档恢复大季节状态
            self.macro_current = MacroSeason(saved_state["macro_current"])
            self.macro_start = saved_state["macro_start"]
            self.macro_duration = saved_state["macro_duration"]

            # 从存档恢复小季节状态
            self.micro_current = MicroPhase(saved_state["micro_current"])
            self.micro_start = saved_state["micro_start"]
            self.micro_duration = saved_state["micro_duration"]
        else:
            # 无存档，初始化为星球元年（此刻）
            now = int(time.time())

            self.macro_current = MacroSeason.DROUGHT
            self.macro_start = now
            self.macro_duration = self._get_random_duration("macro", self.macro_current)

            self.micro_current = MicroPhase.DUAL_1
            self.micro_start = now
            self.micro_duration = self._get_random_duration("micro", self.micro_current)

    def _get_random_duration(self, clock_type: str, state: Enum) -> int:
        """根据配置获取指定阶段的随机持续秒数"""
        range_cfg = self.config[clock_type][state]
        return random.randint(range_cfg["min"], range_cfg["max"])

    def _get_next_macro(self, current: MacroSeason) -> MacroSeason:
        """大季节流转规则"""
        transitions = {
            MacroSeason.DROUGHT: MacroSeason.TRANSITION_TO_RAIN,
            MacroSeason.TRANSITION_TO_RAIN: MacroSeason.RAIN,
            MacroSeason.RAIN: MacroSeason.TRANSITION_TO_DROUGHT,
            MacroSeason.TRANSITION_TO_DROUGHT: MacroSeason.DROUGHT
        }
        return transitions[current]

    def _get_next_micro(self, current: MicroPhase) -> MicroPhase:
        """小天象流转规则"""
        transitions = {
            MicroPhase.DUAL_1: MicroPhase.BLOOD,
            MicroPhase.BLOOD: MicroPhase.DUAL_2,
            MicroPhase.DUAL_2: MicroPhase.WHITE,
            MicroPhase.WHITE: MicroPhase.DUAL_1
        }
        return transitions[current]

    def get_local_time_period(self, hour: int | None = None) -> str:
        """返回 30 小时制下的时间段名称。

        使用 7 段式分割：日出 / 上午 / 中午 / 下午 / 黄昏 / 晚上 / 凌晨。
        """
        if hour is None:
            hour = self.get_local_time()["hour"]
        if 7 <= hour < 9:
            return "日出"
        if 9 <= hour < 13:
            return "上午"
        if 13 <= hour < 17:
            return "中午"
        if 17 <= hour < 24:
            return "下午"
        if 24 <= hour < 27:
            return "黄昏"
        if 27 <= hour < 30:
            return "晚上"
        return "凌晨"

    def get_local_time(self, now: int | None = None) -> Dict[str, Any]:
        """返回当前星球本地时间，单位为 30 小时制。

        Returns:
            {
                "hour": 0-29,
                "minute": 0-59,
                "second": 0-59,
                "time": "HH:MM:SS",
                "period": "上午|中午|下午|晚上|黄昏|...",
                "day_hours": 30,
            }
        """
        if now is None:
            now = int(time.time())
        total_seconds = now % (30 * 60 * 60)
        hour = total_seconds // 3600
        minute = (total_seconds % 3600) // 60
        second = total_seconds % 60
        period = self.get_local_time_period(hour)
        return {
            "hour": hour,
            "minute": minute,
            "second": second,
            "time": f"{hour:02d}:{minute:02d}:{second:02d}",
            "period": period,
            "day_hours": 30,
        }

    def _update_clocks(self, now: int):
        """
        仅在被查询时执行的天象更新。
        """
        # 1. 结算大季节
        while now >= self.macro_start + self.macro_duration:
            self.macro_start += self.macro_duration
            self.macro_current = self._get_next_macro(self.macro_current)
            self.macro_duration = self._get_random_duration("macro", self.macro_current)
            # 可在此处接入日志或事件分发机制
            # print(f"[大季节更替] 忒利亚进入：{self.macro_current.value}")

        # 2. 结算小天象
        while now >= self.micro_start + self.micro_duration:
            self.micro_start += self.micro_duration
            self.micro_current = self._get_next_micro(self.micro_current)
            self.micro_duration = self._get_random_duration("micro", self.micro_current)

            # 异象发生与结束的日志判断
            # display_season = MICRO_DISPLAY_MAP[self.micro_current]
            # if display_season != MicroSeason.DUAL_SUN:
            #     print(f"[天象播报] 异象发生：{display_season.value} 开始！")
            # else:
            #     print(f"[天象播报] 异象结束，恢复为 {display_season.value}。")
        # 自动保存
        self._save()

    def _save(self):
            """保存当前状态

            Returns:
                Dict[str, Any]: 时间线天象状态
            """
            save_dict = {
                "macro_current": self.macro_current.value,
                "macro_start": self.macro_start,
                "macro_duration": self.macro_duration,
                "micro_current": self.micro_current.value,
                "micro_start": self.micro_start,
                "micro_duration": self.micro_duration,
            }
            jsontools.save_to_path(self.local_path, save_dict)

    def get_current_state(self) -> Tuple[MacroSeason, MicroSeason, Dict[str, Any]]:
        """ 获取当前星球综合状态。
            调用此方法会自动触发时间线推进。

        Returns:
            Tuple[MacroSeason, MicroSeason, Dict[str, Any]]:
                大季节，小季节，本地时间信息（30 小时制）
        """
        now = int(time.time())
        self._update_clocks(now)
        local_time = self.get_local_time(now)
        return self.macro_current, MICRO_DISPLAY_MAP[self.micro_current], local_time


class Countdown:
    """倒计时"""
    def __init__(self, total_secs: float, start_sec: float | None = None, end_countdown=False):
        """倒计时构造函数

        Args:
            total_secs (float): 倒计时总秒数
        """
        self.total_secs: float = total_secs
        self.start_sec: float | None = start_sec
        self.end_countdown = end_countdown

    @property
    def remaining_secs(self) -> float:
        """剩余秒数
        """
        if self.start_sec is None:
            return self.total_secs
        elapsed = time.time() - self.start_sec
        remaining = self.total_secs - elapsed
        return max(0.0, remaining)

    def start(self):
        """开始倒计时记录
        """
        if self.start_sec is not None:
            raise ValueError("倒计时记录不能重复开始。")
        self.start_sec = time.time()

    def check(self) -> bool:
        """检查当前倒计时状态

        Returns:
            bool: 倒计时是否结束
        """
        if self.start_sec is None:
            raise ValueError("需要先开始记录再检查状态。")
        if self.end_countdown:
            return True
        elapsed = time.time() - self.start_sec
        if elapsed < self.total_secs:
            return False
        self.end_countdown = True
        return True

    def __dict__(self):
        return {
            "total_secs": self.total_secs,
            "start_sec": self.start_sec,
            "end_countdown": self.end_countdown,
        }


class Timer:
    def __init__(self):
        # self.timer_count = 0
        self.start_time = None
        self.end_time = None

    def start(self):
        self.start_time = time.time()

    def stop(self):
        if self.start_time == 0:
            raise RuntimeError("计时器尚未开始")
        self.end_time = time.time()

    def get_timer_value(self) -> float:
        """得到计时器秒数

        Returns:
            float: 秒数
        """
        if self.start_time is None:
            return 0.
        if self.end_time is None:
            return time.time() - self.start_time
        return self.end_time - self.start_time

class TimeUnit(Enum):
    SECOND = 1
    MINUTE = 60
    HOUR = 60 * 60
    DAY = 60 * 60 * 24
    WEEK = 60 * 60 * 24 * 7
    MONTH = 60 * 60 * 24 * 30
    YEAR = 60 * 60 * 24 * 365

def time_diff(t1: float, t2: float, unit: TimeUnit = TimeUnit.SECOND) -> float:
    """
    计算 t2 - t1 的时间差，并转换为指定单位
    """
    return (t2 - t1) / unit.value

def get_valuetime(time_float, unit: TimeUnit):
    if unit is TimeUnit.WEEK:
        # 周对齐到周一 00:00：纪元 0 是周四 00:00 UTC，而入参是 GMT+8 时间戳，
        # 周一 00:00（GMT+8）= UTC 周日 16:00 = 纪元基准后 3 天 16 小时，
        # 故 +3 天后按周取整，边界正好落在周一 00:00（GMT+8）
        return math.floor((time_float + 3 * TimeUnit.DAY.value) / unit.value)
    if unit in [TimeUnit.DAY, TimeUnit.MONTH, TimeUnit.YEAR] and time_float < 50000:
        return time_float
    return math.floor(time_float / unit.value)

def get_closest_time(times: list, target_time="NOW", format="%Y-%m-%d %H:%M:%S"):
    """获得与目标时间最接近的时间索引

    Args:
        times (list): 时间列表
        target_time (str): 目标时间，填写 NOW 为现在. Defaults to "NOW"
        format (str, optional): 时间格式. Defaults to "%Y-%m-%d %H:%M:%S".

    Returns:
        int: 最接近的时间索引
    """
    min_time = -1
    min_index = -1
    for i, t in enumerate(times):
        differ = abs(get_time_difference(t, target_time, format))
        if min_time < 0:
            min_time = differ
            min_index = i
            continue
        min_time = differ if differ < min_time else min_time
        min_index = i
    return min_index

def secs_to_ymdh(secs: int | float, format=("年", "个月", "天", "小时", "分钟", "秒")):
    """将秒数转换为年月天小时分钟秒

    Args:
        secs (int | float): 秒数

    Returns:
        str: 转换成的时间格式
    """
    days = secs / 86400
    years = days // 365
    # 计算剩余天数
    remaining_days = days % 365
    months = remaining_days // 30
    remaining_days = remaining_days % 30
    hours = 24 * (remaining_days % 1)

    mins = 24 * 60 * (remaining_days % 1) % 60

    remaining_secs = secs % 60 % 60

    # 返回格式化后的字符串z
    formatted_string = "" if years < 1 else str(int(years)) + format[0]
    formatted_string += "" if months < 1 else str(int(months)) + format[1]
    formatted_string += "" if remaining_days < 1 else str(int(remaining_days)) + format[2]
    formatted_string += "" if hours < 1 else str(int(hours)) + format[3]
    formatted_string += "" if mins < 1 else str(int(mins)) + format[4]
    formatted_string += str(int(remaining_secs)) + format[5]
    return formatted_string

def curr_days():
    """当前天数(从1970年1月1日算)
    """
    start_date = datetime(1970, 1, 1)
    current_date = datetime.now()
    return (current_date - start_date).days

def get_time_now(format="%Y-%m-%d %H:%M:%S"):
    return datetime.now().strftime(format)

def days_differ(start_date: int):
    """计算今天与指定天数相差

    Args:
        start_date (int): 指定天数
    """
    current_date = datetime.now()
    return (current_date - start_date).days

def timenow(offset: int=8, unit: TimeUnit=TimeUnit.HOUR) -> float:
    """获取当前时间
    """
    return time.time() + offset * unit.value

def int_to_date(date_num: int, format: str="%Y年%m月%d日") -> str:
    """将从1970年1月1日经过的天数变成日期

    Args:
        date_num (int): 经过的天数
        format (str, optional): 日期格式. Defaults to "%Y年%m月%d日".

    Returns:
        str: 日期字符串
    """
    start_date = datetime(1970, 1, 1)
    target_date = start_date + timedelta(days=date_num)
    return target_date.strftime(format)

def week_str(week_num, is_chinese: bool=True):
    week: dict = {}
    if(is_chinese):
        week = {
            1: "星期一",
            2: "星期二",
            3: "星期三",
            4: "星期四",
            5: "星期五",
            6: "星期六",
            7: "星期日",
        }
    else:
        week = {
            1: "Monday",
            2: "Tuesday",
            3: "Wednesday",
            4: "Thursday",
            5: "Friday",
            6: "Saturday",
            7: "Sunday",
        }
    return week.get(week_num, "Error")

def iso_format_time(time_str, format="%Y-%m-%d %H:%M:%S"):
    """将 ISO 时间转换为指定格式的 GMT+8 时间

    Args:
        time_str (_type_): ISO 时间
        format (_type_): 转换为的时间
    """
    # 解析为datetime对象
    dt = datetime.fromisoformat(time_str)

    # 设置时区
    tz = pytz.timezone('Asia/Shanghai')
    dt_gmt8 = dt.astimezone(tz)
    formatted_time = dt_gmt8.strftime(format)
    return formatted_time

def get_time_difference(t, target_time="NOW", time_format="%Y-%m-%d %H:%M:%S"):
    """获取两个日期相隔的秒数

    Args:
        time (str): 指定的时间
        target_time (str): 目标时间，填写 NOW 为现在. Defaults to "NOW"
        time_format (str): 时间格式

    Returns:
        float: 秒数，负数为更晚，正数为更早
    """
    date1 = datetime.strptime(t, time_format)
    date2 = datetime.now() if target_time == "NOW" else datetime.strptime(target_time, time_format)
    difference = (date2 - date1).total_seconds()
    return difference


def get_curr_hour():
    # 获取当前时间
    now = datetime.now()
    # 提取小时部分
    hour = now.hour
    return hour

def get_time_period():
    """获取当前时间段名称

    Returns:
        str: 当前时间段名称
    """
    hour = get_curr_hour()

    # 判断时间段
    if 0 <= hour < 5:
        return "凌晨"
    elif 5 <= hour < 9:
        return "早上"
    elif 9 <= hour < 11:
        return "上午"
    elif 11 <= hour < 13:
        return "中午"
    elif 13 <= hour < 18:
        return "下午"
    elif 18 <= hour < 23:
        return "晚上"
    elif 23 <= hour < 24:
        return "凌晨"
    raise ValueError("小时数大于 24")

# ---------------------------------------------------------------------------
# 时间文本解析（快捷定时共用：句式预处理与 /alarm 指令）
#
# 支持两种格式（都可带可选的「后/之后」）：
# 1. 相对时长："1分20秒" / "五分钟" / "3天"
# 2. 自然语句时间："5点40分5秒" / "明天9点" / "后天下午3点" / "周三8点" /
#    "下个月3日9点" / "8月15日9点" / "明年3月1日9点"
# ---------------------------------------------------------------------------

# 时长单位别名 → (单位秒数, 该单位允许的最大数值)；单位范围校验的唯一来源
DURATION_UNITS: Dict[str, Tuple[int, int]] = {
    "秒": (1, 59),
    "秒钟": (1, 59),
    "分": (60, 59),
    "分钟": (60, 59),
    "时": (3600, 23),
    "小时": (3600, 23),
    "天": (86400, 366),
    "日": (86400, 366),
}

# 总时长上限（秒）：小时/天可以写得很大，但整体不超过一年
MAX_DURATION_SECS = 366 * 86400

# 没写日期/天词时，"最近的一个将来时刻"超过这个秒数（>12 小时）就要用户标注哪一天：
# 14 点说「13点」、凌晨 4 点说「凌晨3点」都超出 12 小时，要求标注；14 点说「1点」
# 落在 11 小时后的凌晨 1 点，直接排。
NEED_DAY_THRESHOLD_SECS = 12 * 3600

# 出现这些时长单位（周/月/年等）时给调用方一个"不支持"的明确信号
UNSUPPORTED_DURATION_UNITS: Tuple[str, ...] = ("礼拜", "星期", "周", "月", "年")

# 中文数字里 cn2an 不认但口语常见的写法
_CN_NUMBER_FALLBACK = {"两": 2.0}

# 数值：阿拉伯数字 / 中文数字 / 半
_NUMBER_PATTERN = r"(?:[0-9]+(?:\.[0-9]+)?|[零一二三四五六七八九十百千万两点]+|半)"
# 时间点里的数值（不需要「半」，半点单独匹配）
_CLOCK_NUMBER_PATTERN = r"(?:[0-9]+(?:\.[0-9]+)?|[零一二三四五六七八九十百千万两点]+)"

# 相对时长：数值+单位（单位按长度倒序，保证「分钟」先于「分」匹配）
_UNIT_PATTERN = "|".join(sorted(DURATION_UNITS, key=len, reverse=True))
# 「5分钟」「一个半小时」（X个半Y）「一天半」（XY半）都算
_DURATION_TOKEN_RE = re.compile(
    rf"\s*(?P<value>{_NUMBER_PATTERN})\s*个?\s*(?P<half_before>半)?\s*"
    rf"(?P<unit>{_UNIT_PATTERN})(?P<half_after>半)?")
_UNSUPPORTED_TOKEN_RE = re.compile(
    rf"\s*{_NUMBER_PATTERN}\s*个?\s*(?:{'|'.join(UNSUPPORTED_DURATION_UNITS)})")

# 时段的小时范围 → (起始小时, 结束小时)，区间含两端；起始 > 结束表示跨到次日。
# 「时段+几点」的换算与歧义归位都以这张表为准（如「凌晨11点」按 23~6 归到 23 点），
# 调整各时段的定义改这里就行
PERIOD_HOUR_RANGES: Dict[str, Tuple[int, int]] = {
    "凌晨": (23, 6),
    "清晨": (4, 7), "清早": (4, 7),
    "早晨": (4, 10), "早上": (4, 10),
    "上午": (5, 11),
    "中午": (11, 14), "正午": (11, 14),
    "下午": (12, 18),
    "傍晚": (15, 20),
    "晚上": (16, 2), "夜里": (16, 2), "夜晚": (16, 2),
    "深夜": (21, 3), "半夜": (21, 3),
}
_PERIOD_PATTERN = "|".join(sorted(PERIOD_HOUR_RANGES, key=len, reverse=True))
_PERIOD_RE = re.compile(rf"\s*(?P<period>{_PERIOD_PATTERN})")
# 天词 → (天数偏移, 隐含时段)；「今早/今晚」这类词自带时段
_DAY_WORDS = {
    "今天": (0, ""), "今日": (0, ""),
    "明天": (1, ""), "明日": (1, ""),
    "后天": (2, ""), "大后天": (3, ""),
    "今早": (0, "早上"), "明早": (1, "早上"), "今晚": (0, "晚上"), "明晚": (1, "晚上"),
}
_DAY_WORD_PATTERN = "|".join(sorted(_DAY_WORDS, key=len, reverse=True))
_DAY_WORD_RE = re.compile(rf"\s*(?P<word>{_DAY_WORD_PATTERN})")
_WEEKDAY_NUMBERS = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "日": 7, "天": 7}
_WEEKDAY_RE = re.compile(r"\s*(?P<next>下)?(?:周|星期|礼拜)(?P<day>[一二三四五六日天])")
# 下个月3日 / 明年3月1日 / 3月1日（日期后缀 日/号 均可）
_NEXT_MONTH_DATE_RE = re.compile(rf"\s*下个?月\s*(?P<day>{_CLOCK_NUMBER_PATTERN})\s*[日号]")
_DATE_RE = re.compile(
    rf"\s*(?P<next_year>明年)?\s*(?P<month>{_CLOCK_NUMBER_PATTERN})\s*月\s*"
    rf"(?P<day>{_CLOCK_NUMBER_PATTERN})\s*[日号]")
# 时间点：可选时段 + 小时点（可带 分钟/半 与 秒）
_CLOCK_RE = re.compile(
    rf"\s*(?:(?P<period>{_PERIOD_PATTERN})\s*)?(?P<hour>{_CLOCK_NUMBER_PATTERN})\s*点(?:钟)?"
    rf"(?:\s*(?:(?P<minute>{_CLOCK_NUMBER_PATTERN})\s*分|(?P<half>半)))?"
    rf"(?:\s*(?P<second>{_CLOCK_NUMBER_PATTERN})\s*秒)?")

# 句尾动词模式（「记得提醒我 / 叫我 / 喊我 / 让我」及口头语），定时句必须由它收尾；
# 「一下」后面跟着「午」时是「一下午」，不算口头语
_REMIND_VERB_PATTERN = r"(?:记得)?(?:提醒|叫|喊|让)(?:一下|下)?\s*我(?:(?:一下|下)(?!午)|一声)?"
_REMIND_VERB_RE = re.compile(r"\s*" + _REMIND_VERB_PATTERN + r"\s*[,，]?\s*(?P<action>.*)$",
                             re.DOTALL)
# 连接语后面允许出现的东西：空白、结尾、或提醒动词——由此判断连接语是不是时间的一部分
_AFTER_TAIL_PATTERN = r"(?:\s|$|(?:记得)?(?:提醒|叫|喊|让))"
# 连接语：后/之后（可再跟 的时候/时候/时刻）+ 的时候/时候/时刻/时/整
_AFTER_CONNECTOR_PATTERN = r"(?:(?:后|之后)(?:的时候|时候|时刻)?|(?:的时候|时候|时刻|时|整))"
_AFTER_RE = re.compile(
    _AFTER_CONNECTOR_PATTERN + r"|\s+" + _AFTER_CONNECTOR_PATTERN
    + r"(?=" + _AFTER_TAIL_PATTERN + r")")
# 时间表达前可选的引导字：「在明天9点提醒我」「到5点叫我」「约5小时40分后」都算。
# 「约/大约」这类只有在后面直接跟数字时才剪（免得吃掉「约会8点」的「约」）
_LEADING_PARTICLE_RE = re.compile(
    r"\s*(?:(?:在|到)\s*|(?:大约|大概|差不多|将近|近|约)(?=\s*(?:\d|[零一二三四五六七八九十百千万两半点]))\s*)+")

# 句式里「提醒我」之后可选的动作词前缀，不当作提醒内容
_ACTION_PREFIX_WORDS = ("去", "做", "干", "要", "记得")
# 动作词前缀剥离后至少保留的字数（「做操」不能剥成「操」）
_ACTION_MIN_KEEP = 2
# 提醒内容首尾要剪掉的句末标点（「叫我去XXX。」→「XXX」；括号等不动，留着「交房租(1月)」）
_ACTION_TRIM_CHARS = " \t\n　。！？!?~～….,，"

# 星期几 → 展示名
_WEEKDAY_NAMES = {1: "周一", 2: "周二", 3: "周三", 4: "周四", 5: "周五", 6: "周六", 7: "周日"}

# 循环前缀的说法：「每天/每晚/每早」每=天词、「每周X…」、周末/工作日、每月X号、
# 每年X月X日 / 每个X月的X日
# 「每N分钟/每半小时/每分钟」（N 要能整除 60，保证落在自然网格上）
_EVERY_MINUTES_RE = re.compile(rf"\s*每(?:隔)?\s*(?P<value>{_CLOCK_NUMBER_PATTERN}|半)?\s*分(?:钟)?")
# 「每小时/每N小时」+ 可选「零X分/半」偏移
_EVERY_HOURS_RE = re.compile(
    rf"\s*每(?:隔)?\s*(?P<step>{_CLOCK_NUMBER_PATTERN}|半)?\s*小时"
    rf"(?:\s*(?P<minute>{_CLOCK_NUMBER_PATTERN}|半)\s*分)?")
_EVERY_DAY_RE = re.compile(r"\s*(?:每天|每日|每早|每晚)")
_EVERY_DAY_PERIODS = {"每早": "早上", "每晚": "晚上"}
_EVERY_WEEKEND_RE = re.compile(r"\s*(?:每|每个)周末")
_EVERY_WORKDAY_RE = re.compile(r"\s*(?:每|每个)个?工作日")
_EVERY_WEEK_RE = re.compile(r"\s*(?:每|每个)(?:周|星期|礼拜)")
# 「每周X和Y…」的单个星期项（首项可省分隔符，后续项可省「周」）
_WEEKDAY_ITEM_RE = re.compile(r"\s*[、,，和与跟及/或者]?\s*(?:周|星期|礼拜)?(?P<day>[一二三四五六日天])")
_EVERY_MONTH_RE = re.compile(r"\s*(?:每|每个)个?月")
_EVERY_YEAR_RE = re.compile(r"\s*(?:每|每个)年")
# 「每年3月…」里的月份（不带「每」）
_GIVEN_MONTH_RE = re.compile(rf"\s*(?P<month>{_CLOCK_NUMBER_PATTERN})\s*月")
# 「每个3月的1日」里的月份（带「每」）
_EVERY_GIVEN_MONTH_RE = re.compile(rf"\s*(?:每|每个)个?(?P<month>{_CLOCK_NUMBER_PATTERN})\s*月")
# 「X号 / 最后一天」（可带「的」，如「每个3月的1日」）
_MONTH_DAY_RE = re.compile(
    rf"\s*的?\s*(?:(?P<last>最后一天|最后一日)|(?P<day>{_CLOCK_NUMBER_PATTERN})\s*[日号]?)")
# 「每N分钟」允许的间隔：不小于 MIN_REPEAT_MINUTES 且能整除 60（才能落在自然网格上）。
# 太短的间隔会刷屏（每分钟 = 1440 条/天），所以设了下限。
MIN_REPEAT_MINUTES = 5
MINUTE_STEPS = (5, 6, 10, 12, 15, 20, 30, 60)

# 各月最多天数（2 月按闰年算 29），用于校验「每年X月X日」这种日期是否可能出现
_MONTH_MAX_DAYS = {1: 31, 2: 29, 3: 31, 4: 30, 5: 31, 6: 30,
                   7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31}


@dataclass(frozen=True)
class RepeatRule:
    """循环规则：按 unit 反复触发，次数不限，删除即停。

    - minute：每 step 分钟（自然网格，step 要能整除 60）
    - hour：每 step 小时（按小时的网格）+ minute 分
    - week 用 weekdays（1=周一 … 7=周日）
    - month 用 day（几号）；year 用 month + day
    - day 为 None 表示"最后一天"（每月最后一天 / 每年X月最后一天）
    """
    unit: str
    weekdays: Tuple[int, ...] = ()
    month: int = 0
    day: Optional[int] = None
    step: int = 1                 # 间隔型（minute/hour）的步长
    minute: int = 0               # 间隔型（hour）的分钟偏移

    def to_dict(self) -> dict:
        return {"unit": self.unit, "weekdays": list(self.weekdays),
                "month": self.month, "day": self.day,
                "step": self.step, "minute": self.minute}

    @classmethod
    def from_dict(cls, data: dict) -> Optional["RepeatRule"]:
        """从存档还原；字段不合法返回 None（按不循环处理，兼容旧存档）。"""
        try:
            unit = str(data["unit"])
            if unit not in ("minute", "hour", "day", "week", "month", "year"):
                return None
            weekdays = tuple(sorted({int(day) for day in (data.get("weekdays") or [])}))
            if unit == "week" and not weekdays:
                return None
            month = int(data.get("month") or 0)
            raw_day = data.get("day")
            day = None if raw_day is None else int(raw_day)
            step = int(data.get("step") or 1)
            minute = int(data.get("minute") or 0)
            if unit == "minute" and (not 1 <= step <= 60 or 60 % step != 0):
                return None
            if unit == "hour" and (not 1 <= step <= 24 or not 0 <= minute <= 59):
                return None
            return cls(unit=unit, weekdays=weekdays, month=month, day=day,
                       step=step, minute=minute)
        except (KeyError, TypeError, ValueError):
            return None


class TimeError(Enum):
    """时间解析失败的原因（单点定义，调用方按类型选文案）。"""
    NO_TIME = "no_time"                    # 开头没有可识别的时间表达
    BAD_FORMAT = "bad_format"              # 写法不合法（单位重复、非整数秒、时段配 24 点等）
    OUT_OF_RANGE = "out_of_range"          # 某段数值超该单位上限（如「60秒」）
    ZERO = "zero_time"                     # 总时长为 0
    UNSUPPORTED_UNIT = "unsupported_unit"  # 不支持的时长单位（周/月/年）
    BAD_INTERVAL = "bad_interval"          # 间隔型循环的间隔不合法（如每7分钟）
    BAD_DATE = "bad_date"                  # 无效日期（如 2月30日、下个月31日）
    NEED_CLOCK = "need_clock"              # 给了日期/时段但没给几点
    NEED_DAY = "need_day"                  # 最近的一次也在 12 小时以后（或写明的一天已过），要说清哪一天


@dataclass(frozen=True)
class TimeResult:
    """一次时间表达解析结果。

    成功时给出 fire_at（到点时间戳）与 seconds（相对现在的秒数），repeat 为循环规则
    （None 表示只响一次）；失败时前几项为 None，error 给出原因、detail 给出出错片段
    原文；consumed 为从文本开头消费掉的字符数（0 表示没识别到时间，调用方应放行）。
    """
    seconds: Optional[int] = None
    fire_at: Optional[float] = None
    error: Optional[TimeError] = None
    detail: str = ""
    consumed: int = 0
    repeat: Optional[RepeatRule] = None


def _number_value(number_text: str) -> Optional[float]:
    """阿拉伯数字/中文数字/「半」文本 → 数值；无法转换返回 None。

    口语里的前导零（「零五分」「零八点」）先去掉；「零点五」这种保留。
    """
    if number_text == "半":
        return 0.5
    if len(number_text) > 1 and number_text.startswith("零") and not number_text[1:].startswith("点"):
        number_text = number_text[1:]
    if number_text in _CN_NUMBER_FALLBACK:
        return _CN_NUMBER_FALLBACK[number_text]
    if re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", number_text):
        return float(number_text)
    value = no_except_cn2an(number_text)
    return float(value) if isinstance(value, (int, float)) else None


def _duration_time(text: str, now_ts: float) -> TimeResult:
    """解析文本开头的相对时长（内部实现，见 parse_leading_time）。

    各段单位不可重复；每段数值不得超过该单位上限（「60秒」算超范围）；支持小数
    （"1.5小时"）与「半」（"半分钟"），但总秒数必须是正整数且不超过 MAX_DURATION_SECS。
    """
    total = 0.0
    consumed = 0
    seen_unit_secs: set[int] = set()
    while True:
        matched = _DURATION_TOKEN_RE.match(text, consumed)
        if matched is None:
            break
        raw_token = matched.group(0).strip()
        unit = matched.group("unit")
        value = _number_value(matched.group("value"))
        if value is not None:
            # 「一个半小时」=1.5 小时、「一天半」=1.5 天
            if matched.group("half_before"):
                value += 0.5
            if matched.group("half_after"):
                value += 0.5
        unit_secs, unit_max = DURATION_UNITS[unit]
        if value is None or unit_secs in seen_unit_secs:
            return TimeResult(error=TimeError.BAD_FORMAT, detail=raw_token, consumed=matched.end())
        if value > unit_max:
            return TimeResult(error=TimeError.OUT_OF_RANGE, detail=raw_token, consumed=matched.end())
        seen_unit_secs.add(unit_secs)
        total += value * unit_secs
        consumed = matched.end()
    if consumed == 0:
        unsupported = _UNSUPPORTED_TOKEN_RE.match(text)
        if unsupported is not None:
            return TimeResult(error=TimeError.UNSUPPORTED_UNIT,
                              detail=unsupported.group(0).strip(), consumed=unsupported.end())
        return TimeResult(error=TimeError.NO_TIME)
    detail = text[:consumed].strip()
    if total <= 0:
        return TimeResult(error=TimeError.ZERO, detail=detail, consumed=consumed)
    if total != int(total):
        return TimeResult(error=TimeError.BAD_FORMAT, detail=detail, consumed=consumed)
    if total > MAX_DURATION_SECS:
        return TimeResult(error=TimeError.OUT_OF_RANGE, detail=detail, consumed=consumed)
    seconds = int(total)
    return TimeResult(seconds=seconds, fire_at=now_ts + seconds, consumed=consumed)


def _hour_in_period_range(hour: int, hour_range: Tuple[int, int]) -> bool:
    """小时是否落在时段范围内（区间含两端；起始 > 结束表示跨天，如 23~6）。"""
    start, end = hour_range
    if start <= end:
        return start <= hour <= end
    return hour >= start or hour <= end


def _apply_period(hour_value: float, period_word: str) -> float:
    """「时段+几点」→ 24 小时制钟点（时段范围见 PERIOD_HOUR_RANGES）。

    小时先按原样试；不在该时段范围内就试加 12 小时（「晚上8点」→ 20 点、
    「凌晨11点」→ 23 点）；两个都不在范围内时按原样保留（「上午12点」→ 12 点）。
    结果是 24 及以上表示顺延到次日（「晚上12点」→ 24 点，即次日 0 点）。
    """
    hour_range = PERIOD_HOUR_RANGES.get(period_word)
    if hour_range is None:
        return hour_value
    for candidate in (hour_value, hour_value + 12):
        if _hour_in_period_range(int(candidate) % 24, hour_range):
            return candidate
    return hour_value


def _resolve_date(now_dt: datetime, matched: "re.Match", next_month: bool) -> Tuple[Optional[datetime], str]:
    """解析「下个月X日 / X月X日 / 明年X月X日」为基准日期（当天 0 点）。

    「X月X日」今年的这个日子已经过了就顺延到明年；非法日期返回 (None, 出错原文)。
    """
    raw = matched.group(0).strip()
    day_value = _number_value(matched.group("day"))
    if day_value is None or day_value != int(day_value) or not 1 <= int(day_value) <= 31:
        return None, raw
    day = int(day_value)
    try:
        if next_month:
            first_of_next = (now_dt.replace(day=1) + timedelta(days=32)).replace(day=1)
            return now_dt.replace(year=first_of_next.year, month=first_of_next.month, day=day), ""
        month_value = _number_value(matched.group("month"))
        if month_value is None or not 1 <= month_value <= 12:
            return None, raw
        month = int(month_value)
        if matched.group("next_year"):
            return now_dt.replace(year=now_dt.year + 1, month=month, day=day), ""
        target = now_dt.replace(month=month, day=day)
        if target.date() < now_dt.date():
            # 今年的这个日子已经过了 → 顺延到明年
            target = now_dt.replace(year=now_dt.year + 1, month=month, day=day)
        return target, ""
    except ValueError:
        return None, raw


def _resolve_clock_only(now_dt: datetime, hour: int, minute: int, second: int,
                       period_word: str, day_roll: int) -> Optional[datetime]:
    """没写日期/天词时，时刻落在哪一天。

    返回最近的一个将来时刻；如果它离现在超过 NEED_DAY_THRESHOLD_SECS（>12 小时，
    实际已经是"明天或更远"这一档），返回 None 让调用方要求用户标注哪一天——例如
    14 点说「13点」、凌晨 4 点说「凌晨3点」。超 24 点（「25点」）与「晚上12点」
    这类已经写明跨天的写法不做判断，直接算下一天。
    """
    today = now_dt.replace(hour=0, minute=0, second=0, microsecond=0)

    def at(offset_days: int, clock_hour: int) -> datetime:
        return (today + timedelta(days=offset_days)).replace(
            hour=clock_hour, minute=minute, second=second)

    if day_roll:
        return at(day_roll, hour)
    if period_word or hour >= 13:
        # 写明了时段、或 13~23 点：只在今天与明天之间取最近的一个
        candidates = [at(0, hour), at(1, hour)]
    elif hour == 12:
        # 12 点可能是中午，也可能是（次日的）凌晨 0 点
        candidates = [at(0, 12), at(1, 0), at(1, 12)]
    elif hour == 0:
        candidates = [at(0, 0), at(1, 0)]
    else:
        candidates = [at(0, hour), at(0, hour + 12), at(1, hour)]
    future = [candidate for candidate in candidates if candidate > now_dt]
    nearest = min(future) if future else at(1, hour)
    if nearest - now_dt > timedelta(seconds=NEED_DAY_THRESHOLD_SECS):
        return None
    return nearest


def _month_occurrence(year: int, month: int, day: Optional[int],
                      clock: Tuple[int, int, int]) -> Optional[datetime]:
    """某年某月某日的到点钟点；day 为 None 表示当月最后一天，日期不存在返回 None。"""
    try:
        if day is None:
            last = (datetime(year, month, 1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            return last.replace(hour=clock[0], minute=clock[1], second=clock[2])
        return datetime(year, month, day, clock[0], clock[1], clock[2])
    except ValueError:
        return None


def next_repeat_occurrence(rule: RepeatRule, after: datetime,
                           clock: Tuple[int, int, int] = (0, 0, 0)) -> datetime:
    """循环规则里严格晚于 after 的下一次到点（天级规则的钟点由 clock 给出）。

    间隔型按自然网格对齐：「每5分钟」落在整 5 分的格子上、「每小时」落在整点、
    「每小时5分」落在每小时的 :05；天级规则用 clock 的时分秒。
    「每月31号」遇没有 31 号的月份、「每年2月29日」遇平年都会跳过——不存在的日期不提醒。
    """
    if rule.unit == "minute":
        candidate = after.replace(second=0, microsecond=0)
        if candidate <= after or candidate.minute % rule.step:
            candidate += timedelta(minutes=1)
            while candidate.minute % rule.step:
                candidate += timedelta(minutes=1)
        return candidate
    if rule.unit == "hour":
        candidate = after.replace(minute=rule.minute, second=0, microsecond=0)
        if candidate <= after:
            candidate += timedelta(hours=1)
        while candidate.hour % rule.step:
            candidate += timedelta(hours=1)
        return candidate
    if rule.unit == "day":
        candidate = after.replace(hour=clock[0], minute=clock[1], second=clock[2], microsecond=0)
        return candidate if candidate > after else candidate + timedelta(days=1)
    if rule.unit == "week":
        candidate = after.replace(hour=clock[0], minute=clock[1], second=clock[2], microsecond=0)
        for _ in range(8):
            if candidate > after and candidate.isoweekday() in rule.weekdays:
                return candidate
            candidate += timedelta(days=1)
        return candidate
    if rule.unit == "month":
        base = after.replace(day=1, hour=clock[0], minute=clock[1], second=clock[2], microsecond=0)
        for _ in range(25):
            candidate = _month_occurrence(base.year, base.month, rule.day, clock)
            if candidate is not None and candidate > after:
                return candidate
            base = (base + timedelta(days=32)).replace(day=1)
        return base
    # year：从今年开始往后找（2月29日最坏 8 年内必有一个闰年）
    for year in range(after.year, after.year + 9):
        candidate = _month_occurrence(year, rule.month, rule.day, clock)
        if candidate is not None and candidate > after:
            return candidate
    return after.replace(hour=clock[0], minute=clock[1], second=clock[2], microsecond=0)


def _scan_weekdays(text: str, pos: int) -> Tuple[Tuple[int, ...], int]:
    """扫描「每周X和Y…」的星期几列表，返回 (星期集合, 结束位置)。"""
    days = []
    end = pos
    while True:
        matched = _WEEKDAY_ITEM_RE.match(text, end)
        if matched is None:
            break
        days.append(_WEEKDAY_NUMBERS[matched.group("day")])
        end = matched.end()
    return tuple(sorted(set(days))), end


def _scan_month_day(text: str, pos: int) -> "Tuple[Optional[int], int, str]":
    """扫描「X号 / 最后一天」，返回 (日, 结束位置, 出错原文)；日为 None 表示最后一天。"""
    matched = _MONTH_DAY_RE.match(text, pos)
    if matched is None:
        return None, pos, ""
    if matched.group("last") is not None:
        return None, matched.end(), ""
    raw_day = matched.group(0).strip()
    day_value = _number_value(matched.group("day"))
    if day_value is None or day_value != int(day_value) or not 1 <= int(day_value) <= 31:
        return None, matched.end(), raw_day
    return int(day_value), matched.end(), ""


def _match_repeat_prefix(text: str) -> Union[Tuple[RepeatRule, int, str], TimeResult, None]:
    """匹配开头的循环说法，返回 (循环规则, 消费字符数, 隐含时段)；不是循环说法返回 None。

    日期明显非法（如「每月32号」）时直接返回带错误的 TimeResult，交给调用方回执。
    支持：每天/每日/每早/每晚、每周X[和Y…]、每个周末、每个工作日、每月X号、
    每月最后一天、每年X月X日、每个X月的X日、每年X月最后一天。
    """
    minute_matched = _EVERY_MINUTES_RE.match(text)
    if minute_matched is not None:
        raw_value = (minute_matched.group("value") or "1").strip()
        if raw_value != "半":
            value = _number_value(raw_value)
            if value is None or value != int(value):
                return None
            step = int(value)
        else:
            step = 1          # 「每半分钟」= 30 秒，不支持（分钟网格最小 1 分钟）
            return TimeResult(error=TimeError.BAD_INTERVAL,
                              detail=minute_matched.group(0).strip(),
                              consumed=minute_matched.end())
        if step not in MINUTE_STEPS:
            return TimeResult(error=TimeError.BAD_INTERVAL,
                              detail=minute_matched.group(0).strip(),
                              consumed=minute_matched.end())
        return RepeatRule(unit="minute", step=step), minute_matched.end(), ""
    hours_matched = _EVERY_HOURS_RE.match(text)
    if hours_matched is not None:
        raw_step = (hours_matched.group("step") or "1").strip()
        raw_minute = (hours_matched.group("minute") or "").strip()
        if raw_step == "半" or raw_minute == "半":
            if raw_step == "半":
                # 「每半小时」= 每 30 分钟
                return RepeatRule(unit="minute", step=30), hours_matched.end(), ""
            return TimeResult(error=TimeError.BAD_INTERVAL,
                              detail=hours_matched.group(0).strip(),
                              consumed=hours_matched.end())
        step_value = _number_value(raw_step)
        if step_value is None or step_value != int(step_value) or not 1 <= int(step_value) <= 24:
            return TimeResult(error=TimeError.BAD_INTERVAL,
                              detail=hours_matched.group(0).strip(),
                              consumed=hours_matched.end())
        minute = 0
        if raw_minute:
            minute_value = _number_value(raw_minute)
            if minute_value is None or minute_value != int(minute_value) or not 0 <= int(minute_value) <= 59:
                return TimeResult(error=TimeError.BAD_INTERVAL,
                                  detail=hours_matched.group(0).strip(),
                                  consumed=hours_matched.end())
            minute = int(minute_value)
        return RepeatRule(unit="hour", step=int(step_value), minute=minute), hours_matched.end(), ""
    matched = _EVERY_DAY_RE.match(text)
    if matched is not None:
        word = matched.group(0).strip()
        return RepeatRule(unit="day"), matched.end(), _EVERY_DAY_PERIODS.get(word, "")
    matched = _EVERY_WEEKEND_RE.match(text)
    if matched is not None:
        return RepeatRule(unit="week", weekdays=(6, 7)), matched.end(), ""
    matched = _EVERY_WORKDAY_RE.match(text)
    if matched is not None:
        return RepeatRule(unit="week", weekdays=(1, 2, 3, 4, 5)), matched.end(), ""
    matched = _EVERY_WEEK_RE.match(text)
    if matched is not None:
        weekdays, end = _scan_weekdays(text, matched.end())
        if not weekdays:
            return None      # 「每周」后面没跟星期几：不算循环说法
        return RepeatRule(unit="week", weekdays=weekdays), end, ""
    matched = _EVERY_MONTH_RE.match(text)
    if matched is not None:
        day, end, bad_text = _scan_month_day(text, matched.end())
        if bad_text:
            return TimeResult(error=TimeError.BAD_DATE, detail=text[:end].strip(), consumed=end)
        return RepeatRule(unit="month", day=day), end, ""
    matched = _EVERY_YEAR_RE.match(text)
    if matched is not None:
        month_matched = _GIVEN_MONTH_RE.match(text, matched.end())
    else:
        month_matched = _EVERY_GIVEN_MONTH_RE.match(text)
    if month_matched is None:
        return None      # 「每年」后面没跟月份：不算循环说法
    month_value = _number_value(month_matched.group("month"))
    if month_value is None or not 1 <= month_value <= 12:
        return None
    day, end, bad_text = _scan_month_day(text, month_matched.end())
    if bad_text:
        return TimeResult(error=TimeError.BAD_DATE, detail=text[:end].strip(), consumed=end)
    month = int(month_value)
    if day is not None and day > _MONTH_MAX_DAYS[month]:
        # 「每年2月30日」这类不可能出现的日期直接报错，而不是永远不响
        return TimeResult(error=TimeError.BAD_DATE, detail=text[:end].strip(), consumed=end)
    return RepeatRule(unit="year", month=month, day=day), end, ""


def rule_skips_missing_dates(rule: RepeatRule) -> bool:
    """该循环规则是否可能出现"不存在的日期"（需要向用户说明会被跳过）。

    「每月29号及以上」在 2 月（29 号还看闰年）、「每年2月29日」在平年都会跳过。
    """
    if rule.unit == "month":
        return rule.day is not None and rule.day > 28
    if rule.unit == "year":
        return (rule.month, rule.day) == (2, 29)
    return False


def _parse_clock(clock_matched: "re.Match",
                 fallback_period: str = "") -> Union[Tuple[int, int, int, str, int], TimeResult]:
    """解析「[时段]X点[Y分|半][Z秒]」为 (时, 分, 秒, 时段词, 跨天数)；不合法时返回带错误的 TimeResult。"""
    clock_text = clock_matched.group(0).strip()
    period_word = clock_matched.group("period") or fallback_period
    hour_value = _number_value(clock_matched.group("hour"))
    minute_value = 30.0 if clock_matched.group("half") else _number_value(clock_matched.group("minute") or "0")
    second_value = _number_value(clock_matched.group("second") or "0")
    if hour_value is None or minute_value is None or second_value is None:
        return TimeResult(error=TimeError.BAD_FORMAT, detail=clock_text,
                          consumed=clock_matched.end())
    if minute_value > 59:
        return TimeResult(error=TimeError.OUT_OF_RANGE, detail=f"{clock_matched.group('minute') or ''}分",
                          consumed=clock_matched.end())
    if second_value > 59:
        return TimeResult(error=TimeError.OUT_OF_RANGE, detail=f"{clock_matched.group('second') or ''}秒",
                          consumed=clock_matched.end())
    if period_word and hour_value >= 24:
        # 「下午25点」这类写法不成立（超 24 点本身已隐含跨天）
        return TimeResult(error=TimeError.BAD_FORMAT, detail=clock_text,
                          consumed=clock_matched.end())
    if period_word:
        hour_value = _apply_period(hour_value, period_word)
    clock_secs = hour_value * 3600 + minute_value * 60 + second_value
    if clock_secs != int(clock_secs):
        return TimeResult(error=TimeError.BAD_FORMAT, detail=clock_text,
                          consumed=clock_matched.end())
    day_roll, clock_secs = divmod(int(clock_secs), 86400)
    hour, remainder = divmod(clock_secs, 3600)
    minute, second = divmod(remainder, 60)
    return hour, minute, second, period_word, day_roll


def _absolute_time(text: str, now_dt: datetime) -> Optional[TimeResult]:
    """把文本开头解析为自然语句时间（内部实现，见 parse_leading_time）。

    不是这种格式返回 None（调用方去试相对时长）。
    """
    # 循环说法（每天/每周X/每月X号/每年X月X日…）：算出一规则 + 下一次到点
    repeat_matched = _match_repeat_prefix(text)
    if isinstance(repeat_matched, TimeResult):
        return repeat_matched
    if repeat_matched is not None:
        rule, repeat_end, repeat_period = repeat_matched
        clock_matched = _CLOCK_RE.match(text, repeat_end)
        if clock_matched is None and rule.unit not in ("minute", "hour"):
            # 「每天/每周X…」后面没有几点：要求补时间（间隔型自带网格，不需要钟点）
            return TimeResult(error=TimeError.NEED_CLOCK, detail=text[:repeat_end].strip(),
                              consumed=repeat_end)
        if clock_matched is None:
            fire_dt = next_repeat_occurrence(rule, now_dt)
            consumed = repeat_end
        else:
            parsed = _parse_clock(clock_matched, fallback_period=repeat_period)
            if isinstance(parsed, TimeResult):
                return parsed
            hour, minute, second, _period_word, _day_roll = parsed
            if rule.unit in ("minute", "hour"):
                # 间隔型自带网格，后面跟的几点没有意义：消费掉但忽略
                fire_dt = next_repeat_occurrence(rule, now_dt)
            else:
                fire_dt = next_repeat_occurrence(rule, now_dt, (hour, minute, second))
            consumed = clock_matched.end()
        fire_at = fire_dt.timestamp()
        return TimeResult(seconds=int(round(fire_at - now_dt.timestamp())), fire_at=fire_at,
                          consumed=consumed, repeat=rule)

    consumed = 0
    detail = ""
    period_word = ""
    day_offset: Optional[int] = None          # 相对天数（天词/星期）
    target_date: Optional[datetime] = None    # 明确的日期（下个月X日等）
    weekday_is_today = False                  # 「周X」正好是今天时，时刻过了要顺延一周

    word_matched = _DAY_WORD_RE.match(text)
    if word_matched is not None:
        day_offset, period_word = _DAY_WORDS[word_matched.group("word")]
        consumed = word_matched.end()
    else:
        week_matched = _WEEKDAY_RE.match(text)
        if week_matched is not None:
            week_day = _WEEKDAY_NUMBERS[week_matched.group("day")]
            if week_matched.group("next"):
                # 下周X：下一个自然周（周一起算）里的那一天
                day_offset = (8 - now_dt.isoweekday()) + (week_day - 1)
            else:
                day_offset = (week_day - now_dt.isoweekday()) % 7
                weekday_is_today = day_offset == 0
            consumed = week_matched.end()
        else:
            date_matched = _NEXT_MONTH_DATE_RE.match(text)
            next_month = date_matched is not None
            if date_matched is None:
                date_matched = _DATE_RE.match(text)
            if date_matched is not None:
                resolved, bad_text = _resolve_date(now_dt, date_matched, next_month=next_month)
                if resolved is None:
                    return TimeResult(error=TimeError.BAD_DATE, detail=bad_text,
                                      consumed=date_matched.end())
                target_date = resolved
                consumed = date_matched.end()

    clock_matched = _CLOCK_RE.match(text, consumed)
    if clock_matched is None:
        period_matched = _PERIOD_RE.match(text, consumed)
        if period_matched is not None:
            return TimeResult(error=TimeError.NEED_CLOCK,
                              detail=text[:consumed] + period_matched.group("period"),
                              consumed=period_matched.end())
        if consumed > 0:
            # 给了日期/天词但没给几点（如「明天叫我」「周三提醒我」）
            return TimeResult(error=TimeError.NEED_CLOCK, detail=text[:consumed].strip(),
                              consumed=consumed)
        return None

    # 时刻：小时支持小数（1.5点 = 1 点半）与「半」；分/秒不得超过 59
    clock_text = clock_matched.group(0).strip()
    parsed = _parse_clock(clock_matched, fallback_period=period_word)
    if isinstance(parsed, TimeResult):
        return parsed
    hour, minute, second, period_word, day_roll = parsed

    if target_date is not None:
        base = target_date + timedelta(days=day_roll)
        fire_dt = base.replace(hour=hour, minute=minute, second=second, microsecond=0)
    elif day_offset is not None:
        fire_dt = (now_dt + timedelta(days=day_offset + day_roll)).replace(
            hour=hour, minute=minute, second=second, microsecond=0)
        if weekday_is_today and fire_dt <= now_dt:
            # 「周X」正好是今天、但时刻已经过了 → 顺延到下周同一天
            fire_dt += timedelta(days=7)
    else:
        fire_dt = _resolve_clock_only(now_dt, hour, minute, second, period_word, day_roll)
        if fire_dt is None:
            # 最近的一个将来时刻也在 12 小时以后：说清哪一天才记得住
            return TimeResult(error=TimeError.NEED_DAY, detail=clock_text,
                              consumed=clock_matched.end())
    if fire_dt <= now_dt:
        # 明确写了日期（如「今天9点」）但已经过去了：同样要求标注哪一天
        return TimeResult(error=TimeError.NEED_DAY, detail=clock_text,
                          consumed=clock_matched.end())
    fire_at = fire_dt.timestamp()
    return TimeResult(seconds=int(round(fire_at - now_dt.timestamp())), fire_at=fire_at,
                      consumed=clock_matched.end())


def parse_leading_time(text: str, now: Optional[float] = None) -> TimeResult:
    """解析文本开头的时间表达，成功时给出到点时间（fire_at / seconds）。

    两种格式，都可带可选的「后/之后」：
    1. 相对时长："1分20秒" / "五分钟" / "3天"（单位上限见 DURATION_UNITS，总长 ≤ MAX_DURATION_SECS）
    2. 自然语句时间："5点40分5秒" / "明天9点" / "后天下午3点" / "周三8点" /
       "下个月3日9点" / "8月15日9点" / "明年3月1日9点"；时刻可以写到 25 点（顺延次日）；
       只写日期/时段没写几点 → NEED_CLOCK；没写日期且最近的一次在 12 小时以后（或写明
       的日期已经过去）→ NEED_DAY，提示用户标注哪一天

    两种格式都命中时取开头消费更长的那一种（如「一点五小时」按 1.5 小时算）；
    失败时 error/detail 说明原因，consumed 为 0 表示开头没有可识别的时间表达。
    """
    now_ts = time.time() if now is None else now
    now_dt = datetime.fromtimestamp(now_ts)
    # 开头允许带个「在/到」（「在明天9点提醒我」「到5点叫我」），下面按去掉它之后解析
    leading = _LEADING_PARTICLE_RE.match(text)
    offset = leading.end() if leading is not None else 0
    body = text[offset:]
    duration = _duration_time(body, now_ts)
    absolute = _absolute_time(body, now_dt)
    if absolute is not None and absolute.consumed > duration.consumed:
        result = absolute
    else:
        result = duration
    if result.consumed == 0:
        return result
    if result.error is not None:
        # 出错的位置可能停在日期/日期形式上，后面还跟着几点（「明年2月29日1点」「每月32号9点」）：
        # 一并消费掉，句式尾动词才接得上（回复仍是这个错误，不会静默放行）
        clock_matched = _CLOCK_RE.match(body, result.consumed)
        if clock_matched is not None:
            result = replace(result, consumed=clock_matched.end())
    after_matched = _AFTER_RE.match(body, result.consumed)
    consumed = result.consumed if after_matched is None else after_matched.end()
    # 「后/之后」属于时间表达本身（两种格式都可有）；consumed 要带上开头的「在/到」
    return replace(result, consumed=offset + consumed)

def format_duration(seconds: int) -> str:
    """秒数 →「1天2小时30分钟5秒」风格的时长文本（跳过为 0 的分段，全 0 输出「0秒」）。"""
    days, remainder = divmod(int(seconds), 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, secs = divmod(remainder, 60)
    parts = []
    if days:
        parts.append(f"{days}天")
    if hours:
        parts.append(f"{hours}小时")
    if minutes:
        parts.append(f"{minutes}分钟")
    if secs:
        parts.append(f"{secs}秒")
    return "".join(parts) or "0秒"


def _format_clock(fire_dt: datetime) -> str:
    """时刻 →「9点05分30秒」风格（分/秒为 0 时省略）。"""
    clock = f"{fire_dt.hour}点"
    if fire_dt.minute or fire_dt.second:
        clock += f"{fire_dt.minute:02d}分"
    if fire_dt.second:
        clock += f"{fire_dt.second:02d}秒"
    return clock


def format_time_natural(fire_at: float, now: Optional[float] = None) -> str:
    """到点时间戳 → 自然语句时间（用于提醒文案里的"哪天几点"）。

    天数近的用 今天/明天/后天/大后天；一周内用 周X；更远用 M月D日（跨年带年份）；
    时刻用 H点（有分钟/秒才带 MM分[SS秒]）。
    """
    now_dt = datetime.fromtimestamp(time.time() if now is None else now)
    fire_dt = datetime.fromtimestamp(fire_at)
    delta_days = (fire_dt.date() - now_dt.date()).days
    if delta_days == 0:
        prefix = "今天"
    elif delta_days == 1:
        prefix = "明天"
    elif delta_days == 2:
        prefix = "后天"
    elif delta_days == 3:
        prefix = "大后天"
    elif 3 < delta_days < 7:
        prefix = _WEEKDAY_NAMES[fire_dt.isoweekday()]
    elif fire_dt.year == now_dt.year:
        prefix = f"{fire_dt.month}月{fire_dt.day}日"
    else:
        prefix = f"{fire_dt.year}年{fire_dt.month}月{fire_dt.day}日"
    return f"{prefix}{_format_clock(fire_dt)}"


def format_repeat_rule(rule: RepeatRule, fire_at: float) -> str:
    """循环规则 + 到点钟点 → 展示文案（「每天9点05分」「每周三和周五8点」「每月最后一天9点」）。"""
    if rule.unit == "minute":
        return "每分钟" if rule.step == 1 else f"每{rule.step}分钟"
    if rule.unit == "hour":
        label = "每小时" if rule.step == 1 else f"每{rule.step}小时"
        return f"{label}{rule.minute}分" if rule.minute else label
    clock = _format_clock(datetime.fromtimestamp(fire_at))
    if rule.unit == "day":
        label = "每天"
    elif rule.unit == "week":
        if rule.weekdays == (6, 7):
            label = "每个周末"
        elif rule.weekdays == (1, 2, 3, 4, 5):
            label = "每个工作日"
        else:
            label = "每" + "和".join(_WEEKDAY_NAMES[day] for day in rule.weekdays)
    elif rule.unit == "month":
        label = "每月最后一天" if rule.day is None else f"每月{rule.day}号"
    else:
        label = (f"每年{rule.month}月最后一天" if rule.day is None
                 else f"每年{rule.month}月{rule.day}日")
    return f"{label}{clock}"


def _clean_action(action: str) -> str:
    """去掉提醒内容开头的动作词前缀（「去做作业」→「作业」）。

    剥后不足 _ACTION_MIN_KEEP 字则保留原样，避免「提醒我做操」被剥成「操」。
    """
    action = action.strip(_ACTION_TRIM_CHARS)
    changed = True
    while changed and action:
        changed = False
        for word in _ACTION_PREFIX_WORDS:
            if action.startswith(word) and len(action) - len(word) >= _ACTION_MIN_KEEP:
                action = action[len(word):].strip(_ACTION_TRIM_CHARS)
                changed = True
    return action


@dataclass(frozen=True)
class ReminderRequest:
    """「{时间}[后]提醒我/叫我…」句式解析结果；time 带 error 时表示时间不合法。"""
    time: TimeResult
    action: str = ""


# 「提醒我」开头（不带 action 捕获），用于"提醒在前"的语序；后面允许跟一个逗号
_REMIND_VERB_START_RE = re.compile(r"\s*" + _REMIND_VERB_PATTERN + r"\s*[,，]?\s*")


def extract_reminder(text: str, now: Optional[float] = None) -> Optional[ReminderRequest]:
    """从提醒句式里提取请求，两种语序都认：

    - 「{时间}[后]提醒我/叫我[去/做…]内容」（如「5分钟后提醒我去写作业」）
    - 「提醒我/叫我{时间}[后][去/做…]内容」（如「提醒我一个半小时后去写作业」）

    时间支持相对时长与自然语句时间两种格式（见 parse_leading_time）。两种语序都不匹配
    时返回 None，调用方应放行；匹配时返回请求——time 可能带解析错误，调用方据此回复
    对应文案。
    """
    # 语序一：时间在前
    parsed = parse_leading_time(text, now)
    if parsed.consumed > 0:
        matched = _REMIND_VERB_RE.match(text[parsed.consumed:])
        if matched is not None:
            return ReminderRequest(time=parsed, action=_clean_action(matched.group("action")))
    # 语序二：提醒在前（「提醒我一个半小时后去写作业」）
    verb_matched = _REMIND_VERB_START_RE.match(text)
    if verb_matched is None:
        return None
    body = text[verb_matched.end():]
    parsed = parse_leading_time(body, now)
    if parsed.consumed == 0:
        return None
    return ReminderRequest(time=parsed, action=_clean_action(body[parsed.consumed:]))

TELIA_CONFIG = {
        "macro": {
            MacroSeason.DROUGHT: {"min": 10 * TimeUnit.DAY.value, "max": 23 * TimeUnit.DAY.value},
            MacroSeason.TRANSITION_TO_RAIN: {"min": 1 * TimeUnit.DAY.value, "max": 3 * TimeUnit.DAY.value},
            MacroSeason.RAIN: {"min": 8 * TimeUnit.DAY.value, "max": 14 * TimeUnit.DAY.value},
            MacroSeason.TRANSITION_TO_DROUGHT: {"min": int(1.5 * TimeUnit.DAY.value), "max": int(2.5 * TimeUnit.DAY.value)},
        },
        "micro": {
            # 凌空期
            MicroPhase.DUAL_1: {"min": 80 * TimeUnit.HOUR.value, "max": 95 * TimeUnit.HOUR.value},
            # 血日期
            MicroPhase.BLOOD: {"min": 40 * TimeUnit.MINUTE.value, "max": 140 * TimeUnit.MINUTE.value},

            # 凌空期 2
            MicroPhase.DUAL_2: {"min": 80 * TimeUnit.HOUR.value, "max": 95 * TimeUnit.HOUR.value},
            # 白日期
            MicroPhase.WHITE: {"min": 80 * TimeUnit.MINUTE.value, "max": 240 * TimeUnit.MINUTE.value},
        }
    }

TELIA_CLOCK = TeliaClock(TELIA_CONFIG, "./data/telia_clock.json")