"""视频工具包：基于 yt-dlp 的各平台视频链接「提取 → 解析 → 下载」。

内部结构：
- platforms.py  平台注册器（VideoPlatform 统一描述各平台全部可解析链接形式）
- core.py       核心流程（文本提取 / 元信息解析 / 下载 / 组合入口）

外部统一从包入口导入（如 from xme.xmetools.videotools import extract_and_download）。

常用入口速查：
- extract_video_links(text)         提取文本中所有视频链接（纯文本，不联网）
- replace_video_links(text, repl)    把文本中视频链接替换为 repl（默认移除）
- parse_video(url)                  异步解析链接元信息（不下载）
- download_video(url, output_dir)   异步下载单个视频
- extract_and_download(text, dir)   组合：提取 + 并发下载 + 无链接文本
"""
from .core import (
    VideoDownload,
    VideoExtractResult,
    VideoInfo,
    VideoLink,
    build_ydl_opts,
    download_video,
    extract_and_download,
    extract_video_links,
    find_urls,
    is_video_url,
    parse_video,
    replace_video_links,
)
from .platforms import (
    VideoPlatform,
    all_platforms,
    get_platform,
    match_platform,
    register_platform,
)

__all__ = [
    "VideoDownload",
    "VideoExtractResult",
    "VideoInfo",
    "VideoLink",
    "VideoPlatform",
    "all_platforms",
    "build_ydl_opts",
    "download_video",
    "extract_and_download",
    "extract_video_links",
    "find_urls",
    "get_platform",
    "is_video_url",
    "match_platform",
    "parse_video",
    "register_platform",
    "replace_video_links",
]
