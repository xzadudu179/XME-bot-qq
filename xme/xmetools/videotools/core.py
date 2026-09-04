"""视频工具核心流程：基于 yt-dlp 的「文本提取 → 平台匹配 → 解析/下载」。

与 platforms.py（平台注册器）配合：
    文本 --extract_video_links--> VideoLink 列表 --yt-dlp--> 解析/下载

公共入口（除前两个纯文本函数外均为异步函数，经包 __init__ 统一导出）：
- extract_video_links(text)          提取文本中所有可解析的视频链接（纯文本匹配，不联网）
- replace_video_links(text, repl)    把文本中视频链接替换为 repl（默认移除）
- is_video_url(url)                  判断单个链接是否可解析
- parse_video(url)                   异步解析单个链接的元信息（不下载）
- download_video(url, output_dir)    异步下载单个视频到指定文件夹
- extract_and_download(text, dir)    组合入口：提取 + 并发下载 + 返回无链接文本

典型场景（机器人收到一条消息）：
    result = await extract_and_download(text, "./data/videos")
    for d in result.downloads: ...          # 逐条下载结果（含文件路径）
    reply(result.cleaned_text)              # 回复去掉链接后的剩余文本
"""
import asyncio
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path

import yt_dlp
from nonebot.log import logger

from .platforms import VideoPlatform, match_platform

# URL 正文排除：空白、HTML/markdown 包裹符、CJK 字符及其中文标点
# （中文语境里链接后常紧跟 ，。等标点且无空格）
_URL_RE = re.compile(r"https?://[^\s<>\"'\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]+")
# URL 末尾粘连的收尾标点（如 "链接。" / "markdown 链接)"），逐个剔除
_TRAILING_PUNCT = ".,!?;:)]}>'\"`" + "，。！？；：、）】》」』＞”’…"


@dataclass(frozen=True)
class VideoLink:
    """文本中提取到的一条视频链接；start/end 是它在原文本中的下标区间 [start, end)。"""

    url: str
    platform: VideoPlatform | None
    start: int
    end: int


@dataclass
class VideoInfo:
    """yt-dlp 解析出的视频元信息；合集/多 P 链接的子视频在 entries 里。"""

    url: str
    platform_name: str
    extractor: str
    video_id: str
    title: str
    duration: float | None
    uploader: str
    description: str
    thumbnail: str
    webpage_url: str
    is_live: bool
    entries: list["VideoInfo"] = field(default_factory=list)


@dataclass
class VideoDownload:
    """一次下载的结果；ok=True 时 file_paths 是后处理完成后的成品文件
    （合集链接含每个子视频），ok=False 时 file_paths 必为空列表、error 说明原因
    （失败前可能已落盘部分文件，需调用方扫描 output_dir 找回）。"""

    url: str
    platform_name: str
    title: str
    file_paths: list[Path]
    ok: bool
    error: str | None = None


@dataclass
class VideoExtractResult:
    """extract_and_download 的组合结果。"""

    links: list[VideoLink]
    downloads: list[VideoDownload]
    cleaned_text: str


def find_urls(text: str) -> list[tuple[str, int, int]]:
    """提取文本中所有 URL，返回 (url, 起点, 终点) 列表，已剔除尾部粘连标点。"""
    result = []
    for m in _URL_RE.finditer(text):
        url = m.group().rstrip(_TRAILING_PUNCT)
        if "." not in url:
            continue
        result.append((url, m.start(), m.start() + len(url)))
    return result


def extract_video_links(
    text: str,
    *,
    platforms: Iterable[str] | None = None,
    dedupe: bool = True,
) -> list[VideoLink]:
    """提取文本中所有可解析为视频的链接（纯文本匹配，不联网）。

    text: 任意可能包含视频链接的文本
    platforms: 限定平台标识列表；None 表示全部已注册平台
    dedupe: 相同链接只保留第一次出现

    返回按出现顺序排列的 VideoLink 列表。
    """
    links: list[VideoLink] = []
    seen: set[str] = set()
    for url, start, end in find_urls(text):
        platform = match_platform(url, names=platforms)
        if platform is None:
            continue
        if dedupe and url in seen:
            continue
        seen.add(url)
        links.append(VideoLink(url=url, platform=platform, start=start, end=end))
    return links


def replace_video_links(
    text: str,
    repl: str = "",
    *,
    platforms: Iterable[str] | None = None,
) -> str:
    """把文本中全部视频链接替换为 repl（默认空串即移除）；无视频链接时原样返回。

    repl 为空串（移除）时做最小清理：行内多余空格、行尾空白、3 连以上换行
    收敛为一个空行；repl 非空（占位替换）时按原位拼接、不做额外清理，
    保留原文其余格式。重复出现的链接也会被全部替换。
    """
    spans = [
        (start, end)
        for url, start, end in find_urls(text)
        if match_platform(url, names=platforms) is not None
    ]
    if not spans:
        return text
    for start, end in sorted(spans, reverse=True):
        text = text[:start] + repl + text[end:]
    if repl == "":
        text = re.sub(r"[ \t]{2,}", " ", text)
        text = re.sub(r"[ \t]+\n", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def is_video_url(url: str, *, platforms: Iterable[str] | None = None) -> bool:
    """判断单个链接是否属于已注册平台的可解析形式。"""
    return match_platform(url, names=platforms) is not None


def build_ydl_opts(
    *,
    output_dir: str | Path | None = None,
    platform: VideoPlatform | None = None,
    cookies: str | Path | None = None,
    progress_hook: Callable[[dict], None] | None = None,
    extra: dict | None = None,
) -> dict:
    """拼接一份 yt-dlp 参数：公共默认 < 平台专属 < extra（调用方覆盖，优先级最高）。"""
    opts = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "socket_timeout": 20,
        "retries": 3,
    }
    if platform is not None:
        opts.update(platform.ydl_opts)
    if output_dir is not None:
        opts["outtmpl"] = str(Path(output_dir) / "%(title).80s [%(id)s].%(ext)s")
    if cookies:
        opts["cookiefile"] = str(cookies)
    if progress_hook is not None:
        opts["progress_hooks"] = [progress_hook]
    if extra:
        opts.update(extra)
    return opts


def _to_video_info(info: dict, platform_name: str) -> VideoInfo:
    """把 yt-dlp 的 info dict 转成 VideoInfo；合集 entries 递归展开。"""
    return VideoInfo(
        url=info.get("original_url") or info.get("webpage_url", ""),
        platform_name=platform_name,
        extractor=info.get("extractor_key") or "",
        video_id=str(info.get("id") or ""),
        title=info.get("title") or "",
        duration=info.get("duration"),
        uploader=info.get("uploader") or info.get("channel") or "",
        description=info.get("description") or "",
        thumbnail=info.get("thumbnail") or "",
        webpage_url=info.get("webpage_url") or "",
        is_live=bool(info.get("is_live")),
        entries=[
            _to_video_info(e, platform_name)
            for e in (info.get("entries") or [])
            if isinstance(e, dict)
        ],
    )


def _extract_info_sync(url: str, opts: dict) -> dict | None:
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=False)


def _download_sync(url: str, opts: dict, output_dir: Path) -> tuple[dict | None, list[Path]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
    return info, _collect_files(info)


def _collect_files(info: dict | None) -> list[Path]:
    """从下载后的 info 里收集全部落盘文件路径（含合集内每一条，递归）。"""
    if not isinstance(info, dict):
        return []
    files = [
        Path(d["filepath"])
        for d in (info.get("requested_downloads") or [])
        if d.get("filepath")
    ]
    for entry in info.get("entries") or []:
        files.extend(_collect_files(entry))
    return files


async def parse_video(
    url: str,
    *,
    platforms: Iterable[str] | None = None,
    cookies: str | Path | None = None,
    extra_opts: dict | None = None,
    timeout: float = 90,
) -> VideoInfo | None:
    """异步解析单个链接的元信息（标题/时长/合集条目等），不下载视频。

    失败或超时返回 None（不抛异常）。注意：超时只是放弃等待，底层线程仍会
    自行结束，不会阻塞事件循环。
    """
    platform = match_platform(url, names=platforms)
    if platform is None:
        logger.warning(f"parse_video: 未注册的平台链接 {url}")
        return None
    opts = build_ydl_opts(cookies=cookies, platform=platform, extra=extra_opts)
    try:
        info = await asyncio.wait_for(
            asyncio.to_thread(_extract_info_sync, url, opts), timeout
        )
    except asyncio.TimeoutError:
        logger.warning(f"解析超时({timeout}s): {url}")
        return None
    except Exception as e:
        logger.warning(f"解析失败 {url}: {e}")
        return None
    if not info:
        return None
    return _to_video_info(info, platform.name)


async def download_video(
    url: str,
    output_dir: str | Path,
    *,
    platforms: Iterable[str] | None = None,
    cookies: str | Path | None = None,
    extra_opts: dict | None = None,
    progress_hook: Callable[[dict], None] | None = None,
    timeout: float = 900,
) -> VideoDownload:
    """异步下载单个视频（或合集）到指定文件夹，目录不存在会自动创建。

    不抛异常：失败/超时返回 ok=False 且 error 说明原因。
    超时只是放弃等待，底层线程可能仍在下载，已落盘的部分文件可通过扫描
    output_dir 找回。文件名由 yt-dlp 按「标题 [视频id].扩展名」生成。
    """
    platform = match_platform(url, names=platforms)
    if platform is None:
        return VideoDownload(url=url, platform_name="", title="", file_paths=[],
                             ok=False, error="不支持的视频链接")
    opts = build_ydl_opts(output_dir=output_dir, platform=platform, cookies=cookies,
                          progress_hook=progress_hook, extra=extra_opts)
    try:
        info, files = await asyncio.wait_for(
            asyncio.to_thread(_download_sync, url, opts, Path(output_dir)), timeout
        )
    except asyncio.TimeoutError:
        logger.warning(f"下载超时({timeout}s): {url}")
        return VideoDownload(url=url, platform_name=platform.name, title="",
                             file_paths=[], ok=False, error=f"下载超时({timeout}s)")
    except Exception as e:
        logger.warning(f"下载失败 {url}: {e}")
        return VideoDownload(url=url, platform_name=platform.name, title="",
                             file_paths=[], ok=False, error=str(e))
    if not files:
        return VideoDownload(url=url, platform_name=platform.name, title="",
                             file_paths=[], ok=False, error="下载完成但未找到落盘文件")
    return VideoDownload(url=url, platform_name=platform.name,
                         title=(info or {}).get("title") or "",
                         file_paths=files, ok=True)


async def extract_and_download(
    text: str,
    output_dir: str | Path,
    *,
    platforms: Iterable[str] | None = None,
    concurrency: int = 2,
    cookies: str | Path | None = None,
    extra_opts: dict | None = None,
    progress_hook: Callable[[dict], None] | None = None,
    download_timeout: float = 900,
) -> VideoExtractResult:
    """组合入口：提取文本中全部视频链接 → 并发下载到 output_dir → 返回组合结果。

    downloads 与 links 一一对应（同序）；cleaned_text 是移除全部视频链接
    （含重复出现的）后的文本。文本里没有可解析链接时，downloads 为空、
    cleaned_text 与原文相同。
    """
    links = extract_video_links(text, platforms=platforms)
    semaphore = asyncio.Semaphore(max(1, concurrency))

    async def download_one(link: VideoLink) -> VideoDownload:
        async with semaphore:
            return await download_video(
                link.url, output_dir,
                platforms=platforms, cookies=cookies, extra_opts=extra_opts,
                progress_hook=progress_hook, timeout=download_timeout,
            )

    downloads = list(await asyncio.gather(*(download_one(l) for l in links)))
    cleaned_text = replace_video_links(text, platforms=platforms)
    return VideoExtractResult(links=links, downloads=downloads, cleaned_text=cleaned_text)
