"""爱发电开放平台客户端：签名请求、分页拉取、OAuth 兑换与登录 state 签发。

对外使用模块级单例 ``AFDIAN_CLIENT``（仿 dbtools.DATABASE 先例），
密钥均来自根目录 keys.py，本模块不感知 QQ 消息层。
"""
import json
import time
from datetime import datetime
from urllib.parse import urlencode

import aiohttp
import jwt
from keys import (
    AFDIAN_OAUTH_CLIENT_ID,
    AFDIAN_OAUTH_REDIRECT_URI,
    AFDIAN_OAUTH_SECRET,
    AFDIAN_TOKEN,
    AFDIAN_USER_ID,
    afdian_sign,
)
from nonebot.log import logger

from xme.xmetools.afdiantools.constants import (
    API_BASE,
    AUTHORIZE_URL,
    CACHE_TTL,
    MAX_PAGES,
    OAUTH_TOKEN_URL,
    REQUEST_TIMEOUT,
    STATE_TTL,
)


class AfdianApiError(Exception):
    """爱发电接口返回异常（ec != 200 或网络/解析失败）。"""


def parse_order_time(out_trade_no: str) -> datetime | None:
    """从订单号前 14 位解析下单时间（YYYYMMDDHHMMSS），解析失败返回 None。

    官方 query-order 的订单记录不含时间字段，订单号前缀即下单时间。
    """
    prefix = str(out_trade_no or "")[:14]
    if len(prefix) != 14 or not prefix.isdigit():
        return None
    try:
        return datetime.strptime(prefix, "%Y%m%d%H%M%S")
    except ValueError:
        return None


class AfdianClient:
    """爱发电开放平台客户端：统一签名、缓存与 OAuth 辅助方法。"""

    def __init__(
        self,
        user_id: str,
        token: str,
        oauth_client_id: str,
        oauth_secret: str,
        redirect_uri: str,
        cache_ttl: int = CACHE_TTL,
    ) -> None:
        """初始化客户端。

        Args:
            user_id (str): 创作者的爱发电 user_id
            token (str): 开放平台 API token
            oauth_client_id (str): OAuth 应用 client_id
            oauth_secret (str): OAuth 应用 client_secret（同时用作 state JWT 密钥）
            redirect_uri (str): OAuth 回调地址，须与爱发电后台登记一致
            cache_ttl (int): 全量列表缓存秒数
        """
        self.user_id = user_id
        self.token = token
        self.oauth_client_id = oauth_client_id
        self.oauth_secret = oauth_secret
        self.redirect_uri = redirect_uri
        self.cache_ttl = cache_ttl
        # {缓存键: (过期时间戳, 值)}，仅存于实例内，避免模块级可变状态
        self._cache: dict[str, tuple[float, object]] = {}

    def _cache_get(self, key: str):
        cached = self._cache.get(key)
        if cached is None:
            return None
        expires_at, value = cached
        if time.time() > expires_at:
            self._cache.pop(key, None)
            return None
        return value

    def _cache_set(self, key: str, value) -> None:
        self._cache[key] = (time.time() + self.cache_ttl, value)

    async def _signed_post(self, method: str, params: dict) -> dict:
        """签名并 POST 开放平台接口，返回完整响应 dict（含 ec/em/data）。

        签名单点在 keys.afdian_sign（md5(token + "params" + params + "ts" + ts
        + "user_id" + user_id)），params 必须是与请求体一致的 JSON 字符串。
        """
        params_str = json.dumps(params, ensure_ascii=False)
        body = afdian_sign(params_str)
        try:
            async with aiohttp.ClientSession() as aiosession:
                async with aiosession.post(
                    f"{API_BASE}/{method}",
                    json=body,
                    timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
                ) as response:
                    response.raise_for_status()
                    return await response.json(content_type=None)
        except aiohttp.ClientError as e:
            logger.warning(f"爱发电接口 {method} 请求失败: {e}")
            raise AfdianApiError(f"爱发电接口 {method} 请求失败") from e
        except Exception as e:
            logger.warning(f"爱发电接口 {method} 响应解析失败: {e}")
            raise AfdianApiError(f"爱发电接口 {method} 响应异常") from e

    def _unwrap(self, resp: dict, method: str) -> dict:
        """校验开放平台响应 ec == 200 并返回 data 部分。"""
        if not isinstance(resp, dict) or resp.get("ec") != 200:
            em = resp.get("em") if isinstance(resp, dict) else resp
            raise AfdianApiError(f"爱发电接口 {method} 返回异常: {em}")
        return resp.get("data") or {}

    async def ping(self) -> dict:
        """测试签名与网络连通性，返回 data（含 echo 的 request 信息）。

        实测服务端对空对象 params（"{}"）会误报 400003 "params was not
        valid json string"，因此这里传一个无害的非空 params。
        """
        return self._unwrap(await self._signed_post("ping", {"page": 1}), "ping")

    async def fetch_orders_page(self, page: int = 1) -> tuple[list[dict], int, int]:
        """拉取一页订单，返回 (订单列表, 总订单数, 总页数)。"""
        data = self._unwrap(await self._signed_post("query-order", {"page": page}), "query-order")
        return (
            data.get("list") or [],
            int(data.get("total_count") or 0),
            int(data.get("total_page") or 0),
        )

    async def fetch_sponsors_page(self, page: int = 1) -> tuple[list[dict], int, int]:
        """拉取一页赞助者，返回 (赞助者列表, 总人数, 总页数)。"""
        data = self._unwrap(await self._signed_post("query-sponsor", {"page": page}), "query-sponsor")
        return (
            data.get("list") or [],
            int(data.get("total_count") or 0),
            int(data.get("total_page") or 0),
        )

    async def get_orders_by_no(self, out_trade_nos: list[str]) -> list[dict]:
        """按订单号精确查询订单（一次最多约 50 个）。"""
        if not out_trade_nos:
            return []
        data = self._unwrap(
            await self._signed_post("query-order", {"out_trade_no": ",".join(out_trade_nos)}),
            "query-order",
        )
        return data.get("list") or []

    async def get_all_orders(self, force: bool = False) -> list[dict]:
        """获取全量订单列表（带缓存），订单按官方默认创建时间倒序。"""
        if not force:
            cached = self._cache_get("orders")
            if cached is not None:
                return cached
        orders, _, total_page = await self.fetch_orders_page(1)
        for page in range(2, min(total_page, MAX_PAGES) + 1):
            page_orders, _, total_page = await self.fetch_orders_page(page)
            orders.extend(page_orders)
        self._cache_set("orders", orders)
        return orders

    async def get_all_sponsors(self, force: bool = False) -> tuple[list[dict], int]:
        """获取全量赞助者列表（带缓存），返回 (赞助者列表, 总赞助人数)。"""
        if not force:
            cached = self._cache_get("sponsors")
            if cached is not None:
                return cached
        sponsors, total_count, total_page = await self.fetch_sponsors_page(1)
        for page in range(2, min(total_page, MAX_PAGES) + 1):
            page_sponsors, _, total_page = await self.fetch_sponsors_page(page)
            sponsors.extend(page_sponsors)
        self._cache_set("sponsors", (sponsors, total_count))
        return sponsors, total_count

    def build_authorize_url(self, state: str) -> str:
        """构造 OAuth2 授权页链接，state 为服务端签发的 JWT。"""
        params = urlencode({
            "response_type": "code",
            "scope": "basic",
            "client_id": self.oauth_client_id,
            "redirect_uri": self.redirect_uri,
            "state": state,
        })
        return f"{AUTHORIZE_URL}?{params}"

    def make_login_state(self, qq: int | str, ttl: int = STATE_TTL) -> str:
        """为 QQ 用户签发 OAuth state JWT（HS256，带过期时间）。"""
        payload = {"qq": str(qq), "exp": int(time.time()) + ttl}
        return jwt.encode(payload, self.oauth_secret, algorithm="HS256")

    def parse_login_state(self, state: str) -> str | None:
        """解析并校验 OAuth state JWT，返回 qq 号字符串；无效或过期返回 None。"""
        if not state:
            return None
        try:
            payload = jwt.decode(state, self.oauth_secret, algorithms=["HS256"])
        except jwt.PyJWTError:
            return None
        qq = payload.get("qq")
        return str(qq) if qq else None

    async def exchange_oauth_code(self, code: str) -> dict:
        """用授权 code 兑换用户标识，成功返回含 user_id / user_private_id 的 dict。

        官方 OAuth2 的该接口直接返回用户标识（无需 access_token），
        表单提交且 redirect_uri 不需要手动 encode。
        """
        form = {
            "grant_type": "authorization_code",
            "client_id": self.oauth_client_id,
            "client_secret": self.oauth_secret,
            "code": code,
            "redirect_uri": self.redirect_uri,
        }
        try:
            async with aiohttp.ClientSession() as aiosession:
                async with aiosession.post(
                    OAUTH_TOKEN_URL,
                    data=form,
                    timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
                ) as response:
                    resp = await response.json(content_type=None)
        except aiohttp.ClientError as e:
            logger.warning(f"爱发电 OAuth code 兑换请求失败: {e}")
            raise AfdianApiError("爱发电 OAuth code 兑换请求失败") from e
        return self._unwrap(resp if isinstance(resp, dict) else {}, "oauth/access_token")


AFDIAN_CLIENT = AfdianClient(
    user_id=AFDIAN_USER_ID,
    token=AFDIAN_TOKEN,
    oauth_client_id=AFDIAN_OAUTH_CLIENT_ID,
    oauth_secret=AFDIAN_OAUTH_SECRET,
    redirect_uri=AFDIAN_OAUTH_REDIRECT_URI,
)
