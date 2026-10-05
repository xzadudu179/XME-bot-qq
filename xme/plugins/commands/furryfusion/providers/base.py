"""兽聚信息源抽象层：规范化数据模型、异常与 Provider 接口。

命令层和卡片渲染只依赖本模块的 FurEvent / FurProvider，
具体 API 的字段差异由各 provider 适配器抹平。
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from nonebot.log import logger
from xme.xmetools.imgtools import decode_image_bytes
from xme.xmetools.reqtools import fetch_file_stream

# 兽展日历面向国内用户，时间统一按东八区做日期推导与展示
CST = timezone(timedelta(hours=8))

# 宣传图单张下载上限（数据源警告部分宣传图可超过 10MiB）
IMAGE_MAX_SIZE = 20 * 1024 * 1024


class FurAPIError(Exception):
    """数据源请求失败（网络、鉴权、解析等），info 为可向用户展示的原因。"""

    def __init__(self, info: str):
        self.info = info
        super().__init__(info)


@dataclass
class FurEvent:
    """规范化后的兽聚活动条目，时间均为东八区。

    state 为统一活动状态：0 已结束、1 预告中、2 售票中、3 活动中、4 已取消，
    文案映射见 cards.STATE。province 为省份简称（如 江苏），数据源推不出来时为空。
    """
    title: str
    org: str
    state: int
    start: datetime
    end: datetime
    region: str
    address: str
    image: str
    url: str
    province: str = ""

    @property
    def days_until(self) -> int:
        """距开始还有多少天（已开始为负数）。"""
        return (self.start.date() - datetime.now(CST).date()).days

    @property
    def duration_days(self) -> int:
        """活动持续天数（按起止日期差）。"""
        return (self.end.date() - self.start.date()).days

    @staticmethod
    def _fmt_date(date: datetime) -> str:
        """日期转 2026.3.6 形式的文本（不补零，跨平台安全）。"""
        return f"{date.year}.{date.month}.{date.day}"

    @property
    def time_start(self) -> str:
        """开始日期文本，如 2026.3.6。"""
        return self._fmt_date(self.start)

    @property
    def time_end(self) -> str:
        """结束日期文本，如 2026.3.8。"""
        return self._fmt_date(self.end)

    @property
    def time_text(self) -> str:
        """起止日期的紧凑展示，同年时省略结束年份，如 2026.3.6 - 3.8。"""
        if self.start.year == self.end.year:
            return f"{self.time_start} - {self.end.month}.{self.end.day}"
        return f"{self.time_start} - {self.time_end}"

    @property
    def full_title(self) -> str:
        """完整标题：品牌名·主题名（缺其一则只显示另一个）。"""
        if self.org and self.title:
            return f"{self.org}·{self.title}"
        return self.org or self.title

    @property
    def location_text(self) -> str:
        """展示用地点：省份与城市互不包含时显示 省·市（江苏·南京），否则原样。"""
        if self.province and self.province not in self.region and self.region not in self.province:
            return f"{self.province}·{self.region}"
        return self.region


class FurProvider(ABC):
    """兽聚数据源接口：所有 API 适配器按此规范接入。"""

    name: str = ""
    # 数据来源标注，用于卡片页脚与消息文案（如 "FEC·兽展日历"）
    source: str = ""

    @abstractmethod
    async def get_countdown(self) -> list[FurEvent]:
        """获取兽聚时间表（含刚结束的活动），按开始时间升序返回。"""

    @abstractmethod
    async def search(self, keyword: str) -> list[FurEvent]:
        """按关键词搜索兽聚活动，返回规范化条目列表。"""

    async def fetch_image_data(self, url: str) -> bytes | None:
        """下载活动宣传图并校验为有效图片，失败返回 None（调用方回退为无图）。

        默认实现走带浏览器 UA 的标准公网下载通道；图床有特殊拦截行为的
        数据源（如 furrycons）应覆写本方法。
        """
        if not url:
            return None
        try:
            data, _ = await fetch_file_stream(url, max_size=IMAGE_MAX_SIZE)
            return self._validate_image(data, url)
        except Exception as e:
            logger.warning(f"兽聚宣传图下载失败（{url}）：{e}")
            return None

    def _validate_image(self, data: bytes, url: str) -> bytes | None:
        """校验下载内容确为图片，防止反爬页等无效内容混入消息。"""
        try:
            decode_image_bytes(data, source=f"URL={url!r}")
            return data
        except ValueError as e:
            logger.warning(f"兽聚宣传图内容无效（{url}）：{e}")
            return None
