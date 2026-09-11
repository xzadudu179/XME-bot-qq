__plugin_name__ = "ai_helper"

# /ai 指令的别名（agent 内识别同聊天追加消息是否为 ai 指令时复用）
COMMAND_ALIAS = ["ai"]

MAX_CHECK_TIMES = 1400
MAX_HISTORY_COUNT = 80
MAX_TOOL_CALL_TIMES = 1000
# AI 免费 credits 额度（每自然周，周一 00:00 GMT+8 重置；超出部分从自存 credits 扣）
TOKENS_LIMIT_WEEKLY = 12_000_000

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
FLASH_MODEL = "deepseek-flash"

# ---- 多 Provider：模型目录 / 能力配置 / 流式日志（配置单点，可在此直接改）----
# 说明：密钥与端点写在 keys.py 的 LLM_PROVIDERS（keys.py 不提交）；
# 本段只放"可提交"的目录信息：别名 → provider/模型/能力/计费倍率/上下文上限。
# 切换第三方（如 DeepSeek）：在 keys.py 加 provider 配置，再在此处加一个别名即可。

# 默认模型别名（/ai 不带 -m 时使用）
LLM_DEFAULT_MODEL = "dsflash"

# 模型别名 → 目录项；provider 需在 keys.py 的 LLM_PROVIDERS 里存在
LLM_MODELS = {
    "flash": {
        "provider": "glm",
        "model": "glm-5.3-flash",
        "vision": True,              # 是否支持图片/视觉输入（决定图片直注入与带图切换）
        "context_limit": 1_000_000,  # 输入上下文上限（tokens，触发轮内折叠）
        "credit_multiplier": 1,      # credits 计费倍率
        "cache_credit_ratio": 0.25,  # 缓存命中的 tokens 按该比例计费（GLM 口径）
        "description": "glm-5.3-flash 模型",
    },
    "pro": {
        "provider": "glm",
        "model": "glm-5.3",
        "vision": False,
        "context_limit": 1_000_000,
        "credit_multiplier": 10,
        "cache_credit_ratio": 0.25,
        "description": "glm-5.3 模型",
    },
    "dsflash": {
        "provider": "deepseek",
        "model": "deepseek-flash",
        "vision": True,
        "context_limit": 1_000_000,
        "credit_multiplier": 1.2,
        "cache_credit_ratio": 0.02,  # DeepSeek 缓存折扣很低（命中仅按 2% 计）
        "description": "deepseek-flash 模型",
    },
    # "xzadudu179": {
    #     "provider": "kirari",
    #     "model": "xzadudu179",
    #     "vision": True,
    #     "context_limit": 1_000_000,
    #     "credit_multiplier": 0,
    #     "description": "???",
    # },
    # "localgpt": {
    #     "provider": "local",
    #     "model": "gpt-oss-20b",
    #     "vision": False,
    #     "context_limit": 32000,
    #     "credit_multiplier": 0,
    #     "description": "本地 gpt 小模型，只有32k上下文，没什么用但免费",
    # }


}

# 能力配置：各项能力用哪个 provider/模型；api 标识实现方式
# （"chat" 走对话协议；glm_* 为 GLM 专属接口；不方便的第三方可保留 glm 实现）
LLM_CAPABILITIES = {
    "vision": {"provider": "glm", "model": "glm-5.3-flash", "api": "chat"},
    "ocr": {"provider": "glm", "model": "glm-ocr", "api": "glm_layout_parsing"},
    "image_gen": {"provider": "glm", "model": "glm-image", "api": "glm_images"},
    "web_reader": {"provider": "glm", "model": "", "api": "glm_reader"},
    "moderation": {"provider": "glm", "model": "", "api": "glm_moderations"},
}

# 半流式日志：把模型的增量输出（思考/回复/工具调用）逐块写进 ai_helper 调试日志，
# 便于后台排查模型输出问题；最终回复形态与计费完全不受影响
LLM_STREAM_LOG = True

# 单次对话调用超时（秒）
LLM_TIMEOUT = 300.0

# 缓存 tokens 的默认计费倍率（未在模型目录里单独配置时使用；0.25 = GLM 口径）
DEFAULT_CACHE_CREDIT_RATIO = 0.25

# ---- 动态模型分配（按话题自动挑选默认模型）----
# 仅在"用户没有自己设置默认模型（/ai -m xxx）且本次没带 -m"时生效；
# 想要彻底关闭：把 LLM_TOPIC_ROUTING_ENABLED 设为 False（行为与关闭前完全一致）
LLM_TOPIC_ROUTING_ENABLED = True

# 类别 → 模型别名（键就是分类器要输出的类别，单点维护：改这里即可增删类别/换模型）
LLM_TOPIC_ROUTING = {
    "闲聊": "flash",
    "讲故事": "flash",
    "角色扮演": "flash",
    "编程": "dsflash",
    "信息检索": "dsflash",
    "其他": "dsflash",
}

# 分类器候选链（按顺序尝试，前一个失败就换下一个）：直接给 provider + model，
# 无需进 LLM_MODELS 目录。实测（2026-09）：glm-4.7-flash 限流严重（账户级 rate_limit），
# glm-4.7-flashx 单次 40s 太慢，glm-4.5-air 约 1s、glm-4-flashx 约 0.2s 稳定可用，
# 故把稳定的放前面、免费的放最后兜底。
LLM_TOPIC_CLASSIFIERS = [
    {"provider": "glm", "model": "glm-4.5-air"},
    {"provider": "glm", "model": "glm-4-flashx"},
    {"provider": "glm", "model": "glm-4.7-flash"},
]
LLM_TOPIC_BILLABLE = False   # 分类调用是否计入用户 credits（内部开销，默认不计）
LLM_TOPIC_MAX_CHARS = 500    # 本次输入最多取前 N 字
# 话题判断要带上下文：角色扮演/设定常出现在对话开头，只看当前这句会判错
LLM_TOPIC_CONTEXT_ITEMS = 3   # 取最近 N 轮历史（用户+AI）
LLM_TOPIC_CONTEXT_CHARS = 600  # 上下文总长度上限（超出截断，控制 tokens 与延迟）
LLM_TOPIC_TIMEOUT = 8.0      # 单个候选模型的超时；超时/失败换下一个，全失败用兜底类别
LLM_TOPIC_FAIL_STREAK = 3    # 整条候选链都失败达该次数 → 熔断
LLM_TOPIC_COOLDOWN = 120.0   # 熔断时长（秒）；期间不发起分类请求，直接用兜底类别

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