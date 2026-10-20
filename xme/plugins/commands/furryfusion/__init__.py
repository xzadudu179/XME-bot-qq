from nonebot import CommandSession
from xme.xmetools.plugintools import on_command
from xme.xmetools.doctools import CommandDoc
from .apicalls import get_countdown, search
from .filters import filter_events
from .cards import (
    get_countdown_cards, STATE, render_size,
    DEFAULT_CARDS_PER_ROW, CARDS_PER_ROW_MIN, CARDS_PER_ROW_MAX,
)
from .providers import get_provider
from .providers.base import FurAPIError, FurEvent
from xme.plugins.commands.xme_user.classes.user import User, using_user
from xme.xmetools.cmdtools import use_args
from xme.xmetools.imgtools import get_html_image_async
from xme.xmetools.typetools import try_parse
from xme.xmetools.texttools import escape_cq
import random
from xme.xmetools.msgtools import CMD_END, send_session_msg, aget_session_msg
from xme.xmetools.msgtools import image_msg
from character import get_message
random.seed()

alias = ['兽聚汇总', '兽聚', 'fus']
__plugin_name__ = 'furfusion'
__plugin_usage__ = CommandDoc(
    name=__plugin_name__,
    desc=get_message("plugins", __plugin_name__, "desc"),
    introduction=get_message("plugins", __plugin_name__, "introduction"),
    usage='<搜索关键词 或 列数(1-6) 或 filter <地区/时间/名称>，不填或序号为兽聚倒计时>',
    permissions=["无"],
    alias=alias
)

# 用户级时间表列数设置存放在 plugin_datas 下的键名
COLUMNS_DATA_KEY = "furfusion_columns"


def get_user_columns(u: User) -> int:
    """读取用户设置的时间表列数，未设置或非法时回落到默认列数。"""
    value = u.plugin_datas.get(COLUMNS_DATA_KEY)
    if isinstance(value, int) and CARDS_PER_ROW_MIN <= value <= CARDS_PER_ROW_MAX:
        return value
    return DEFAULT_CARDS_PER_ROW


def set_user_columns(u: User, columns: int):
    """保存用户的时间表列数设置到用户数据。"""
    u.plugin_datas[COLUMNS_DATA_KEY] = columns
    u.flush()


def parse_columns_arg(arg: str) -> int | None:
    """参数为允许范围内的纯数字时返回列数（用于 /fus 数字 调列数），否则返回 None。"""
    if arg and arg.isdecimal():
        value = int(arg)
        if CARDS_PER_ROW_MIN <= value <= CARDS_PER_ROW_MAX:
            return value
    return None

async def get_search_fusion_data_msg(event: FurEvent):
    """把规范化活动条目渲染为搜索详情消息。"""
    provider = get_provider()
    image_data = await provider.fetch_image_data(event.image) if event.image else None
    msg = get_message(
        "plugins", __plugin_name__, "fusion_data",
        image=await image_msg(image_data, max_size=300) if image_data else "",
        name=escape_cq(event.title),
        state=STATE.get(event.state, "未知"),
        time=event.time_text,
        region=escape_cq(event.location_text) if event.location_text else "未知",
        org=escape_cq(event.org) if event.org else "未知",
        source=provider.source,
    )
    return msg

async def render_timetable(u: User, events: list[FurEvent], cards_per_row: int = DEFAULT_CARDS_PER_ROW):
    """把活动列表渲染为时间表卡片消息。"""
    provider = get_provider()
    html_card = get_countdown_cards(events, u, provider, cards_per_row)
    width, height = render_size(events, cards_per_row)
    msg = get_message("plugins", __plugin_name__, "countdown", image=(await image_msg(await get_html_image_async(html_card, height=height, width=width))))
    return msg


async def get_countdown_card(u: User, cards_per_row: int = DEFAULT_CARDS_PER_ROW):
    """渲染兽聚时间表卡片消息。"""
    return await render_timetable(u, await get_countdown(), cards_per_row)


async def get_filter_card(u: User, cards_per_row: int, condition: str):
    """按地区/时间/名称过滤后渲染时间线，没有匹配活动时返回没有的文案。"""
    filtered = filter_events(await get_countdown(), condition)
    if not filtered:
        return get_message("plugins", __plugin_name__, "no_search_data", keyword=condition)
    return await render_timetable(u, filtered, cards_per_row)


def get_filter_condition(session: CommandSession) -> str:
    """取 /fus filter 之后的完整过滤条件（保留空格分隔的多个词）。

    参数解析器会把参数截断到固定长度，这里直接读指令原文的剩余部分。
    """
    text = (session.current_arg_text or "").strip()
    parts = text.split(None, 1)
    return parts[1].strip() if len(parts) > 1 else ""

async def search_by_name(session: CommandSession, content):
    """搜索兽聚活动，多结果时交互选择，返回详情消息。

    连续 3 次无效输入放弃选择；发送 quit 直接退出选择；
    无效输入里只有包含数字的才会收到提示，纯闲聊消息静默跳过（同样计入次数）。
    """
    datas = await search(content=content)
    data = None
    if len(datas) < 1:
        return get_message("plugins", __plugin_name__, "no_search_data", keyword=content)
    if len(datas) == 1:
        data = datas[0]
    # 搜索到多个结果
    else:
        titles = "\n".join([f"{i + 1}. {d.full_title}（{d.time_start}）" for i, d in enumerate(datas)][:15]) + (f"\n还有 {len(datas) - 15} 个内容" if len(datas) > 15 else "")
        await send_session_msg(session, get_message("plugins", __plugin_name__, "search_mutiple", datas=titles))
        limit = min(len(datas), 15)
        invalid_count = 0
        while data is None and invalid_count < 3:
            index = await aget_session_msg(session, can_use_command=True)
            if index is CMD_END:
                return CMD_END
            if str(index).strip().lower() == "quit":
                return CMD_END
            index_num = try_parse(index, int)
            if index_num is not None and 0 < index_num <= limit:
                data = datas[index_num - 1]
                continue
            invalid_count += 1
            if any(ch.isdigit() for ch in str(index)):
                tip = "index_out_of_range" if index_num is not None else "index_not_num"
                await send_session_msg(session, get_message("plugins", __plugin_name__, tip))
        if data is None:
            return CMD_END
    return await get_search_fusion_data_msg(data)


@on_command(__plugin_name__, aliases=alias, only_to_me=False, permission=lambda _: True)
@using_user(False)
@use_args(arg_len=2)
async def _(session: CommandSession, u: User, arg_list):
    arg = arg_list
    # 默认为 countdown
    mode = "countdown"
    keyword = ""
    condition = ""
    columns = get_user_columns(u)
    match arg[0]:
        case "s":
            mode = "search"
            keyword = arg[1]
        case "filter" | "fil":
            mode = "filter"
            condition = get_filter_condition(session)
    if arg[0] and mode == "countdown":
        # 纯数字且在允许范围内视为调整时间表列数并记住，其余一律按搜索处理
        columns_arg = parse_columns_arg(arg[0])
        if columns_arg is not None:
            columns = columns_arg
            set_user_columns(u, columns)
        else:
            mode = "search"
            keyword = arg[0]
    msg = ""
    try:
        match mode:
            case "countdown":
                msg = await get_countdown_card(u, columns)
            case "search":
                msg = await search_by_name(session, keyword)
            case "filter":
                msg = await get_filter_card(u, columns, condition)
    except FurAPIError as e:
        msg = get_message("plugins", __plugin_name__, "error", info=e.info)
    if msg is CMD_END:
        return
    await send_session_msg(session, msg, tips=True, tips_percent=30)
    return
