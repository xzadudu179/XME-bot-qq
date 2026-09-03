__plugin_name__ = "ai_helper"

MAX_CHECK_TIMES = 1000
MAX_HISTORY_COUNT = 80
MAX_TOOL_CALL_TIMES = 50
TOKENS_LIMIT = 6000000

# 长上下文：普通历史记录超过 COMPRESS_TRIGGER 条时，触发压缩最旧部分为摘要
COMPRESS_TRIGGER = 79
# 压缩时保留的最新的记录条数（其余压缩进摘要）
CONTEXT_KEEP_RECENT = 20
# 摘要最大长度（传给 ai_configs 里 memory 提示词的 {max_length}）
COMPRESS_MAX_LENGTH = 2000

# 单会话 history 文件夹（AI 转存文件）的资源上限
HISTORY_MAX_FILES = 256                 # 最多 256 个文件
HISTORY_MAX_SIZE = 10 * 1024 * 1024     # 最多 10 MB
