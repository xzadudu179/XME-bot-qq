"""视频平台注册器：统一定义各平台可解析的链接形式与专属参数。

架构分两层（本包 videotools/ 内）：
- 本模块只做「配置」：VideoPlatform 用统一字段描述一个平台的全部可解析
  链接形式（url_patterns）与平台专属 yt-dlp 参数（ydl_opts），通过
  register_platform 注册进注册表；match_platform 是工厂函数，把链接映射到平台。
- core.py 做「流程」：从文本提取 URL → match_platform 判定平台 →
  交给 yt-dlp 解析/下载。

新增平台：在文件底部追加一个 VideoPlatform 并 register_platform 即可，
流程层零改动。url_patterns 只是「可解析形式」的白名单初筛（前缀匹配），
匹配不到一定不能解析，匹配到了实际能否解析仍以 yt-dlp 为准（失败会优雅降级）。
"""
import re
from collections.abc import Iterable
from dataclasses import dataclass, field


@dataclass(frozen=True)
class VideoPlatform:
    """单个视频平台的统一描述。

    name: 平台唯一标识（如 "bilibili"），用作注册表 key
    display_name: 展示名（如 "哔哩哔哩"）
    url_patterns: 全部可解析链接形式（re 前缀匹配，IGNORECASE）
    ydl_opts: 平台专属 yt-dlp 参数（UA、认证等），与公共参数合并，优先级高于公共默认
    """

    name: str
    display_name: str
    url_patterns: tuple[re.Pattern, ...]
    ydl_opts: dict = field(default_factory=dict)

    def matches(self, url: str) -> bool:
        """判断链接是否属于本平台的可解析形式（带不带 scheme 均可）。"""
        return any(p.match(url) for p in self.url_patterns)


# 注册表：平台配置的唯一来源（单点维护）；只允许通过 register_platform 修改
_PLATFORMS: dict[str, VideoPlatform] = {}


def register_platform(platform: VideoPlatform, *, replace: bool = False) -> VideoPlatform:
    """注册一个平台；重名默认抛 ValueError（防意外覆盖），replace=True 允许覆盖。"""
    if platform.name in _PLATFORMS and not replace:
        raise ValueError(f"平台已注册: {platform.name}")
    _PLATFORMS[platform.name] = platform
    return platform


def get_platform(name: str) -> VideoPlatform | None:
    """按平台标识取平台定义；不存在返回 None。"""
    return _PLATFORMS.get(name)


def all_platforms() -> tuple[VideoPlatform, ...]:
    """返回全部已注册平台（按注册顺序）。"""
    return tuple(_PLATFORMS.values())


def match_platform(url: str, *, names: Iterable[str] | None = None) -> VideoPlatform | None:
    """工厂函数：把一个链接匹配到已注册平台；匹配不到返回 None。

    url: 待判定的链接（带或不带 scheme 均可）
    names: 限定在这些平台（标识列表）中匹配；None 表示全部
    """
    if names is None:
        platforms = _PLATFORMS.values()
    else:
        platforms = (_PLATFORMS[n] for n in names if n in _PLATFORMS)
    for platform in platforms:
        if platform.matches(url):
            return platform
    return None


def _make_platform(name: str, display_name: str, patterns: tuple[str, ...], **ydl_opts) -> VideoPlatform:
    """按统一参数构造平台并编译正则；平台专属 yt-dlp 参数走 kwargs。"""
    return VideoPlatform(
        name=name,
        display_name=display_name,
        url_patterns=tuple(re.compile(p, re.IGNORECASE) for p in patterns),
        ydl_opts=ydl_opts,
    )


# ---- 内置平台定义（各平台全部可解析链接形式，统一结构，改这里即全量生效） ----

register_platform(_make_platform(
    "bilibili", "哔哩哔哩",
    (
        # 正片：BV 号 / av 号，www./m. 等子域均可
        r"(?:https?://)?(?:[\w-]+\.)?bilibili\.com/video/(?:BV[0-9A-Za-z]{10}|av\d+)",
        # 番剧/影视
        r"(?:https?://)?(?:[\w-]+\.)?bilibili\.com/bangumi/play/ep\d+",
        # App 分享短链
        r"(?:https?://)?b23\.tv/[\w-]+",
    ),
))

register_platform(_make_platform(
    "douyin", "抖音",
    (
        # App 分享短链
        r"(?:https?://)?v\.douyin\.com/[\w-]+",
        # 网页版视频页
        r"(?:https?://)?(?:www\.)?douyin\.com/video/\d+",
        # 旧版分享页
        r"(?:https?://)?(?:www\.)?iesdouyin\.com/share/video/\d+",
        # 直播间
        r"(?:https?://)?live\.douyin\.com/[\w-]+",
    ),
))

register_platform(_make_platform(
    "kuaishou", "快手",
    (
        # App 分享短链
        r"(?:https?://)?v\.kuaishou\.com/[\w-]+",
        # 网页版视频页
        r"(?:https?://)?(?:[\w-]+\.)?kuaishou\.com/short-video/[\w-]+",
    ),
))

register_platform(_make_platform(
    "weibo", "微博",
    (
        # 微博视频页
        r"(?:https?://)?(?:[\w-]+\.)?weibo\.com/tv/show/[\w.-]+",
        r"(?:https?://)?(?:[\w-]+\.)?weibo\.com/l/wbl/(?:live|p)/[\w.-]+",
    ),
))

register_platform(_make_platform(
    "youtube", "YouTube",
    (
        # watch / shorts / live / embed，music. 等子域均可
        r"(?:https?://)?(?:[\w-]+\.)?youtube\.com/(?:watch|shorts|live|embed)\b",
        # 短链
        r"(?:https?://)?youtu\.be/[\w-]+",
    ),
))

register_platform(_make_platform(
    "tiktok", "TikTok",
    (
        r"(?:https?://)?(?:www\.)?tiktok\.com/@[\w.-]+/video/\d+",
        # App 分享短链
        r"(?:https?://)?(?:vm|vt)\.tiktok\.com/[\w-]+",
    ),
))

register_platform(_make_platform(
    "twitter", "X (Twitter)",
    (
        # 推文（含视频），twitter.com / x.com
        r"(?:https?://)?(?:www\.|mobile\.|m\.)?(?:twitter|x)\.com/i?/?(?:[\w.%-]+/)?status(?:es)?/\d+",
        # 官方短链（跳转到任意推文，非视频推文会在解析阶段优雅失败）
        r"(?:https?://)?t\.co/[\w-]+",
    ),
))

register_platform(_make_platform(
    "instagram", "Instagram",
    (
        r"(?:https?://)?(?:www\.)?instagram\.com/(?:reel|reels|p|tv)/[\w-]+",
    ),
))

register_platform(_make_platform(
    "acfun", "AcFun",
    (
        r"(?:https?://)?(?:[\w-]+\.)?acfun\.cn/v/ac\d+",
    ),
))

register_platform(_make_platform(
    "facebook", "Facebook",
    (
        # watch 页（视频 id 在 query 里，前缀匹配即可）
        r"(?:https?://)?(?:[\w-]+\.)?facebook\.com/watch\b",
        # 短链
        r"(?:https?://)?fb\.watch/[\w-]+",
    ),
))
