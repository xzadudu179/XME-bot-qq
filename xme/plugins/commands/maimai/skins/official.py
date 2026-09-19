"""舞萌 B50 查分卡 official 皮肤：使用者提供的 HTML 设计为准（v2，逐类逐值）。

结构与样式完全按使用者改定的 b50_sample.html 定义（含每个类的值），
仅把其中相对路径的图片替换为动态资源：rating 框/数字、Name.png、
progress_small.png、行底图、曲绘、类型/评级/FC/FS/DX星条贴图。
Re:Master 谱面需加 remaster 类来修改颜色。
"""
import base64
import html
import pathlib

from xme.plugins.commands.maimai.render import B50CardData

from ..constants import MAIMAI_FONT_SUBSET_PATH

NAME = 'official'

DIFF_BG = ["b50_score_basic", "b50_score_advanced", "b50_score_expert", "b50_score_master", "b50_score_remaster"]

# 水鱼缩写 -> 官方图标名（pic 下 UI_MSS_MBase_Icon_{名}.png）
COMBO_ICON = {"fc": "FC", "fcp": "FCp", "ap": "AP", "app": "APp"}
SYNC_ICON = {"fs": "FS", "fsp": "FSp", "fdx": "FSD", "fdxp": "FSDp"}


def _load_font_data() -> bytes:
    """读取 maimai 风格字体子集（数字/拉丁）。"""
    try:
        return pathlib.Path(MAIMAI_FONT_SUBSET_PATH).read_bytes()
    except OSError:
        return b""


def _truncate_title(title: str, limit: int = 18) -> str:
    """按显示宽度截断曲名（全角算 2、半角算 1，约 18 个全角位）。"""
    width = 0
    out = []
    for ch in title:
        width += 2 if ord(ch) > 0x2E80 else 1
        if width > limit * 2:
            return "".join(out) + "..."
        out.append(ch)
    return "".join(out)


def _rank_text(rate: str) -> str:
    """把评级缩写转为官方评级图名（sssp -> SSSp）。"""
    if not rate:
        return ""
    return rate[:-1].upper() + "p" if rate.endswith("p") else rate.upper()


_STYLE = """
@font-face { font-family: 'MaiSGM'; src: url('__SGM_FONT__') format('truetype'); }

* { margin: 0; padding: 0; box-sizing: border-box; }
body { background: transparent; }
img {
    display: inline-block;
}
.stage {
    width: 1600px;
    font-family: "MaiSGM", "Source Han Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif;
    /* 背景保留自定义接口，默认用这个背景 */
    background-image: url('__B50_BG__');
    /* background-image: url('static/xme-bot/background-dark.webp'); */
    background-size: cover;
    background-position: center;
    border-radius: 24px;
    overflow: hidden;
}
.stagecover {
    padding: 24px;
    background: linear-gradient(to bottom, #0000 80%, #0005 100%);
}
/* 排版全在这里调：列数改 repeat(5, 1fr)，卡片间距改 gap */
.grid {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 12px;
    margin-bottom: 24px;
}
/* 关键：1fr 轨道默认会被内容最小宽度撑破画布，必须允许收缩 */
.grid > .cell { min-width: 0; }
.section-title {
    color: #ffffff;
    text-align: center;
    /* -webkit-text-stroke: 1px black; */
    font-size: 24px;
    font-weight: bold;
    margin: 6px 0 10px;
    text-shadow: 0 0 3px rgba(25, 20, 71, 0.699);
}
/* 成绩卡：三行流式布局（题头 / 达成率 / 明细），高度随内容自适应 */
.cell {
    min-width: 0;
    display: flex;
    /* flex-direction: column; */
    position: relative;
    justify-content: start;
    gap: 10px;
    padding: 12px;
    padding-top: 6px;
    border-radius: 12px;
    background-size: contain;
    background-repeat: no-repeat;
}

.cell-right {
    display: flex;
    flex-direction: column;
    justify-content: space-between;
}

.cell-top {
    display: flex;
    align-items: start;
    gap: 10px;
    min-width: 0;
    /* margin-top: 10px; */
}
.jacket {
    width: 92px;
    height: 92px;
    flex: none;
    border-radius: 6px;
    object-fit: cover;
    background: rgba(255, 255, 255, 0.25);
}
.mid { flex: 1; min-width: 0; }
.title {
    margin-top: 15px;
    margin-left: 3px;
    /* max-width: 130px; */
    font-size: 14px;
    height: 18px;
    line-height: 1;
    font-weight: bold;
    white-space: nowrap;
    max-width: 170px;
    overflow: hidden;
    text-overflow: ellipsis;

}
.songid {
    font-size: 11px;
    color: #d2a5ff;
}
.remaster .songid {
    color: #a079c7;
}
.cover {
    position: relative;
    margin-top: 4px;
    /* background-color: #9f51dc; */
}
.cell {
    color: #FFF;
}
.remaster {
    color: #433d50;
}

.typeicon {
    height: 17px;
    vertical-align: middle;
    /* margin-right: 4px; */
    position: absolute;
    top: 3px;
    right: 5px;
}
.rank-icon { height: 22px; flex: none; }
.meta {
    font-size: 12px;
    opacity: 0.95;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.meta-top {
    display: flex;
    justify-content: space-between;
    align-items: center;
    /* gap: 15px; */
    margin-right: 10px;
}
.cell-left {
    position: relative;
}

/* 底部落在本底图的白色区域，文字用深色才可读；放不下时自动换行不溢出 */
.cell-bottom {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 4px 10px;
    min-width: 0;
}
.achievements {
    font-size: 24px;
    font-weight: bold;
    white-space: nowrap;
}
.achievements-block {
    margin-top: 2px;
}
.ra { font-size: 12px; opacity: 0.95; padding-top: 2px; white-space: nowrap; font-weight: bold;}
.dxline {
    color: #4A2E86;
    margin-top: 2px;
    font-size: 11px;
    font-weight: bold;
    opacity: 0.9;
    white-space: nowrap;
}
/* .badges { display: flex; align-items: center; gap: 3px; margin-left: auto; }
.badges img { height: 22px; width: auto; } */
.badges {
    display: flex;
    align-items: center;
    padding-top: 13px;
    height: 39px;
}
.badge:first-child {
    width: 58px;
    margin-right: 2px;
}
.badge {
    list-style: none;
    /* width: 50px; */
}
.badges .round img {
    height: 39px;
    margin-right: -2px;
}
.badges .round {
    width: 39px;
    margin-right: -2px;
}
.badge img {
    height: 28px;
}

.stars-strip {
    height: 22px;
    width: auto;
    /* position: absolute; */
    /* top: 3px; */
    /* right: 5px; */
}
/* 头部：logo + 头像 + 官方姓名牌 + rating 框 */
.header {
    display: flex;
    align-items: center;
    flex-direction: row-reverse;
    justify-content: space-between;
    gap: 14px;
    margin-bottom: 18px;
}
.logo { height: 110px; width: auto; }
.avatar {
    width: 110px;
    height: 110px;
    object-fit: cover;
    border-radius: 10px;
    border: 3px solid rgba(255, 255, 255, 0.9);
}
.plate {
    position: relative;
    width: 800px;
    height: 130px;
    display: flex;
    flex: none;
    align-items: center;
    gap: 10px;
    padding-left: 10px;
    background-size: cover;
    background-position: center;
    border-radius: 10px;
    border: 4px solid #fff;
}

.plate .name {
    font-size: 22px;
    font-weight: bold;
    color: #202020;
    background-image: url('__NAME_PLATE__');
    background-size: contain;
    background-position: center;
    background-repeat: no-repeat;
    width: 300px;
    height: 50px;
    display: flex;
    justify-content: space-between;
    letter-spacing: 0.07em;
    padding: 5px;
    padding-left: 10px;
    align-items: center;
}

.plate .summary {
    font-size: 14px;
    color: #202020;
    background-image: url('__PROGRESS_SMALL__');
    background-size: cover;
    background-position: center;
    display: flex;
    justify-content: center;
    align-items: center;

    border-radius: 999px;
    height: 25px;
}
.daniplate {
    height: 100%;
}
.plate .summary span {
    width: calc(100% - 5px);
    text-align: center;
    height: calc(100% - 5px);
    font-weight: bold;
    background-color: #fff;
    border-radius: 999px;
}
.plate .info {
    display: flex;
    flex-direction: column;
}
.rating-box {
    position: relative;
    width: 186px;
    height: 35px;
    flex: none;
    background-size: 100% 100%;
}
.rating-box .digits {
    position: absolute;
    left: 85px;
    top: 8px;
    height: 20px;
    display: flex;
    padding: 2px 2px;
    gap: 1px;
}
.rating-box .digits img {
    height: 100%; margin-right: 0;
 }

.deonlogo {
    flex: 1;
    height: 100%;
    padding: 30px;
    display: flex;
    justify-content: right;
}

.deonlogo img {
    height: 100%;
    filter: drop-shadow(4px 4px 6px rgba(6, 5, 27, 0.3));
}
"""


def _truncate_title(title: str, limit: int = 18) -> str:
    """按显示宽度截断曲名（全角算 2、半角算 1，约 18 个全角位）。"""
    width = 0
    out = []
    for ch in title:
        width += 2 if ord(ch) > 0x2E80 else 1
        if width > limit * 2:
            return "".join(out) + "..."
        out.append(ch)
    return "".join(out)


def _rank_text(rate: str) -> str:
    """把评级缩写转为官方评级图名（sssp -> SSSp）。"""
    if not rate:
        return ""
    return rate[:-1].upper() + "p" if rate.endswith("p") else rate.upper()


def _header(data: B50CardData) -> str:
    """头部：官方姓名牌（deon 背景 + 头像 + rating 框数字 + 名字/段位牌/汇总）+ logo。"""
    avatar = data.avatar_uri or data.ui.get("deon_avatar", "")
    digits = "".join(
        f'<img src="{data.pic(f"UI_NUM_Drating_{d}.png")}" alt="{d}">'
        for d in f"{data.rating:05d}"
    )
    summary = f"[水鱼] {sum(s.ra for s in data.sd)} + {sum(s.ra for s in data.dx)} = {data.rating}"
    return f"""
            <div class="header">
                <img class="logo" src="{data.pic("prism_plus/logo.png")}"
                    alt>
                <!-- deon-bg 已经上传至仓库的 static 里，这是默认背景，以后允许用户自定义背景，并且可以在shop里买背景 -->
                <div class="plate"
                    style="background-image: url('{data.ui.get("deon_bg", "")}')">
                    <!-- 默认头像用 deon avatar，已上传至仓库，优先使用用户的 qq 头像 -->
                    <img class="avatar"
                        src="{avatar}" alt
                        onerror="this.style.display='none'">
                    <div class="info">
                        <div class="rating-box"
                            style="background-image: url('{data.rating_frame}')">
                            <div class="digits">{digits}</div>
                        </div>
                        <div class="name"><span>{html.escape(data.username)}</span><img
                                class="daniplate"
                                src="{data.pic("UI_DNM_DaniPlate_00.png")}"
                                alt></div>
                        <div class="summary"><span>{html.escape(summary)}</span></div>
                    </div>
                    <!-- Deon logo 已上传至仓库的 static 里 -->
                    <div class="deonlogo">
                        <img src="{data.ui.get("deon_logo", "")}" alt
                            class>
                    </div>
                </div>

            </div>"""

def _score_cell(score, data) -> str:
    """流式组装单条成绩卡（行底图随难度切换，Re:Master 需 remaster 类改配色）。"""
    idx = score.level_index
    remaster = " remaster" if idx == 4 else ""
    cover = data.covers.get(str(score.song_id), "")
    type_icon = data.chart_icons.get(score.type, "")
    rank = data.pic(f"prism_plus/UI_TTR_Rank_{_rank_text(score.rate)}.png") if score.rate else ""
    combo = data.pic(f"UI_MSS_MBase_Icon_{COMBO_ICON[score.fc]}.png") if score.fc in COMBO_ICON else ""
    sync = data.pic(f"UI_MSS_MBase_Icon_{SYNC_ICON[score.fs]}.png") if score.fs in SYNC_ICON else ""
    strip = data.pic(f"UI_GAM_Gauge_DXScoreIcon_0{score.stars}.png") if score.stars else ""
    title = html.escape(_truncate_title(score.title))
    bg = data.pic(f"{DIFF_BG[idx]}.png")
    alt_strip = "★" * score.stars if score.stars else ""

    jacket = f'<img class="jacket" src="{cover}" onerror="this.style.display=\'none\'">' if cover else ""
    type_part = f'<img class="typeicon" src="{type_icon}">' if type_icon else ""
    badge = ""
    badge_body = ['<li class="badge"></li>', '<li class="badge round"></li>', '<li class="badge round"></li>', '<li class="badge"></li>']
    if rank:
        badge_body[0] = (f'<li class="badge"><img class="rank-icon" src="{rank}" '
                  f'alt="{html.escape(score.rate.upper())}"></li>')
    if combo:
        badge_body[1] = f'<li class="badge round"><img src="{combo}" alt="{score.fc.upper()}"></li>'
    if sync:
        badge_body[2] = f'<li class="badge round"><img src="{sync}" alt></li>'
    if strip:
        badge_body[3] = f'<li class="badge"><img class="stars-strip" src="{strip}" alt="{alt_strip}"></li>'
    badge = "\n".join(badge_body)
    badges = f'<ul class="badges">{badge}</ul>'
    return f"""
                <div class="cell{remaster}" style="background-image: url('{bg}');">
                    <div class="cell-left">

                        <div class="cover">
                            {jacket}
                            {type_part}
                        </div>
                        <div class="dxline">DX {score.dx_score}/{score.max_dx_score or "?"}</div>
                    </div>
                    <div class="cell-right">
                        <div class="cell-top">
                            <div class="mid">
                                <div class="meta"><div class="meta-top">
                                        <div class="ra">{score.ds:.1f} &gt;&gt;&gt;
                                            {score.ra}</div>
                                        <div class="songid">id{score.song_id}
                                        </div>
                                    </div>
                                    <div class="title">
                                        {title}

                                    </div>
                                </div>
                                <div class="achievements-block">
                                    <span class="achievements">{score.achievements:.4f}%</span>
                                </div>
                            </div>
                        </div>
                        <div class="cell-bottom" style="color: #FFFFFF;">
                            {badges}
                        </div>
                    </div>
                </div>"""


def render(data) -> str:
    """渲染 official 皮肤 B50 查分卡，返回完整 HTML 文档。"""
    sd_cells = "".join(_score_cell(s, data) for s in data.sd)
    dx_cells = "".join(_score_cell(s, data) for s in data.dx)
    font_data = _load_font_data()
    font_src = "data:font/ttf;base64," + base64.b64encode(font_data).decode('ascii') if font_data else "__SGM_FONT__"
    style = (_STYLE
             .replace("__SGM_FONT__", font_src)
             .replace("__B50_BG__", data.pic("prism_plus/b50.png"))
             .replace("__NAME_PLATE__", data.pic("Name.png"))
             .replace("__PROGRESS_SMALL__", data.pic("progress_small.png")))
    return f"""<!DOCTYPE html>
<html lang="zh">
    <head><meta charset="utf-8">
        <style>
{style}
        </style></head>
    <body>
        <div class="stage">
            <div class="stagecover">
            {_header(data)}
            <div class="section-title">- BEST 35 -</div>
            <div class="grid">{sd_cells}</div>
            <div class="section-title">- BEST 15 -</div>
            <div class="grid">{dx_cells}</div>
            <div
                style="text-align: center; font-size: 14px; color: #fff; margin-top: 6px; text-shadow: #20202044 0 0 3px;">
                Data from Diving-Fish - Generated by XME-Bot</div>
            </div>
        </div>
    </body></html>
"""
