"""maimai 图片资源：曲绘下载缓存 + 官方资源包（maimaiDX/Hoshino static 资源）读取。

曲绘缓存在 COVER_CACHE_DIR（data/ 运行时数据，不入库）；rating 框、DX 星贴片、
谱面类型贴图等来自官方资源包（RESOURCE_DIR，.gitignore，由 sync.sync_resource_pack
在启动时自动下载解压）。素材 URI 一律用本地 file:// 绝对路径（html2image 的
Chrome 可直接加载），仅曲绘下载全失败时回退远程 URL；头像（网络来的内存
数据）用 base64 data URI。
"""

import asyncio
import base64
import io
import pathlib

from PIL import Image
from nonebot.log import logger
from xme.xmetools.reqtools import DEFAULT_UA, fetch_data

from .constants import (
    BADGE_DIR,
    BADGE_ICON_URL,
    COVER_CACHE_DIR,
    COVER_DIVINGFISH_URL,
    JACKET_URL,
    RATING_BANDS,
    RESOURCE_CONCURRENCY,
    RESOURCE_DIR,
)


def jacket_lxns_id(wf_song_id: int | str) -> int:
    """把水鱼曲目 id 换算成落雪资产站的曲目 id（标题对齐 1394 曲推导）。

    规律：宴会曲等 100000 段 id 原样；10000~99999 段（DX 时代新曲）减 10000；
    其余原样。落雪无收录时远程 404，由调用方回退处理。
    """
    try:
        wf = int(wf_song_id)
    except (TypeError, ValueError):
        return wf_song_id
    if 10000 <= wf < 100000:
        return wf - 10000
    return wf


def cover_divingfish_url(wf_song_id: int | str) -> str:
    """构造水鱼官方封面 URL（按官方规则补零 5 位，10001~11000 取减 10000 的封面）。"""
    try:
        mid = int(wf_song_id)
    except (TypeError, ValueError):
        mid = 0
    if 10000 < mid <= 11000:
        mid -= 10000
    return COVER_DIVINGFISH_URL.format(f"{mid:05d}")


# 水鱼 fs 缩写 -> 官方图标名（pic 下 UI_MSS_MBase_Icon_{名}.png；fdx/fdxp 官方记作 FSD/FSDp）
_SYNC_ICON_TEXT = {"fs": "FS", "fsp": "FSp", "fdx": "FSD", "fdxp": "FSDp"}


def path_uri(path: pathlib.Path) -> str:
    """本地文件转 file:// URI，文件不存在返回空串。"""
    path = pathlib.Path(path)
    return path.resolve().as_uri() if path.is_file() else ""


def bytes_to_uri(data: bytes, mime: str) -> str:
    """把内存图片字节转为 data URI（仅头像等小体积内存数据使用）。"""
    return f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"


def sniff_image_mime(data: bytes) -> str:
    """按文件头猜测图片 MIME（PNG/JPEG/GIF/WEBP），未知返回 image/png。"""
    if data.startswith(b'\x89PNG'):
        return 'image/png'
    if data.startswith(b'\xff\xd8'):
        return 'image/jpeg'
    if data.startswith((b'GIF87a', b'GIF89a')):
        return 'image/gif'
    if data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        return 'image/webp'
    return 'image/png'


def avatar_uri(data) -> str:
    """把头像转为 data URI（自动识别格式），空数据返回空串。

    data 支持 bytes 或 PIL Image（get_qq_avatar 返回 PIL 对象）。
    """
    if data is None:
        return ""
    if isinstance(data, bytes):
        raw = data
    else:
        buf = io.BytesIO()
        data.convert("RGBA").save(buf, "PNG")
        raw = buf.getvalue()
    return bytes_to_uri(raw, sniff_image_mime(raw))


def static_asset_uri(relpath: str) -> str:
    """读取仓库 static 下的文件转 file:// URI（越界或缺失返回空串）。"""
    base = pathlib.Path("static").resolve()
    path = (base / relpath).resolve()
    if not path.is_relative_to(base) or not path.is_file():
        return ""
    return path.as_uri()


def _resource_pic_path(*parts: str) -> pathlib.Path:
    """得到官方资源包内 pic 下相对路径的本地路径。"""
    return pathlib.Path(RESOURCE_DIR, "pic", *parts)


def pic_uri(name: str) -> str:
    """按相对路径名读取资源包 pic 下的文件转 file:// URI（越界或缺失返回空串）。"""
    base = (pathlib.Path(RESOURCE_DIR) / "pic").resolve()
    path = (base / name).resolve()
    if not path.is_relative_to(base) or not path.is_file():
        return ""
    return path.as_uri()


def pic_names() -> list[str]:
    """列出资源包 pic 下全部可用文件名（相对路径），供皮肤按名取用。"""
    base = pathlib.Path(RESOURCE_DIR) / "pic"
    if not base.exists():
        return []
    return sorted(str(p.relative_to(base)) for p in base.rglob("*") if p.is_file())


class ResourceCache:
    """多源图源的磁盘缓存：本地 file:// URI、并发下载、远程 URL 兜底。

    url_builders 为按优先级排列的 URL 构造函数列表，下载时逐源尝试，
    每个源先 aiohttp、被反爬拦截时再用系统 curl；全失败回退第一源 URL。
    """

    def __init__(self, cache_dir: str, url_builders: list, ext: str) -> None:
        self._dir = pathlib.Path(cache_dir)
        self._builders = list(url_builders)
        self._ext = ext
        self._locks: dict[str, asyncio.Lock] = {}

    def _path(self, key: str):
        """得到资源 key 对应的本地文件路径（不检查存在性）。"""
        return self._dir / f"{key}{self._ext}"

    def local_uri(self, key: str) -> str | None:
        """读取本地缓存并转为 file:// URI，缺失或为空时返回 None。"""
        path = self._path(key).resolve()
        return path.as_uri() if path.is_file() and path.stat().st_size else None

    def remote_url(self, key: str) -> str:
        """得到资源 key 的远程 URL（第一源，回退展示用）。"""
        return self._builders[0](key)

    async def fetch_uri(self, key: str, sem: asyncio.Semaphore | None = None) -> str:
        """得到资源 key 的可用 URI：本地缓存 → 下载补齐 → 远程 URL 兜底。

        同一 key 的并发下载用 per-key 锁去重；sem 限制总并发；下载失败记日志并回退远程 URL。
        """
        local = self.local_uri(key)
        if local:
            return local
        lock = self._locks.setdefault(str(key), asyncio.Lock())
        if sem:
            async with sem:
                async with lock:
                    if not await self._download(key):
                        return self.remote_url(key)
        else:
            async with lock:
                if not await self._download(key):
                    return self.remote_url(key)
        return self.local_uri(key) or self.remote_url(key)

    async def get_uris(self, keys) -> dict:
        """并发（受限）得到多个资源的 URI 映射（自动按 key 去重）。"""
        unique = list(dict.fromkeys(str(k) for k in keys))
        sem = asyncio.Semaphore(RESOURCE_CONCURRENCY)
        pairs = await asyncio.gather(*(self.fetch_uri(k, sem) for k in unique))
        return dict(zip(unique, pairs))

    async def sync_missing(self, keys) -> tuple[int, int]:
        """补齐缺失的本地缓存文件，返回 (成功补齐数, 失败数)；已有缓存的 key 跳过。"""
        missing = [k for k in dict.fromkeys(str(k) for k in keys) if not self._path(k).is_file()]
        if not missing:
            return 0, 0
        sem = asyncio.Semaphore(RESOURCE_CONCURRENCY)
        results = await asyncio.gather(*(self._download(k, sem) for k in missing))
        ok = sum(1 for r in results if r)
        return ok, len(results) - ok

    async def _download(self, key: str, sem: asyncio.Semaphore | None = None) -> bool:
        """下载资源并落盘（不转 URI），返回是否成功；sem 用于限制并发。

        逐源尝试；落雪系资产站对非浏览器 TLS 指纹返回 JS 挑战页，
        aiohttp 被拦时自动改用系统 curl 下载（curl 指纹可通过）。
        """
        if sem:
            async with sem:
                return await self._download(key)
        last_error = ""
        for builder in self._builders:
            url = builder(key)
            for transport in ("aiohttp", "curl"):
                try:
                    data = await self._fetch_bytes(url, transport)
                    if not isinstance(data, (bytes, bytearray)) or not data:
                        raise TypeError(f"响应不是有效字节: {type(data)!r}")
                    if not data.startswith(b'\x89PNG'):
                        raise TypeError("响应不是有效图片")
                    self._dir.mkdir(parents=True, exist_ok=True)
                    self._path(key).write_bytes(data)
                    return True
                except Exception as ex:
                    last_error = f"{ex} ({url})"
        logger.warning(f"下载 maimai 资源 {key} 失败: {last_error}")
        return False

    async def _fetch_bytes(self, url: str, transport: str) -> bytes:
        """按指定传输层下载字节（aiohttp 直连 / 系统 curl 兜底）。"""
        if transport == "curl":
            proc = await asyncio.create_subprocess_exec(
                "curl", "-sL", "--max-time", "30", "-A", DEFAULT_UA, "-o", "-", url,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            data, _ = await proc.communicate()
            return bytes(data)
        return await fetch_data(url, response_type="byte", headers={"User-Agent": DEFAULT_UA})


COVERS = ResourceCache(
    cache_dir=COVER_CACHE_DIR,
    url_builders=[cover_divingfish_url, lambda key: JACKET_URL.format(jacket_lxns_id(key))],
    ext='.png',
)
BADGES = ResourceCache(
    cache_dir=BADGE_DIR,
    url_builders=[lambda key: BADGE_ICON_URL.format(key)],
    ext='.webp',
)


def b50_bg_uri() -> str | None:
    """得到官方 B50 整卡背景（prism_plus 主题）的 file:// URI，缺失返回 None。"""
    return path_uri(_resource_pic_path("prism_plus", "b50.png")) or None


def background_uri() -> str | None:
    """得到入库的官方卡头背景（static/maimai/background.png）的 file:// URI。"""
    return path_uri(pathlib.Path("static/maimai/background.png")) or None


def chart_icon_uri(kind: str) -> str | None:
    """得到谱面类型贴图（"dx"/"sd"）的 file:// URI，缺失返回 None。"""
    return path_uri(_resource_pic_path(f"{kind.upper()}.png")) or None


def rating_frame_uri(rating: int) -> str | None:
    """按 rating 值得到对应段位框（prism_plus UI_CMN_DXRating_XX）的 file:// URI。

    段位映射：999→01 灰、1999→02 蓝、3999→03 绿、6999→04 黄、9999→05 橙、
    11999→06 紫、12999→07 红、13999→08 银、14499→09 金、14999→10 白金、
    其余→11 彩。资源包未同步时返回 None。
    """
    for upper, code in RATING_BANDS:
        if upper is None or rating <= upper:
            return path_uri(_resource_pic_path("prism_plus", f"UI_CMN_DXRating_{code}.png")) or None
    return None


def star_icons() -> dict[int, str]:
    """得到游戏原版 DX 星贴片（1~5 星整图）的 {星数: file:// URI} 映射。"""
    icons = {}
    for count in range(1, 6):
        uri = path_uri(_resource_pic_path(f"status_dxstar_{count}.png"))
        if uri:
            icons[count] = uri
    return icons


def official_ui_assets(rates, combos, syncs, star_counts) -> dict[str, str]:
    """按成绩实际出现的值，批量读取官方 UI 小件的 file:// URI（缺文件为空串）。

    返回的 key：b50_bg / logo / plate / default_icon / name_plate /
    digit_{0-9} / rank_{评级缩写} / combo_{fc缩写} / sync_{fs缩写} / star_{星数}。
    """
    assets = {
        "b50_bg": path_uri(_resource_pic_path("prism_plus", "b50.png")),
        "logo": path_uri(_resource_pic_path("prism_plus", "logo.png")),
        "plate": path_uri(_resource_pic_path("UI_Plate_550101.png")),
        "default_icon": path_uri(_resource_pic_path("UI_Icon_509506.png")),
        "name_plate": path_uri(_resource_pic_path("Name.png")),
    }
    for name in ("b50_score_basic", "b50_score_advanced", "b50_score_expert",
                 "b50_score_master", "b50_score_remaster"):
        assets[f"diff_bg_{name}"] = path_uri(_resource_pic_path(f"{name}.png"))
    for digit in "0123456789":
        assets[f"digit_{digit}"] = path_uri(_resource_pic_path(f"UI_NUM_Drating_{digit}.png"))
    for rate in rates:
        if rate:
            text = rate[:-1].upper() + "p" if rate.endswith("p") else rate.upper()
            assets[f"rank_{rate}"] = path_uri(_resource_pic_path("prism_plus", f"UI_TTR_Rank_{text}.png"))
    for combo in combos:
        if combo:
            assets[f"combo_{combo}"] = path_uri(_resource_pic_path(f"UI_MSS_MBase_Icon_{combo.upper()}.png"))
    for sy in syncs:
        icon = _SYNC_ICON_TEXT.get(sy)
        if sy and icon:
            assets[f"sync_{sy}"] = path_uri(_resource_pic_path(f"UI_MSS_MBase_Icon_{icon}.png"))
    for count in star_counts:
        if count:
            assets[f"star_{count}"] = path_uri(_resource_pic_path(f"UI_GAM_Gauge_DXScoreIcon_0{count}.png"))
    return assets
