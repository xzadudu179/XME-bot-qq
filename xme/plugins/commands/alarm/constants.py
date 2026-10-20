"""alarm 插件常量：容量、名字长度、存档与调度宽限（单点来源）。"""

# 单用户同时允许存在的未到期计时器数量
MAX_ACTIVE_PER_USER = 20
# 计时器名字长度上限（字符）
NAME_MAX_CHARS = 30
# 管理指令的保留字（大小写不敏感）：`/alm del ALL` 一次清掉全部，计时器不能叫这个名字
CLEAR_ALL_KEYWORD = "ALL"
# 去重容差（秒）：同名且到点时间相差不超过这么多秒时，视为重复，不再新建
DUPLICATE_TOLERANCE_SECS = 60
# 未到期计时器存档路径（重启后恢复）
STORE_PATH = "./data/alarm_timers.json"
# 重启恢复时，已错过的计时器在启动后延迟这么多秒补响（等 bot 起来）
STARTUP_GRACE_SECS = 10
# apscheduler 错过执行时间的宽限（秒）：事件循环繁忙时到点任务不丢
MISFIRE_GRACE_SECS = 3600
# 剩余时间超过这个秒数时，确认文案用自然语句时间（「明天 9点05分」）而不是时长（「18小时」）
NATURAL_TIME_THRESHOLD_SECS = 7200

# 比"一天一次"更频繁的循环单位：没加 bot 好友的用户不允许添加这类循环
SUB_DAILY_REPEAT_UNITS = ("minute", "hour")
