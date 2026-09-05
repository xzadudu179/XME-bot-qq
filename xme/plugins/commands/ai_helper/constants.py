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
COMPRESS_MAX_LENGTH = 4000

# 单会话 history 文件夹（AI 转存文件）的资源上限
HISTORY_MAX_FILES = 256                 # 最多 256 个文件
HISTORY_MAX_SIZE = 10 * 1024 * 1024     # 最多 10 MB

# 每个用户最多可创建的 AI 会话数（含默认会话）
MAX_SESSIONS = 25
# 会话最长名字
SESSION_NAME_MAX_LEN = 20

# ---- 共享会话（多用户共享一个 AI 会话，见 share.py）----

# 共享会话的存储目录与文件名（ai_historys 下单开，与用户目录平级）
SHARED_DIR_NAME = "shared"              # data/ai_historys/shared/<群号码>/
SHARED_META_FILE = "meta.json"          # 状态文件（群主/成员/请求/屏蔽等）
SHARED_HISTORY_FILE = "history.json"    # 共享历史（与普通会话同格式）
SHARED_GLOBAL_META_FILE = ".global_meta.json"  # 共享全局状态（群号码水位 next_code_n，只增不减，可扩展）

# 用户目录下的状态文件（. 开头，AISession.all 扫描天然跳过）
JOINED_FILE = ".joined"                 # 已加入的共享会话群号码，每行一个，顺序即 a 序号
CURRENT_SHARED_FILE = ".current_shared" # 旧版双指针遗留（仅用于迁移到统一指针，迁移后即删）

# 群号码：AI0000 起递增，数字最少 4 位（≥10000 自然变 5 位），最多 8 位
SHARED_CODE_PREFIX = "AI"
SHARED_CODE_WIDTH = 4
SHARED_CODE_MAX_N = 99_999_999

# 限额
MAX_SHARED_MEMBERS = 10                 # 单个共享会话成员上限（群主是 1 号成员，占名额）
MAX_JOINED_SHARED = 20                  # 单用户最多同时加入（含创建）的共享会话数
JOIN_REQUEST_COOLDOWN = 600             # 重复请求加入的冷却秒数（10 分钟）

# /ai -c rev 支持的操作
SHARED_REQUEST_OPS = ("apr", "rej", "block")
# 新建共享会话的默认标题
DEFAULT_SHARED_TITLE = "共享会话"
# /ai -c history 最多展示的普通记录条数（每条拆 提问+回答 两个转发节点）
MAX_HISTORY_VIEW = 30

# 生成图片 credits 用量
IMAGE_GEN_CREDITS = 80000

# url 下载文件最大大小
MAX_DOWNLOAD_FILE_SIZE = 20 * 1024 * 1024