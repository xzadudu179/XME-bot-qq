from datetime import datetime, timedelta
from enum import Enum
import time

class TimeUnit(Enum):
    SECOND = 1
    MINUTE = 60
    HOUR = 60 * 60
    DAY = 60 * 60 * 24
    WEEK = 60 * 60 * 24 * 7
    MONTH = 60 * 60 * 24 * 30
    YEAR = 60 * 60 * 24 * 365

def secs_to_ymdh(secs):
    """将秒数转换为年月天小时分钟秒

    Args:
        secs (int): 秒数

    Returns:
        str: 转换成的时间格式
    """
    days = secs / 86400
    # 计算年数
    years = days // 365
    # 计算剩余天数
    remaining_days = days % 365
    # 计算月数
    months = remaining_days // 30
    # 计算剩余天数
    remaining_days = remaining_days % 30
    # 计算小时数
    hours = 24 * (remaining_days % 1)

    mins = 24 * 60 * (remaining_days % 1) % 60

    remaining_secs = secs % 60 % 60

    # 返回格式化后的字符串z
    formatted_string = "" if years < 1 else str(int(years)) + "年"
    formatted_string += "" if months < 1 else str(int(months)) + "个月"
    formatted_string += "" if remaining_days < 1 else str(int(remaining_days)) + "天"
    formatted_string += str(int(hours)) + "小时"
    formatted_string += str(int(mins)) + "分钟"
    formatted_string += str(int(remaining_secs)) + "秒"
    return formatted_string

def curr_days():
    """当前天数(从1970年1月1日算)
    """
    start_date = datetime(1970, 1, 1)
    current_date = datetime.now()
    return (current_date - start_date).days

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

def int_to_days(date_num: int, format: str="%Y年%m月%d日") -> str:
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

def get_secs_difference(time, new_time):
    """获取两个时间相隔的秒数

    Args:
        time (_type_): 旧时间
        new_time (_type_): 新时间

    Returns:
        int: 秒数
    """
    difference = new_time - time
    seconds_diff = difference.total_seconds()
    return seconds_diff

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
