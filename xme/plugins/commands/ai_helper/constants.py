__plugin_name__ = "ai_helper"

# /ai 指令的别名（agent 内识别同聊天追加消息是否为 ai 指令时复用）
COMMAND_ALIAS = ["ai"]

MAX_CHECK_TIMES = 1400
MAX_HISTORY_COUNT = 80
MAX_TOOL_CALL_TIMES = 1000
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
MAX_SESSIONS = 40
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

# zip_files 打包的压缩包大小上限
MAX_ZIP_SIZE = 50 * 1024 * 1024

# extract_archive 解压上限（防压缩炸弹：条目数 / 解压总大小）
MAX_EXTRACT_FILES = 200
MAX_EXTRACT_TOTAL_SIZE = 50 * 1024 * 1024

# 语法检测的文件/内联代码大小上限（防超大输入拖垮解析进程）
MAX_SYNTAX_CHECK_SIZE = 1 * 1024 * 1024

# 语法检测子进程超时（秒），超时 kill
SYNTAX_CHECK_TIMEOUT = 15

# 语法检测子进程的地址空间上限（字节）：python/json 解析器用默认档；
# node（V8 启动即预留 ~1GiB 虚拟内存，512MiB 下 node 20 直接 OOM）必须单独放宽
SYNTAX_CHECK_AS_LIMIT = 512 * 1024 * 1024
SYNTAX_CHECK_AS_LIMIT_NODE = 2 * 1024 * 1024 * 1024

# ---- run_python 工具（沙箱内对文件副本执行 AI 编写的分析代码，见 functions/codeexec.py）----

RUN_PYTHON_TIMEOUT = 30                  # 沙箱墙钟超时（秒）
RUN_PYTHON_MEM_MB = 768                  # 内存上限（MB），matplotlib + numpy 同 calc 绘图档
RUN_PYTHON_FSIZE_MB = 16                 # 工作区内单文件写入上限（MB），要保存图表
RUN_PYTHON_OUTPUT_LIMIT = 8000           # 捕获 print 输出的最大字符数（超出保留末尾）
RUN_PYTHON_MAX_CODE = 20000              # 代码字符数上限
RUN_PYTHON_MAX_INPUT_SIZE = 20 * 1024 * 1024   # 输入文件大小上限
RUN_PYTHON_MAX_FILES = 10                # 产出文件数量上限
RUN_PYTHON_MAX_FILE_SIZE = 10 * 1024 * 1024    # 产出单文件大小上限

# 视觉模型名（图片直注入的判据 + 全插件单点引用，禁止再硬编码）
FLASH_MODEL = "glm-5.3-flash"

# 共享会话插入模式：待插入消息队列上限（对话进行中其他成员的消息）
MAX_PENDING_INSERTS = 5

# GLM thinking 参数（交错式思考）：
# 交错式思考自 GLM-4.5 起默认支持（工具调用之间/收到工具结果后继续思考），
# 硬性要求是把 assistant 消息的 reasoning_content 原样随工具结果回传（run_agent 已实现）。
# "clear_thinking": False 会额外开启保留式思考（跨轮保留思考内容，token 消耗显著更高）
THINKING_PARAMS = {
    "type": "enabled",
    # "clear_thinking": False,
}

# ---- 轮内上下文折叠（长时运行 agent：单轮持续调工具导致 messages 膨胀时主动瘦身）----

# 模型 → 输入上下文上限（tokens），按当次调用的模型动态查找
MODEL_CONTEXT_LIMITS = {
    "glm-5.3": 1_000_000,
    "glm-5.3-flash": 1_000_000,
}
CONTEXT_LIMIT_DEFAULT = 1_000_000        # 未知模型的兜底上限
FOLD_TRIGGER_RATIO = 0.75                # 真实输入达上限 75% → 一级折叠（删最早 reasoning）
FOLD_HARD_RATIO = 0.90                   # 达 90% → 二级折叠（早期工具结果替换为占位符）
FOLD_KEEP_RECENT_ASSISTANTS = 10         # 最近 N 条 assistant 保持原样（含完整思考）
FOLD_KEEP_RECENT_TOOLS = 10              # 最近 N 条 tool 消息保持原样

MAX_HISTORY_FILE_COUNTS = 100
MAX_HISTORY_FILES_SIZE = 100 * 1024 * 1024