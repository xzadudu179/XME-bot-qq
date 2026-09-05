"""视频文件探测：针对直链媒体文件 URL 的元数据读取（当前只提供时长）。

与 core.py 的平台链接解析互补，按 URL 类型选入口：
- 平台页面链接（B 站/YouTube 等） → core.parse_video（yt-dlp）；
- 直链媒体文件（xxx.mp4/.mkv/.webm 等） → 本模块 get_video_duration（ffprobe）。

实现基于系统 ffprobe 对远程地址的流式探测：HTTP Range 按需读取容器元数据，
不下载整个文件；因此服务端需支持 Range 请求，且 mp4 的 moov 在文件尾部
且服务端不支持 Range 时会探测失败（优雅返回 None）。
"""
import asyncio


def _parse_duration(raw: str) -> float | None:
    """把 ffprobe 的输出解析为正时长；空/N-A/非法值返回 None。"""
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        duration = float(raw)
    except ValueError:
        return None
    return duration if duration > 0 else None


async def get_video_duration(path_or_url: str, *, timeout: float = 30) -> float | None:
    """探测视频文件/URL 的时长（秒）；无法解析（非媒体/不可达/超时）返回 None，不抛异常。

    path_or_url: 直链媒体文件地址，也可传本地文件路径；平台页面链接请用 parse_video。
    timeout: ffprobe 进程的等待上限（秒），超时进程会被终止。
    """
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(path_or_url),
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
    except FileNotFoundError:  # 环境未安装 ffprobe
        return None
    try:
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout)
    except asyncio.TimeoutError:
        proc.kill()
        return None
    return _parse_duration(stdout.decode("utf-8", "ignore"))
