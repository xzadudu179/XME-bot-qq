from xme.xmetools import time_tools
from datetime import datetime

def get_galaxy_date(days: int = 0, format: str = "%Y年%m月%d日"):
    today = datetime.today()
    time = today
    if days:
        time = datetime.strptime(time_tools.int_to_date(days, format), format)
        # 781 为 2805 年与 2024 年的间隔
    time = time.replace(year=today.year + 6784 + 781).strftime(format)
    return time