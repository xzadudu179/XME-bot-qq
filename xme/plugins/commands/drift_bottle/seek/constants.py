"""seek 物品栏与持久数据相关的常量"""

# plugin_datas 中 seek 数据的命名空间键
SEEK_DATAS_KEY = "seek"
# plugin_datas 中物品栏的键名
INVENTORY_KEY = "inventory"
# plugin_datas 中统计数据的键名
STATS_KEY = "stats"
# 物品栏容量上限（普通模式）
INVENTORY_MAX_SLOTS = 6
# 无依无靠模式下可携带的物品上限
HARDCORE_ITEM_LIMIT = 3
# 结算时深度惩罚比例需要低于该值才会保存物品栏
ITEM_SAVE_PUNISH_RATE = 0.5
