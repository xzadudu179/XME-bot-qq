"""舞萌插件常量：入口/子命令别名、水鱼 API 地址、限频参数与默认皮肤（单一来源）。

自定义指令名：修改本文件的别名列表后重启 bot 即可生效。
"""

# 入口指令名与别名
CMD_MAI = 'mai'
MAI_ALIAS = ['舞萌', 'maimai']

# 子命令名与别名（改这里即可自定义子指令，重启生效）
CMD_B50 = 'b50'
B50_ALIAS = ['b50', '查分', '查询成绩']
CMD_BIND = 'bind'
BIND_ALIAS = ['bind', '绑定']
CMD_UPDATE = 'update'
UPDATE_ALIAS = ['update', '更新数据', '导入token', '上传分数']
CMD_UNBIND = 'unbind'
UNBIND_ALIAS = ['unbind', '解绑']

# 水鱼查分器（Diving-Fish）API
API_BASE = 'https://www.diving-fish.com/api/maimaidxprober'
QUERY_PLAYER_PATH = '/query/player'
PLAYER_RECORDS_PATH = '/player/records'
MUSIC_DATA_PATH = '/music_data'

# 曲绘：主源为水鱼官方 covers（png，id 补零 5 位，10001~11000 减 10000，见 covers.cover_divingfish_url）；
# 备源为落雪资产站 jacket（水鱼 id 换算见 covers.jacket_lxns_id）
COVER_DIVINGFISH_URL = 'https://www.diving-fish.com/covers/{}.png'
JACKET_URL = 'https://assets2.lxns.net/maimai/jacket/{}.png'

# maimai 官方风格徽章图标（落雪查分器前端同款资源）
# fc：fc/fcp/ap/app；fs：fs/fsp/fsd(FDX)/fsdp(FDX+)/sync（同步游玩）
BADGE_ICON_URL = 'https://maimai.lxns.net/assets/maimai/music_icon/{}.webp'
BADGE_NAMES = ('fc', 'fcp', 'ap', 'app', 'fs', 'fsp', 'fsd', 'fsdp', 'sync')

# 本地资源：徽章/字体子集/卡头背景（入库）；rating 框、DX 星贴片、谱面类型贴图的
# 最新版由官方资源包提供（见 RESOURCE_DIR，不入库，启动时自动下载）
BADGE_DIR = './static/maimai/badges'
MAIMAI_FONT_SUBSET_PATH = './static/maimai/fonts/sgm-subset.ttf'  # 数字/拉丁子集（查分卡内嵌用）
COVER_CACHE_DIR = './data/maimai/covers'

# DX Rating 段位映射：(区间上界, 编号)；上界 None 表示最后一段
# 分档依据 maimai DX 官方姓名框（灰蓝绿黄橙紫红银金白金彩），编号对应
# 资源包内 prism_plus/UI_CMN_DXRating_{编号}.png
RATING_BANDS = (
    (999, '01'),
    (1999, '02'),
    (3999, '03'),
    (6999, '04'),
    (9999, '05'),
    (11999, '06'),
    (12999, '07'),
    (13999, '08'),
    (14499, '09'),
    (14999, '10'),
    (None, '11'),
)

# maimaiDX(Hoshino) 官方静态资源包：体积约 467MB，不入库（.gitignore），
# 由 bot 启动时自动下载并解压出 pic 子集；/f/ 分享链接会自动 302 到带签名的直链
RESOURCE_PACK_URL = 'https://cloud.yuzuchan.moe/f/34s7/Resource%20CN1.55.7z'
RESOURCE_DIR = './static/maimai/resource'

# 曲绘/徽章并发下载限制（对图源友好）
RESOURCE_CONCURRENCY = 5

# 启动 1 分钟后是否在后台补齐一次曲绘缓存
SYNC_ON_STARTUP = True

# 曲目表缓存时长（秒）
MUSIC_CACHE_TTL = 24 * 60 * 60

# b50 查分限频：B50_LIMIT_INTERVAL 单位时间内最多 B50_LIMIT_COUNT 次
B50_LIMIT_NAME = 'mai_b50'
B50_LIMIT_INTERVAL = 1
B50_LIMIT_COUNT = 10

# 默认查分卡皮肤名（official = 官方素材流式排版）
DEFAULT_SKIN = 'official'

# 调试：每次 b50 渲染把最终 HTML 存到项目根目录 b50_debug.html（固定覆盖，仅留最新）
DEBUG_SAVE_HTML = False
DEBUG_HTML_PATH = './b50_debug.html'

# 渲染缓存：同一 HTML（已包含头像/背景等全部资源状态）直接复用上次出图
RENDER_CACHE_DIR = './data/maimai/render_cache'
RENDER_CACHE_MAX = 300


# 导入 Token 在回复中打码时保留的可见前缀长度
TOKEN_MASK_PREFIX = 4
