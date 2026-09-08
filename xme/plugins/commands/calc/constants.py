"""calc 插件常量（单一来源）。"""

MAX_ARG_LEN = 1000
"""表达式最大字符数"""

PARSE_TIMEOUT = 7.5
"""解析 + 求值沙箱墙钟超时（秒）"""

DRAW_TIMEOUT = 15
"""绘图沙箱墙钟超时（秒）"""

DRAW_MEM_MB = 768
"""绘图沙箱内存上限（MB），matplotlib + sympy 导入开销较大"""

DRAW_FSIZE_MB = 32
"""绘图沙箱允许写入的单文件上限（MB），需要落盘 PNG"""

MAX_INT_DIGITS = 1000
"""sympy 表达式中整数字面量的最大位数"""

RESULT_STR_MAX = 3000
"""结果字符串最大长度，超出视为结果过大"""
