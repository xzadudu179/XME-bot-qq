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

下载限制（大小/时长/清晰度）：DEFAULT_MAX_FILESIZE_MB / DEFAULT_MAX_DURATION_SECS /
DEFAULT_MAX_HEIGHT 常量全局默认，download_video / extract_and_download 的同名参数可按次覆盖。
"""
import asyncio
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path

import yt_dlp
from yt_dlp.utils import match_filter_func
from nonebot.log import logger

from .platforms import VideoPlatform, match_platform

# ---- 下载限制（可调：直接改这里的默认值，或调用方用同名参数按次覆盖）----
DEFAULT_MAX_FILESIZE_MB = 200    # 单次下载产物总大小上限（MB），超出即删除并报错
DEFAULT_MAX_DURATION_SECS = 600  # 视频时长上限（秒），超时长的链接在下载前被过滤（直播等无时长的放行）
DEFAULT_MAX_HEIGHT = 720         # 默认最高清晰度（画面高度像素），如需 480p 改为 480

# URL 正文排除：空白、HTML/markdown 包裹符、CJK 字符及其中文标点
# （中文语境里链接后常紧跟 ，。等标点且无空格）
_URL_RE = re.compile(r"https?://[^\s<>\"'\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]+")
# URL 末尾粘连的收尾标点（如 "链接。" / "markdown 链接)"），逐个剔除
_TRAILING_PUNCT = ".,!?;:)]}>'\"`" + "，。！？；：、）】》」』＞”’…"


@dataclass(frozen=True)
class VideoLink:
    """文本中提取到的一条视频链接（extract_video_links 的返回项）。"""

    # 原文中的链接字符串：仅剔除尾部粘连标点（中文标点/引号等），其余未改写，
    # 可与 VideoDownload.url、VideoInfo.url 直接字符串比对
    url: str
    # 链接所属平台定义（match_platform 的结果）；提取时已按注册表过滤，不会为 None
    platform: VideoPlatform | None
    # 链接在原文本中的起止下标（[start, end)，满足 text[start:end] == url），
    # 用于对原文做原位替换/删除
    start: int
    end: int


@dataclass
class VideoInfo:
    """yt-dlp 解析出的单条视频元信息（parse_video 的返回项，不下载）。

    字段取自 yt-dlp 的 info dict；合集/多 P/播放列表解析出的子视频在
    entries 里，元素也是 VideoInfo、字段含义相同（顶层是合集入口的信息）。
    默认 noplaylist=True：形如 bilibili ?p=N 的「视频+合集」两可链接只解析
    指向的那一 P；独立的合集/播放列表链接才会展开出 entries（extra_opts 可覆盖）。
    """

    # 请求解析时传入的原始链接（yt-dlp original_url，兜底 webpage_url），
    # 与 VideoLink.url、VideoDownload.url 一致，可作匹配 key。
    # 注意：entries 子条目的该字段可能继承合集入口链接，子视频自身地址优先看 webpage_url
    url: str
    # 平台标识（platforms 注册表 name，如 "bilibili"）
    platform_name: str
    # yt-dlp 的 extractor 标识（如 "BiliBili"）；为 "Generic" 说明 yt-dlp 没有
    # 专用解析器、只是通用网页解析（多半拿不到可下载的视频）
    extractor: str
    # 平台侧视频 id（如 BV 号 / av 号）
    video_id: str
    # 标题；合集链接时是合集标题，子视频标题看 entries[i].title
    title: str
    # 时长（秒）；直播中或拿不到时为 None
    duration: float | None
    # UP 主 / 频道名（yt-dlp uploader，兜底 channel）
    uploader: str
    # 简介全文，可能很长，展示前建议自行截断
    description: str
    # 封面图链接；拿不到时为空串
    thumbnail: str
    # yt-dlp 解析重定向后的规范化页面地址（如 b23.tv 短链 → 完整 BV 页）。
    # 与 url 的区别：url 是「请求时的原始链接」，本字段适合展示或二次解析
    webpage_url: str
    # 是否正在直播
    is_live: bool
    # 合集/多 P 的子视频列表，按合集内顺序；普通单视频为空列表
    entries: list["VideoInfo"] = field(default_factory=list)


@dataclass
class VideoDownload:
    """单条链接的一次下载结果（download_video 的返回项）。

    不抛异常：成功 ok=True；失败/超时 ok=False，error 说明原因。
    下载行为与 VideoInfo 的解析一致（默认 noplaylist=True，extra_opts 可覆盖）。
    """

    # 原样传入的下载链接（未经改写）；extract_and_download 中与 links[i].url 相同
    url: str
    # 平台标识（platforms 注册表 name）；链接不属于任何已注册平台时为 ""
    platform_name: str
    # 视频标题；未进入解析（平台不识别）或解析失败/超时时为 ""
    title: str
    # 下载并后处理（合并音视频等）完成后的成品文件路径，文件名形如
    # "标题 [视频id].扩展名"；单视频 1 个，合集/多 P 每个子视频 1 个（按下载顺序）；
    # 不含 .part 临时文件和字幕/封面等附属文件。
    # ok=False 时必为空列表：超时/异常拿不到线程内的落盘状态，
    # 已写了一半的文件需调用方扫描 output_dir 找回
    file_paths: list[Path]
    # 是否下载成功
    ok: bool
    # 失败原因：ok=False 时为 "不支持的视频链接" / "下载超时(Ns)" / yt-dlp 报错信息；成功为 None
    error: str | None = None


@dataclass
class VideoExtractResult:
    """extract_and_download 的组合结果：提取 + 并发下载 + 无链接文本。"""

    # 从文本提取到的全部视频链接（按出现顺序，已去重）
    links: list[VideoLink]
    # 下载结果，与 links 一一对应且同序（downloads[i] 对应 links[i]）
    downloads: list[VideoDownload]
    # 移除全部视频链接（含重复出现）后的剩余文本；文本里没有视频链接时与原文相同
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
    max_filesize_mb: float | None = None,
    max_duration_secs: float | None = None,
    max_height: int | None = None,
) -> dict:
    """拼接一份 yt-dlp 参数：公共默认 < 平台专属 < extra（调用方覆盖，优先级最高）。

    下载限制（大小/时长/清晰度）缺省取 DEFAULT_MAX_* 常量，可用同名参数按次覆盖；
    extra 里传 format/match_filter/max_filesize 仍可整体压过这里的限制设置。
    """
    max_filesize_mb = DEFAULT_MAX_FILESIZE_MB if max_filesize_mb is None else max_filesize_mb
    max_duration_secs = DEFAULT_MAX_DURATION_SECS if max_duration_secs is None else max_duration_secs
    max_height = DEFAULT_MAX_HEIGHT if max_height is None else max_height
    opts = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "socket_timeout": 20,
        "retries": 3,
        # 清晰度上限：优先 ≤上限的最优视频+音频，退化到 ≤上限的单文件，再退化到最优单文件
        "format": f"bv*[height<={max_height}]+ba/b[height<={max_height}]/b",
        # 大小上限（按字节）：yt-dlp 在下载前按服务器提供的估计大小跳过超限格式
        "max_filesize": int(max_filesize_mb * 1024 * 1024),
        # 时长上限：超时长的条目在下载前被过滤；"?=" 表示无时长字段（如直播）时放行
        "match_filter": match_filter_func(f"duration<=?{int(max_duration_secs)}"),
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


def _enforce_size_limit(file_paths: list[Path], max_filesize_mb: float) -> str | None:
    """下载后的硬校验：产物总大小超过上限时全部删除并返回错误文案；合规返回 None。

    yt-dlp 的 max_filesize 依赖服务器提供的文件大小，部分格式拿不到估计值会漏网，
    所以落盘后再按实际大小兜底（上限作用于本次下载的全部产物之和）。
    """
    total = 0
    for p in file_paths:
        try:
            total += p.stat().st_size
        except OSError:
            return None  # 文件已不在（异常状态），宁可不校验也不误删
    if total <= max_filesize_mb * 1024 * 1024:
        return None
    for p in file_paths:
        p.unlink(missing_ok=True)
    return f"视频超出 {max_filesize_mb:g}MiB 大小限制（实际 {total / 1048576:.1f}MiB），已删除下载内容"


def _empty_download_reason(info: dict | None, max_filesize_mb: float, max_duration_secs: float) -> str:
    """下载完成但没有产物时，根据 info 推断被限制过滤的原因，给出可读文案。

    yt-dlp 被 match_filter/max_filesize 过滤时不报错、只返回零产物（info dict
    仍带 duration/filesize 估计），据此区分"时长超限/大小超限/未知"。
    """
    if not isinstance(info, dict):
        return "下载完成但未找到落盘文件"
    duration = info.get("duration")
    if duration and duration > max_duration_secs:
        mins, secs = int(duration) // 60, int(duration) % 60
        return (f"视频时长 {mins}分{secs:02d}秒 超出 "
                f"{int(max_duration_secs) // 60} 分钟限制，已跳过下载")
    size = info.get("filesize") or info.get("filesize_approx")
    if size and size > max_filesize_mb * 1024 * 1024:
        return (f"视频大小约 {size / 1048576:.1f}MiB 超出 "
                f"{max_filesize_mb:g}MiB 限制，已跳过下载")
    return "下载完成但未找到落盘文件（可能被下载限制过滤）"


async def download_video(
    url: str,
    output_dir: str | Path,
    *,
    platforms: Iterable[str] | None = None,
    cookies: str | Path | None = None,
    extra_opts: dict | None = None,
    progress_hook: Callable[[dict], None] | None = None,
    timeout: float = 900,
    max_filesize_mb: float | None = None,
    max_duration_secs: float | None = None,
    max_height: int | None = None,
) -> VideoDownload:
    """异步下载单个视频（或合集）到指定文件夹，目录不存在会自动创建。

    不抛异常：失败/超时返回 ok=False 且 error 说明原因。
    超时只是放弃等待，底层线程可能仍在下载，已落盘的部分文件可通过扫描
    output_dir 找回。文件名由 yt-dlp 按「标题 [视频id].扩展名」生成。
    下载限制：大小/时长/清晰度缺省用 DEFAULT_MAX_* 常量，同名参数可按次覆盖；
    超出大小上限的产物会被删除并返回 ok=False。
    """
    platform = match_platform(url, names=platforms)
    if platform is None:
        return VideoDownload(url=url, platform_name="", title="", file_paths=[],
                             ok=False, error="不支持的视频链接")
    max_mb = DEFAULT_MAX_FILESIZE_MB if max_filesize_mb is None else max_filesize_mb
    opts = build_ydl_opts(output_dir=output_dir, platform=platform, cookies=cookies,
                          progress_hook=progress_hook, extra=extra_opts,
                          max_filesize_mb=max_mb, max_duration_secs=max_duration_secs,
                          max_height=max_height)
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
        reason = _empty_download_reason(info, max_mb,
                                        DEFAULT_MAX_DURATION_SECS if max_duration_secs is None else max_duration_secs)
        logger.info(f"下载无产物 {url}: {reason}")
        return VideoDownload(url=url, platform_name=platform.name, title="",
                             file_paths=[], ok=False, error=reason)
    oversize_error = _enforce_size_limit(files, max_mb)
    if oversize_error:
        logger.warning(f"下载产物超限已删除 {url}: {oversize_error}")
        return VideoDownload(url=url, platform_name=platform.name, title="",
                             file_paths=[], ok=False, error=oversize_error)
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
    max_filesize_mb: float | None = None,
    max_duration_secs: float | None = None,
    max_height: int | None = None,
) -> VideoExtractResult:
    """组合入口：提取文本中全部视频链接 → 并发下载到 output_dir → 返回组合结果。

    downloads 与 links 一一对应（同序）；cleaned_text 是移除全部视频链接
    （含重复出现的）后的文本。文本里没有可解析链接时，downloads 为空、
    cleaned_text 与原文相同。下载限制参数原样透传 download_video。
    """
    links = extract_video_links(text, platforms=platforms)
    semaphore = asyncio.Semaphore(max(1, concurrency))

    async def download_one(link: VideoLink) -> VideoDownload:
        async with semaphore:
            return await download_video(
                link.url, output_dir,
                platforms=platforms, cookies=cookies, extra_opts=extra_opts,
                progress_hook=progress_hook, timeout=download_timeout,
                max_filesize_mb=max_filesize_mb, max_duration_secs=max_duration_secs,
                max_height=max_height,
            )

    downloads = list(await asyncio.gather(*(download_one(l) for l in links)))
    cleaned_text = replace_video_links(text, platforms=platforms)
    return VideoExtractResult(links=links, downloads=downloads, cleaned_text=cleaned_text)
