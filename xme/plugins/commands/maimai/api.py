"""水鱼查分器（Diving-Fish）薄客户端：b50 查询、导入 Token 读成绩、曲目表缓存。

请求统一走 xmetools.reqtools；失败统一抛 MaimaiAPIError（reason 标明类别），
回复文案由命令层按 reason 映射，本模块不产生任何文案。
"""

import functools
import time

from nonebot.log import logger
from xme.xmetools.reqtools import DEFAULT_UA, fetch_data, fetch_data_post

from .constants import (
    API_BASE,
    MUSIC_CACHE_TTL,
    MUSIC_DATA_PATH,
    PLAYER_RECORDS_PATH,
    QUERY_PLAYER_PATH,
)

# MaimaiAPIError.reason 的合法取值
REASON_PRIVACY = 'privacy'
REASON_NOT_FOUND = 'not_found'
REASON_INVALID_TOKEN = 'invalid_token'
REASON_NETWORK = 'network'


class MaimaiAPIError(Exception):
    """水鱼 API 请求失败。

    Attributes:
        reason (str): 错误类别，privacy（隐私保护）/ not_found（查无此人）/
            invalid_token（导入 Token 无效）/ network（网络或其他异常）
        message (str): 原始错误信息，供日志与调试
    """

    def __init__(self, reason: str, message: str = "") -> None:
        self.reason = reason
        self.message = message
        super().__init__(f"{reason}: {message}")


async def query_player_b50(username: str | None = None, qq: int | str | None = None,
                           b50: bool = True) -> dict:
    """查询水鱼玩家成绩，返回查分器原始响应 dict。

    Args:
        username (str | None): 水鱼用户名，与 qq 至少提供一个
        qq (int | str | None): 玩家 QQ 号，与 username 至少提供一个
        b50 (bool): 是否返回 b50（False 时为简略信息，用于存在性检查）

    Returns:
        dict: 含 username/rating/nickname/plate/charts 等字段的原始响应

    Raises:
        ValueError: username 与 qq 均未提供
        MaimaiAPIError: 查无此人、隐私保护或网络异常
    """
    if not username and not qq:
        raise ValueError("username 和 qq 至少提供一个")
    body: dict = {"b50": b50}
    if username:
        body["username"] = username
    else:
        body["qq"] = str(qq)
    return await _post_query(body)


async def _post_query(body: dict) -> dict:
    """POST query/player 并按响应内容区分错误类别。"""
    try:
        data = await fetch_data_post(
            f"{API_BASE}{QUERY_PLAYER_PATH}",
            json=body,
            headers={"User-Agent": DEFAULT_UA},
        )
    except Exception as ex:
        logger.warning(f"水鱼查询请求异常: {ex}")
        raise MaimaiAPIError(REASON_NETWORK, str(ex)) from ex
    if isinstance(data, dict) and "charts" in data:
        return data
    # 查分器错误响应形如 {"message": "..."}；请求封装拿不到状态码，按 message 关键词分类
    message = data.get("message", "") if isinstance(data, dict) else str(data)[:100]
    reason = REASON_PRIVACY if "隐私" in message else REASON_NOT_FOUND
    raise MaimaiAPIError(reason, message)


async def username_exists(username: str) -> bool:
    """检查水鱼用户名是否存在（用于绑定校验，轻量查询不含成绩）。

    隐私保护的用户同样视为存在。

    Raises:
        MaimaiAPIError: 网络异常
    """
    try:
        await _post_query({"username": username})
        return True
    except MaimaiAPIError as ex:
        if ex.reason == REASON_PRIVACY:
            return True
        if ex.reason == REASON_NOT_FOUND:
            return False
        raise


async def fetch_records_payload(token: str) -> dict:
    """用成绩导入 Token 读取账号完整数据（records + username/rating 等）。

    Args:
        token (str): 水鱼官网生成的成绩导入 Token

    Returns:
        dict: 查分器原始响应（含 records 列表等字段）

    Raises:
        MaimaiAPIError: Token 无效或网络异常（reason=invalid_token）
    """
    try:
        data = await fetch_data(
            f"{API_BASE}{PLAYER_RECORDS_PATH}",
            response_type="json",
            raise_error=True,
            headers={"Import-Token": token, "User-Agent": DEFAULT_UA},
        )
    except Exception as ex:
        logger.warning(f"导入 Token 读取成绩失败: {ex}")
        raise MaimaiAPIError(REASON_INVALID_TOKEN, str(ex)) from ex
    if not isinstance(data, dict) or not isinstance(data.get("records"), list):
        raise MaimaiAPIError(REASON_INVALID_TOKEN, "响应缺少 records 字段")
    return data


async def fetch_records(token: str) -> list[dict]:
    """用成绩导入 Token 读取账号的全量成绩记录（同时用于验证 Token 有效性）。

    Args:
        token (str): 水鱼官网生成的成绩导入 Token

    Returns:
        list[dict]: 全量成绩记录列表

    Raises:
        MaimaiAPIError: Token 无效或网络异常（reason=invalid_token）
    """
    return (await fetch_records_payload(token))["records"]


class MusicLibrary:
    """水鱼曲目表缓存：过期或缺失时自动重新拉取（实例经 _music_library 单例持有）。"""

    def __init__(self) -> None:
        self._music: list[dict] | None = None
        self._fetched_at: float = 0.0

    async def get(self) -> list[dict]:
        """得到曲目表，超过 MUSIC_CACHE_TTL 后重新拉取，失败时抛 MaimaiAPIError。"""
        if self._music is None or time.time() - self._fetched_at > MUSIC_CACHE_TTL:
            try:
                data = await fetch_data(
                    f"{API_BASE}{MUSIC_DATA_PATH}",
                    response_type="json",
                    headers={"User-Agent": DEFAULT_UA},
                )
            except Exception as ex:
                logger.warning(f"拉取水鱼曲目表失败: {ex}")
                raise MaimaiAPIError(REASON_NETWORK, str(ex)) from ex
            if not isinstance(data, list):
                raise MaimaiAPIError(REASON_NETWORK, "music_data 响应格式异常")
            self._music = data
            self._fetched_at = time.time()
        return self._music


@functools.lru_cache(maxsize=1)
def _music_library() -> MusicLibrary:
    """进程内唯一的曲目表缓存实例。"""
    return MusicLibrary()


async def fetch_music_data() -> list[dict]:
    """得到水鱼曲目表（带 TTL 缓存）。"""
    return await _music_library().get()
