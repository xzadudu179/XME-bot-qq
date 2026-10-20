"""兽聚时间线过滤：按地区/时间/名称筛选活动（纯逻辑，与网络、渲染分离）。"""
import re

from xme.xmetools.loctools import short_region

from .providers.base import FurEvent

# 时间过滤词形式：2026 / 2026年（年份），2026.10、2026-10、2026/10、2026年10月（年月），10月（月份）
_YEAR_MONTH_RE = re.compile(r"(\d{4})\s*[.\-/年]\s*(\d{1,2})\s*月?")
_YEAR_RE = re.compile(r"(\d{4})\s*年?")
_MONTH_RE = re.compile(r"(\d{1,2})\s*月")


def _parse_time_filter(token: str) -> tuple[int | None, int | None] | None:
    """把过滤词解析为 (年, 月) 约束，不是合法时间形式时返回 None。"""
    match = _YEAR_MONTH_RE.fullmatch(token)
    if match:
        month = int(match.group(2))
        return (int(match.group(1)), month) if 1 <= month <= 12 else None
    match = _YEAR_RE.fullmatch(token)
    if match:
        return (int(match.group(1)), None)
    match = _MONTH_RE.fullmatch(token)
    if match:
        month = int(match.group(1))
        return (None, month) if 1 <= month <= 12 else None
    return None


def _time_matches(event: FurEvent, condition: tuple[int | None, int | None]) -> bool:
    """活动开始日期是否落在过滤的年/月内（与时间线按开始月分组的口径一致）。"""
    year, month = condition
    return (year is None or event.start.year == year) and (month is None or event.start.month == month)


def _place_matches(event: FurEvent, token: str) -> bool:
    """活动地区是否匹配过滤词：先归一行政区划后缀，再按省份/城市互含判断。"""
    token = short_region(token)
    if not token:
        return False
    province_hit = bool(event.province) and (
        token == event.province or token in event.province or event.province in token)
    region_hit = bool(event.region) and (token in event.region or event.region in token)
    return province_hit or region_hit


def _name_matches(event: FurEvent, token: str) -> bool:
    """活动名或主办方是否包含过滤词（忽略大小写与空格）。"""
    normalized = "".join(token.casefold().split())
    if not normalized:
        return False
    haystack = "".join((event.title + event.org).casefold().split())
    return normalized in haystack


def filter_events(events: list[FurEvent], text: str) -> list[FurEvent]:
    """按条件过滤活动列表：条件留空时返回全部活动。

    每个词独立判定约束类型，优先级为 时间/地区 → 名称：
    时间形式（年 / 年月 / 月）按时间约束；能在活动地区中命中的词按地区约束；
    其余按名称约束。地区与时间优先，保证「武汉」这类既像地名又可能出现在
    名称里的词按地区解释。

    多个时间词之间取并集（如「10月 11月」= 这两个月的活动），
    时间条件整体与地区/名称条件之间为且关系。
    """
    tokens = text.split()
    if not tokens:
        return list(events)
    time_ranges: list[tuple[int | None, int | None]] = []
    conditions = []
    for token in tokens:
        time_range = _parse_time_filter(token)
        if time_range is not None:
            time_ranges.append(time_range)
        elif any(_place_matches(e, token) for e in events):
            conditions.append(lambda e, t=token: _place_matches(e, t))
        else:
            conditions.append(lambda e, t=token: _name_matches(e, t))
    return [
        e for e in events
        if (not time_ranges or any(_time_matches(e, tr) for tr in time_ranges))
        and all(cond(e) for cond in conditions)
    ]
