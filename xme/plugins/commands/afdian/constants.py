"""afdian 插件常量：子命令名、排行与展示上限、时间格式（单一来源）。"""

# 子命令名
CMD_RANK = 'rank'
CMD_LOGIN = 'bind'
CMD_UNBIND = "unbind"
CMD_ME = 'me'
CMD_STAT = 'stats'
CMD_SEND = 'send'

# 排行榜展示条数上限（.afd rank <数量>）
RANK_DEFAULT_COUNT = 10
RANK_MAX_COUNT = 20

# .afd me 最近订单展示条数
RECENT_ORDER_SHOWN = 5

# 通用时间显示格式
TIME_FORMAT = "%Y-%m-%d %H:%M"
