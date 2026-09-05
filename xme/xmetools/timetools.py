from datetime import datetime, timedelta
from enum import Enum
import pytz
import time
import math
import time
import random
from enum import Enum
from typing import Dict, Any, Optional
import time
import random
from xme.xmetools import jsontools
import os
from enum import Enum
from typing import Dict, Any, Optional, Tuple

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
        if 17 <= hour < 23:
            return "下午"
        if 24 <= hour < 26:
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
                "period": "上午|中午|下午|晚上|黄昏|日出",
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