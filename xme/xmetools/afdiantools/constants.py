"""爱发电开放平台常量：接口地址、分页大小、缓存与超时。"""

# 开放平台 API 基础地址（query-order / query-sponsor / ping）
API_BASE = "https://afdian.com/api/open"
# OAuth2 授权页与 code 兑换接口
AUTHORIZE_URL = "https://afdian.com/oauth2/authorize"
OAUTH_TOKEN_URL = "https://afdian.com/api/oauth2/access_token"

# query-order 每页固定 50 条，query-sponsor 每页固定 20 条（官方文档）
ORDER_PAGE_SIZE = 50
SPONSOR_PAGE_SIZE = 20

# 全量订单/赞助者列表的内存缓存秒数，防止指令频繁刷 API
CACHE_TTL = 300
# 单次全量拉取的最大页数保护，防止订单量异常时无限翻页
MAX_PAGES = 100
# 开放平台请求超时（秒）
REQUEST_TIMEOUT = 30

# OAuth 登录 state（JWT）默认有效期（秒）
STATE_TTL = 600
