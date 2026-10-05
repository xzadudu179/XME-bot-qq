"""FCC API（furrycons.cn 兽展日历）适配器，实现 FurProvider 接口。

接口文档：https://docs.furrycons.cn/docs/intro
鉴权：请求头 Authorization 直接携带 token（dashboard.furrycons.cn 工作台申请）。
图床 images.furrycons.cn 按 TLS 指纹拦截 Python HTTP 客户端（aiohttp/urllib/httpx
均返回反爬挑战页），宣传图须经系统 curl 下载。
"""
import asyncio
from datetime import datetime, timedelta, timezone

from keys import FURCONS_TOKEN
from nonebot.log import logger
from xme.xmetools.loctools import derive_province
from xme.xmetools.reqtools import PROXY_URL, assert_public_http_url, fetch_data

from .base import CST, IMAGE_MAX_SIZE, FurAPIError, FurEvent, FurProvider

BASE_URL = "https://api.furrycons.cn/open"
PAGE_SIZE = 100
# 倒计时时间表从 60 天前开始拉取，让刚结束的活动也能在时间线上展示
COUNTDOWN_PAST_DAYS = 60
# 翻页上限，防止异常的 total 导致死循环拉取
MAX_PAGES = 5

# 已文档化/可预期的 status 值到统一状态的映射，未命中的按起止日期推导
STATUS_STATES = {
    "cancelled": 4,
    "canceled": 4,
    "ticketing": 2,
    "selling": 2,
    "ongoing": 3,
    "in_progress": 3,
    "finished": 0,
    "completed": 0,
    "ended": 0,
}


def _parse_time(text: str) -> datetime:
    """解析 FCC 的 ISO 8601 时间（如 2026-03-06T02:00:00.000Z）并转为东八区。"""
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(CST)
    except (ValueError, AttributeError) as e:
        raise FurAPIError(f"时间格式无法解析：{text}") from e


def _derive_state(status: str, start: datetime, end: datetime) -> int:
    """由 status 字符串与起止日期推导统一活动状态。"""
    known = STATUS_STATES.get((status or "").lower())
    if known is not None:
        return known
    today = datetime.now(CST).date()
    if today < start.date():
        return 1
    if today <= end.date():
        return 3
    return 0


def _map_event(raw: dict) -> FurEvent:
    """把 FCC 事件 JSON 映射为规范化 FurEvent，缺失字段容忍为空。"""
    start = _parse_time(raw["startDate"])
    end = _parse_time(raw["endDate"])
    return FurEvent(
        title=str(raw.get("name") or "").strip(),
        org=str((raw.get("organization") or {}).get("name") or "").strip(),
        state=_derive_state(str(raw.get("status") or ""), start, end),
        start=start,
        end=end,
        region=str(raw.get("region") or ""),
        address=str(raw.get("address") or ""),
        image=str(raw.get("thumbnail") or ""),
        url=str(raw.get("url") or ""),
        province=derive_province(str(raw.get("region") or "")),
    )


async def _fetch_events(params: dict) -> list[dict]:
    """请求事件列表接口并翻页取全，返回原始事件 dict 列表。"""
    events: list[dict] = []
    for current in range(1, MAX_PAGES + 1):
        try:
            resp = await fetch_data(
                f"{BASE_URL}/event",
                raise_error=True,
                headers={"Authorization": FURCONS_TOKEN},
                params={**params, "current": current, "pageSize": PAGE_SIZE},
            )
        except FurAPIError:
            raise
        except Exception as e:
            raise FurAPIError(f"FCC API 请求失败（{e.__class__.__name__}）") from e
        if not isinstance(resp, dict) or not isinstance(resp.get("data"), list):
            raise FurAPIError("FCC API 返回格式异常")
        events.extend(resp["data"])
        if current * PAGE_SIZE >= resp.get("total", 0) or not resp["data"]:
            break
    return events


def _fuzzy_match(raw: dict, keyword: str) -> bool:
    """本地模糊匹配：关键词与 名称/主办方/slug 都做 忽略大小写+去空格 的子串比较。"""
    normalized = "".join(keyword.casefold().split())
    if not normalized:
        return False
    haystack = "".join((
        str(raw.get("name") or ""),
        str((raw.get("organization") or {}).get("name") or ""),
        str(raw.get("slug") or ""),
    ))
    return normalized in "".join(haystack.casefold().split())


class FurryconsProvider(FurProvider):
    """furrycons.cn（FEC·兽展日历）数据源。"""

    name = "furrycons"
    source = "FEC·兽展日历 (furrycons.cn)"

    async def get_countdown(self) -> list[FurEvent]:
        """获取近期兽聚时间表（自 60 天前起），按开始时间升序。"""
        since = datetime.now(timezone.utc) - timedelta(days=COUNTDOWN_PAST_DAYS)
        raws = await _fetch_events({
            "eventStartAt": since.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        })
        events = [_map_event(raw) for raw in raws]
        return sorted(events, key=lambda e: e.start)

    async def search(self, keyword: str) -> list[FurEvent]:
        """按关键词搜索兽聚活动。

        数据源的搜索只匹配活动名且大小写敏感，先走它作为快路径；
        无结果时全量拉取后本地模糊匹配活动名/主办方/slug，
        覆盖忽略大小写、忽略空格、只记得品牌名等情况。
        """
        raws = await _fetch_events({"search": keyword})
        if not raws:
            raws = [raw for raw in await _fetch_events({}) if _fuzzy_match(raw, keyword)]
        return [_map_event(raw) for raw in raws]

    async def fetch_image_data(self, url: str) -> bytes | None:
        """经系统 curl 下载宣传图：图床按 TLS 指纹放行 curl、拦截 Python 客户端。"""
        if not url:
            return None
        assert_public_http_url(url)
        # 不跟随重定向：起始 URL 已做 SSRF 校验，避免跳转到未校验地址
        cmd = ["curl", "-fsS", "--max-time", "45",
               "--max-filesize", str(IMAGE_MAX_SIZE)]
        if PROXY_URL:
            cmd += ["-x", PROXY_URL]
        cmd.append(url)
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL)
            data, _ = await proc.communicate()
        except (OSError, asyncio.TimeoutError) as e:
            logger.warning(f"兽聚宣传图下载失败（{url}）：{e}")
            return None
        if proc.returncode != 0:
            logger.warning(f"兽聚宣传图下载失败（{url}）：curl 退出码 {proc.returncode}")
            return None
        return self._validate_image(data, url)
