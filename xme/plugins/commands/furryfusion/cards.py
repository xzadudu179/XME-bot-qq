from itertools import groupby

from xme.xmetools.templates import FONTS_STYLE
from xme.plugins.commands.xme_user.classes.user import User
from xme.xmetools.loctools import short_region

from .providers.base import FurEvent, FurProvider

STATE = {
    0: "活动结束",
    1: "预告中",
    2: "售票中",
    3: "活动中",
    4: "活动取消"
}

# 时间表列数：用户可经 /fus 数字 调整，命令层用 MIN/MAX 校验输入范围
DEFAULT_CARDS_PER_ROW = 2
CARDS_PER_ROW_MIN = 1
CARDS_PER_ROW_MAX = 6
# 卡片与容器尺寸：CSS 与本文件的宽度计算共用同一来源（.main-container 的
# width 由 container_width 注入，映射到 CSS 的左右 padding 为 CONTAINER_PADDING_X/2；
# .rec-timeline 的 3px 左边框 + 25px 左内边距计入 TIMELINE_WIDTH_LOSS）
CARD_WIDTH = 400
CARD_MARGIN_X = 40          # 卡片左右外边距合计
CONTAINER_PADDING_X = 50    # 容器左右内边距合计
TIMELINE_WIDTH_LOSS = 30    # 时间线左边框 + 左内边距占用（含 2px 余量）
# 高度估算：行高按缩略图 + 文字区并留余量；页眉页脚按年份标题 + 页脚 + 内边距估算
CARD_ROW_HEIGHT = 400
RENDER_HEADER_HEIGHT = 1400


def _check_cards_per_row(cards_per_row) -> int:
    """校验时间表列数为正整数，非法输入直接抛错。"""
    try:
        value = int(cards_per_row)
    except (TypeError, ValueError) as ex:
        raise ValueError(f"时间表列数必须是整数，收到 {cards_per_row!r}") from ex
    if value < 1:
        raise ValueError(f"时间表列数必须大于 0，收到 {value}")
    return value


def estimate_render_height(events: list[FurEvent], cards_per_row: int = DEFAULT_CARDS_PER_ROW) -> int:
    """估算卡片渲染所需视口高度：逐月统计卡片行数，加页眉页脚余量。

    渲染视口过矮会截掉末尾的卡片与页脚，过高只是多出的透明区被裁掉。
    """
    cards_per_row = _check_cards_per_row(cards_per_row)
    month_counts: dict[tuple[int, int], int] = {}
    for event in events:
        key = (event.start.year, event.start.month)
        month_counts[key] = month_counts.get(key, 0) + 1
    rows = sum(-(-count // cards_per_row) for count in month_counts.values())
    return RENDER_HEADER_HEIGHT + rows * CARD_ROW_HEIGHT


def container_width(cards_per_row: int = DEFAULT_CARDS_PER_ROW) -> int:
    """时间表容器宽度：按列数容纳卡片行（宽度同时决定渲染视口宽度）。"""
    n = _check_cards_per_row(cards_per_row)
    return CONTAINER_PADDING_X + TIMELINE_WIDTH_LOSS + (CARD_WIDTH + CARD_MARGIN_X) * n


def render_size(events: list[FurEvent], cards_per_row: int = DEFAULT_CARDS_PER_ROW) -> tuple[int, int]:
    """时间表渲染视口尺寸 (宽, 高)：宽按列数容纳容器，高按活动行数估算。"""
    return container_width(cards_per_row), estimate_render_height(events, cards_per_row)

def get_event_card(event: FurEvent, u: User, provider: FurProvider):
    """渲染单张活动卡片：顶部缩略图为活动封面，下方为标题与时间信息。"""
    state_class = {
        0: "cancelled",
        1: "",
        2: "",
        3: "on-event",
        4: "cancelled",
    }
    c = state_class[event.state]
    state_c = c
    if event.state in [0, 3, 4]:
        daysleft_str = {
            0: "活动结束",
            3: "正在进行",
            4: "活动取消"
        }[event.state]
    else:
        time_surplus = event.days_until
        if time_surplus < 10:
            c = "about-begin"
        daysleft_str = f"剩余 {time_surplus} 天"
        if time_surplus <= 0:
            c = "on-event"
            daysleft_str = "即将开始"
    title_class = ""
    if event.duration_days > 3:
        title_class = "gold"
    loc_class = ""
    border_c = ""
    # 本地高亮：优先省份匹配（同城不同市也算本地），城市名互含作为兜底
    loc = u.plugin_datas.get("location", {})
    user_province = short_region(loc.get("adm1") or "")
    user_city = short_region(loc.get("adm2") or "")
    is_local = bool(user_province and event.province and user_province == event.province) \
        or bool(user_province and user_province in event.region) \
        or bool(user_city and event.region and (user_city in event.region or event.region in user_city))
    if is_local:
        loc_class = "gold-small"
    if loc_class == "gold-small" and title_class == "gold":
        c = "gold"
        border_c = "gold-border"
    if event.start.year == event.end.year:
        time_formatted = f"{event.start.month}.{event.start.day} - {event.end.month}.{event.end.day}"
    else:
        time_formatted = f"{event.time_start} - {event.time_end}"
    # 大标题显示主办方品牌名，活动主题名放小字；缺品牌名时回退为主题名
    main_title = event.org or event.title
    sub_title = event.title if event.org else ""
    thumb_url = provider.card_image_url(event.image)
    thumb_style = f" style=\"background-image: url('{thumb_url}')\"" if thumb_url else ""
    return f"""
        <section class="card {border_c}">
            <div class="img">
                <div class="thumbnail"{thumb_style}></div>
                <div class="cover">
                    <div class="top">
                        <h1 class="title {title_class}">{main_title}</h1>
                        <div>
                            <p class="{loc_class}">{event.location_text}</p>
                            <p class="{state_c}">{STATE[event.state]}</p>
                        </div>
                    </div>
                    <div class="bottom">
                        <div>

                            <p>{sub_title}</p>
                            <p>{time_formatted}</p>
                        </div>
                        <div class="btm_right">
                            <p class="remaining daysleft {c}">
                                {daysleft_str}
                            </p>

                        </div>
                    </div>
                </div>
            </div>
        </section>
    """
def get_countdown_cards(events: list[FurEvent], u: User, provider: FurProvider, cards_per_row: int = DEFAULT_CARDS_PER_ROW):
    cards_per_row = _check_cards_per_row(cards_per_row)
    html_head = """
    <!DOCTYPE html>
    <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Document</title>
            <style>
    """ + FONTS_STYLE + """
            :root {
                --strong-color: #94d8ff;
                --text-color: #fffef6;
                --background: #BEAD90;
                --info-color: #9696a0;
                --border-color: #36363e;
                --background-color: #1b1b25;
                --primary-color: #78B9FF;
                --error-color: #ff7a85;
                --about-begin-color: #8affff;
                --on-event-color: #7bffb6;
            }

            * {
                box-sizing: border-box;
                margin: 0;
                padding: 0;
                font-size: 1rem;
                color: var(--text-color);
                font-family: "Helvetica Neue", "Noto Sans CJK SC", "Noto Sans SC", Geist Variable, -apple-system, BlinkMacSystemFont, PingFang SC, Microsoft YaHei, Heiti SC, WenQuanYi Micro Hei, normal;
            }

            h2 span {
                font-size: 2rem;
            }
            h2 {
                border-bottom: 1px solid var(--border-color);
                padding-bottom: 8px;
                margin-bottom: 20px;
            }

            h4 span {
                font-size: 1.2rem;
                font-weight: normal;
                margin-left: 30px;
            }

            h4 {
                display: flex;
                align-items: center;
                /* flex-direction: row; */
                margin-top: 15px;
            }

            .title {
                flex: 1;
                min-width: 0;
                margin-right: 12px;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
            }

            .rec-circsmall {
                width: 12px;
                height: 12px;
                border: 3px solid var(--border-color);
                background: var(--background-color);
                border-radius: 999%;
                margin-left: -32.4px;
                position: relative;
                /* top: 23px; */
            }
            .rec-timeline * {
                font-family: 'Orbitron', "Helvetica Neue", "Noto Sans CJK SC", "Noto Sans SC", Geist Variable, -apple-system, BlinkMacSystemFont, PingFang SC, Microsoft YaHei, Heiti SC, WenQuanYi Micro Hei, normal;
                letter-spacing: 0.06em;
            }
            .rec-timeline {
                width: 100%;
                padding: 0px 0 50px 25px;
                /* margin: 0 12px; */
                border-left: 3px solid;
                border-image: linear-gradient(#0000 0%, var(--border-color) 100px, var(--border-color) 90%, #0000 100%) 1;
            }
            .rec-circbig {
                width: 20px;
                height: 20px;
                border: 3px solid var(--primary-color);
                background: var(--background-color);
                border-radius: 999%;
                margin-left: -36.5px;
                position: relative;
                top: 30px;
                box-shadow: 0 0 50px 5px transparent;
            }
            .rec-circbig + span {
                font-weight: normal;
            }
            .rec-uparrow {
                position: relative;
                top: 20.3px;
                right: 7.9px;
                color: var(--border-color);
                font-size: 25px;
            }

            .card {
                width: """ + str(CARD_WIDTH) + """px;
                margin: """ + str(CARD_MARGIN_X // 2) + """px;
                border-radius: 20px;
                overflow: hidden;
                border: 4px solid rgba(255, 255, 255, 0.116);
                box-shadow: 0 0 15px #FFF1;
            }

            body {
                background-color: transparent;
            }



            .main-container {
                width: """ + str(container_width(cards_per_row)) + """px;
                padding: """ + str(CONTAINER_PADDING_X // 2) + """px;
                background: var(--background-color);
                /* background: url("./img/background/1791.png"); */
                /* background-size: cover; */
            }
            .img {
                max-width: """ + str(CARD_WIDTH) + """px;
                position: relative;
                background-color: #24252e;
            }

            .thumbnail {
                height: 140px;
                background-size: cover;
                background-position: center;
                background-repeat: no-repeat;
                border-bottom: 3px solid var(--border-color);
            }

            .cover {
                width: 100%;
                /* background-color: #0009; */
                /* padding: 20px; */
                position: relative;
            }

            .top {
                width: 100%;
                display: flex;
                justify-content: space-between;
                padding: 10px 20px;
                align-items: center;
            }

            .top p:nth-child(1) {
                padding-top: 10px;
            }

            .top p {
                text-align: right;
            }

            .bottom {
                /* color: white; */
                display: flex;
                justify-content: space-between;
                width: 100%;
                align-items: end;
                padding: 0 20px 20px;
                /* padding-right: 40px; */
            }

            .bottom > div:first-child {
                min-width: 0;
            }

            .bottom p {
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
            }


            h1 {
                font-size: 2rem;
                /* color: var(--strong-color); */
            }

            .data {
                padding: 10px;
                padding-top: 0;
            }

            .right {
                position: relative;
            }

            .daysleft {
                color: var(--strong-color);
                font-size: 1.5rem;
                font-weight: 600;
            }

            .btm_right {
                text-align: right;
            }

            .cancelled {
                color: var(--error-color);
            }

            .on-event {
                color: var(--on-event-color);
            }

            .month {
                display: flex;
                flex-wrap: wrap;
                /* justify-content; */
            }

            footer {
                text-align: center;
            }

            footer p {
                color: var(--info-color);
                font-size: 1em;
                line-height: 1.6em;
            }

            .about-begin {
                color: var(--about-begin-color);
            }

            .gold-border {
                border-color: #3c6a88;
            }

            .gold-small {
                color: #9df4ff;
            }

            .gold {
                /* background: linear-gradient(45deg, #ffb29b 0%, #ffdc9b 100%); */
                color: #9df4ff;
                /* color: transparent; */
                /* background-clip: text; */
                /* -webkit-background-clip: text; */
                /* -moz-background-clip: text; */
            }

        </style>
    </head>
    <body>
        <div class="main-container">
            <div class="rec-timeline">
    """
    html_bottom = """
                </div>
                <footer>
                    <p class="orbitron">数据来源于 {source} 提供的 API.</p>
                </footer>
            </div>
        </body>
    </html>
    """.format(source=provider.source)
    html_content = ""
    ordered = sorted(events, key=lambda e: (e.start.year, e.start.month))
    for year, year_events in groupby(ordered, key=lambda e: e.start.year):
        html_content += f"""
        <h2>
            <div class="rec-circbig"></div>
            <span>{year}</span>
        </h2>
        """
        for month, month_events in groupby(year_events, key=lambda e: e.start.month):
            html_content += f"""
            <h4>
                <div class="rec-circsmall"></div>
                <span>{year}.{month}</span>
            </h4>
            <div class="month">
            """
            for event in month_events:
                html_content += get_event_card(event, u, provider)
            html_content += "</div>"
    return html_head + html_content + html_bottom