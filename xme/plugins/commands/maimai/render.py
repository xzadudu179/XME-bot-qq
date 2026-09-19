"""b50 查分卡数据模型、合成入口与皮肤注册表。

皮肤契约：skins/ 包下每个模块定义 NAME（皮肤名字符串）与
render(data: B50CardData) -> str（返回完整 HTML 文档），本模块导入时
自动发现并注册，皮肤模块无需 import 本模块（类型提示用 TYPE_CHECKING）。
"""

import importlib
import pathlib
import pkgutil

from dataclasses import dataclass, field
from typing import Callable
from typing import Callable

from nonebot.log import logger

from .constants import DEFAULT_SKIN


@dataclass
class B50SongScore:
    """单条 b50 成绩（曲名取自查分器响应，music_list 用于物量联表算星星）。"""

    song_id: int
    title: str
    type: str          # "dx" | "sd"（已小写归一）
    level: str         # 等级，如 "14"
    level_index: int   # 难度序号（0 基本 ~ 4 智）
    level_label: str   # 难度名，如 "Master"
    ds: float          # 定数
    achievements: float
    ra: int
    rate: str          # 评级字母，如 "sssp"
    dx_score: int = 0  # DX 分数（原始值）
    max_dx_score: int = 0  # DX 分数满值（物量×3，0 表示未知）
    stars: int | None = None  # DX 星级 0~5（缺物量数据时为 None，无法计算）
    fc: str = ""
    fs: str = ""

    @property
    def is_dx(self) -> bool:
        """是否为 DX 谱。"""
        return self.type == "dx"


def dx_star_count(dx_score: int, max_dx_score: int) -> int | None:
    """按 DX 分数占比计算星级（0~5），满分为 0 或缺数据时返回 None。

    阈值采用机台规则（maimaiDX 插件同款）：>97% 5★、>95% 4★、>93% 3★、
    >90% 2★、>85% 1★、其余 0★。
    """
    if max_dx_score <= 0:
        return None
    ratio = dx_score / max_dx_score * 100
    if ratio > 97:
        return 5
    if ratio > 95:
        return 4
    if ratio > 93:
        return 3
    if ratio > 90:
        return 2
    if ratio > 85:
        return 1
    return 0


@dataclass
class B50CardData:
    """b50 查分卡渲染所需的全量数据。

    covers/badges 由命令层在渲染前填充：covers 为 曲目id(字符串) -> 曲绘图片
    URI，badges 为 FC/FS 缩写（fc/fcp/ap/app/fs/fsp/fdx/fdxp/sync）-> 徽章图片
    URI（均为本地缓存的 data URI，失败时为远程 URL）。
    rating_frame/avatar_uri/background_uri 同为 data URI，缺资源时为空串。
    """

    username: str
    rating: int
    nickname: str | None
    plate: str | None
    dx: list[B50SongScore]   # 15 条最佳新谱（DX）成绩
    sd: list[B50SongScore]   # 35 条最佳旧谱（SD）成绩
    covers: dict[str, str] = field(default_factory=dict)
    badges: dict[str, str] = field(default_factory=dict)
    rating_frame: str = ""   # 按 rating 段位匹配的姓名框图片
    avatar_uri: str = ""     # 玩家头像（自己/@ 查询时为 QQ 头像）
    background_uri: str = "" # 卡头默认背景图
    star_icons: dict[int, str] = field(default_factory=dict)  # 星数(1~5) -> 游戏原版 N 星贴片 URI
    chart_icons: dict[str, str] = field(default_factory=dict)  # "dx"/"sd" -> 谱面类型贴图 URI
    ui: dict[str, str] = field(default_factory=dict)  # 官方 UI 小件袋（b50_bg/logo/plate/digit/rank/combo/sync/star）
    pic: Callable[[str], str] = field(default_factory=lambda: _pic_stub)  # 按名取 pic 资源（resource/pic 相对路径）


def _pic_stub(name: str) -> str:
    """data.pic 未注入时的默认取图函数（返回空串，皮肤需容忍空值）。"""
    return ""


def build_b50_card_data(raw: dict, music_list: list[dict] | None = None) -> B50CardData:
    """把水鱼 b50 原始响应合成为渲染数据（纯函数）。

    Args:
        raw (dict): query/player 的原始响应（成绩自带 title/dxScore）
        music_list (list[dict] | None): 水鱼曲目表，用于联表物量计算 DX 星级

    Returns:
        B50CardData: 可直接交给皮肤渲染的数据
    """
    title_map = {str(m.get("id")): m.get("title", "") for m in (music_list or [])}
    # (曲目id, 难度序号) -> 总物量；满 DX 分 = 总物量 × 3
    notes_map: dict[tuple[str, int], int] = {}
    for m in (music_list or []):
        sid = str(m.get("id"))
        for idx, chart in enumerate(m.get("charts", []) or []):
            notes = chart.get("notes") if isinstance(chart, dict) else None
            if isinstance(notes, list) and notes:
                notes_map[(sid, idx)] = sum(n for n in notes if isinstance(n, (int, float)))

    def to_score(chart: dict) -> B50SongScore:
        song_id = int(chart.get("song_id", chart.get("id", 0)))
        title = chart.get("title") or title_map.get(str(song_id)) or f"Unknown-{song_id}"
        level_index = int(chart.get("level_index", 0))
        dx_score = int(chart.get("dxScore") or 0)
        max_notes = notes_map.get((str(song_id), level_index))
        max_dx = max_notes * 3 if max_notes else 0
        stars = dx_star_count(dx_score, max_dx) if max_dx else None
        return B50SongScore(
            song_id=song_id,
            title=str(title),
            type=str(chart.get("type", "sd")).lower(),
            level=str(chart.get("level", "")),
            level_index=level_index,
            level_label=str(chart.get("level_label", "")),
            ds=float(chart.get("ds", 0.0)),
            achievements=float(chart.get("achievements", 0.0)),
            ra=int(chart.get("ra", 0)),
            rate=str(chart.get("rate", "")),
            dx_score=dx_score,
            stars=stars,
            max_dx_score=max_dx,
            fc=str(chart.get("fc") or ""),
            fs=str(chart.get("fs") or ""),
        )

    charts = raw.get("charts", {})
    nickname = raw.get("nickname")
    plate = raw.get("plate")
    return B50CardData(
        username=str(raw.get("username", "未知")),
        rating=int(raw.get("rating", 0)),
        nickname=str(nickname) if nickname else None,
        plate=str(plate) if plate else None,
        dx=[to_score(c) for c in charts.get("dx", [])],
        sd=[to_score(c) for c in charts.get("sd", [])],
    )


def b50_text_summary(data: B50CardData) -> str:
    """把 b50 数据转成纯文本摘要（渲染查分卡失败时的降级展示）。"""
    lines = [f"DX ({len(data.dx)})"]
    lines += [
        f"{s.title} [{s.level_label} {s.ds:.1f}] {s.achievements:.4f}% ra{s.ra}"
        for s in data.dx
    ]
    lines.append(f"SD ({len(data.sd)})")
    lines += [
        f"{s.title} [{s.level_label} {s.ds:.1f}] {s.achievements:.4f}% ra{s.ra}"
        for s in data.sd
    ]
    return "\n".join(lines)


class SkinRegistry:
    """查分卡皮肤注册表：导入时填充一次，运行期只读。"""

    def __init__(self) -> None:
        self._skins: dict[str, Callable[[B50CardData], str]] = {}

    def register(self, name: str, render: Callable[[B50CardData], str]) -> None:
        """注册皮肤，重名时覆盖并告警。"""
        if name in self._skins:
            logger.warning(f"查分卡皮肤 {name} 重复注册，已覆盖")
        self._skins[name] = render

    def get(self, name: str) -> Callable[[B50CardData], str] | None:
        """按名字得到皮肤渲染函数，不存在返回 None。"""
        return self._skins.get(name)

    def names(self) -> list[str]:
        """得到全部已注册皮肤名（排序后）。"""
        return sorted(self._skins)


SKINS = SkinRegistry()


def register_skin(name: str, render: Callable[[B50CardData], str]) -> None:
    """向全局皮肤注册表注册一张查分卡皮肤。"""
    SKINS.register(name, render)


def render_b50_html(data: B50CardData, skin: str | None = None) -> str:
    """用指定皮肤渲染 b50 查分卡 HTML。

    Args:
        data (B50CardData): 查分卡数据
        skin (str | None): 皮肤名，None 时使用 DEFAULT_SKIN

    Raises:
        KeyError: 皮肤不存在
    """
    name = skin or DEFAULT_SKIN
    render = SKINS.get(name)
    if render is None:
        raise KeyError(name)
    return render(data)


def _load_skin_modules() -> None:
    """自动发现 skins/ 包下的皮肤模块并注册，单个皮肤加载失败仅告警跳过。"""
    package_dir = pathlib.Path(__file__).parent / "skins"
    for module_info in pkgutil.iter_modules([str(package_dir)]):
        if module_info.name.startswith("_"):
            continue
        try:
            module = importlib.import_module(f".skins.{module_info.name}", __package__)
        except Exception as ex:
            logger.warning(f"加载查分卡皮肤 {module_info.name} 失败: {ex}")
            continue
        name = getattr(module, "NAME", None)
        render = getattr(module, "render", None)
        if isinstance(name, str) and callable(render):
            register_skin(name, render)
        else:
            logger.warning(f"皮肤模块 {module_info.name} 缺少 NAME/render 定义，已跳过")


_load_skin_modules()
