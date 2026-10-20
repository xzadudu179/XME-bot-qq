from nonebot import CommandSession
import asyncio
from xme.xmetools.plugintools import on_command
from xme.xmetools.doctools import CommandDoc
from ...xmetools import systools as st
from character import get_message
# import heapq
from xme.xmetools.jsontools import read_from_path, save_to_path
from xme.xmetools.msgtools import send_session_msg, image_msg
from xme.xmetools.bottools import bot_call_action
from xme.plugins.commands.xme_user.classes import user
from xme.plugins.commands.ai_helper.llm import balance as ai_balance
from xme.xmetools.plugintools import PluginCallData
from xme.xmetools.drawtools import generate_command_stats_charts

from collections import defaultdict

from datetime import datetime, timedelta

TOP_K = 8
STATS_DAYS = 95  # 指令统计窗口（天）

alias = ['系统状态', 'stats']
__plugin_name__ = 'status'
__plugin_usage__ = CommandDoc(
    name=__plugin_name__,
    desc=get_message("plugins", __plugin_name__, 'desc'),
    # desc='查看系统状态',
    introduction=get_message("plugins", __plugin_name__, 'introduction'),
    # introduction='查看运行该 XME-Bot 实例的设备的系统状态',
    usage='',
    permissions=["无"],
    alias=alias
)


def weekly_chart_data(datas, start_time):
    """把调用记录按每 7 天一个周期聚合为趋势图数据。

    返回 (data_list, top_names)：data_list 为 (x, y, 指令名) 列表（与 drawtools 的
    数据格式一致）；top_names 是取出的 TOP_K 指令名（按总调用量降序），供时段图
    复用同一顺序，保证两图同名指令颜色一一对应。
    """
    # 按每 7 天聚合调用量
    periods = defaultdict(lambda: defaultdict(int))
    for d in datas:
        dt = datetime.fromtimestamp(d.call_time)
        # 计算该条数据距离 start_time 过去了多少天
        delta_days = (dt - start_time).days
        # 整除 7 得到所在的周期索引 (0, 1, 2...)
        periods[delta_days // 7][d.name] += 1

    period_list = sorted(periods.keys())
    names = set(d.name for d in datas)

    # 计算总日均调用量，总跨度为 STATS_DAYS 天，选择前 TOP_K
    total_daily_avg = {
        name: sum(periods[p].get(name, 0) for p in period_list) / STATS_DAYS
        for name in names
    }
    top_k = sorted(total_daily_avg.items(), key=lambda x: x[1], reverse=True)[:TOP_K]

    data_list = []
    for name, _ in top_k:
        x = list(range(len(period_list)))
        y = []
        for p in period_list:
            # STATS_DAYS 天无法被 7 完全整除（如 95 = 13 * 7 + 4）：前面的周期是
            # 满 7 天的，最后一个周期不足 7 天，这里动态计算除数，确保最后一个
            # 周期的日均调用量统计客观准确
            days_in_period = 7 if p < (STATS_DAYS // 7) else (STATS_DAYS % 7)
            y.append(periods[p].get(name, 0) / days_in_period)

        data_list.append((x, y, name))
    return data_list, [name for name, _ in top_k]


def hourly_chart_data(datas, top_names):
    """按小时（0~23 时）统计各指令的每日平均调用次数，返回时段图 data_list。

    输出顺序与 top_names 一致（即趋势图同序，两图同名指令颜色对应）；
    某小时没有调用记 0，绘制层会按下限贴底显示。
    """
    wanted = set(top_names)
    counts = defaultdict(lambda: defaultdict(int))
    for d in datas:
        if d.name in wanted:
            counts[d.name][datetime.fromtimestamp(d.call_time).hour] += 1
    return [
        (list(range(24)),
         [counts[name].get(hour, 0) / STATS_DAYS for hour in range(24)],
         name)
        for name in top_names
    ]


@on_command(__plugin_name__, aliases=alias, only_to_me=False, permission=lambda _: True)
async def _(session: CommandSession):
    message = ""
    no_info = get_message("plugins", __plugin_name__, 'no_version_info')
    info = await bot_call_action(session.bot, "get_version_info", error_action=lambda _: no_info)
    if info != no_info and isinstance(info, dict):
        info = f'- bot 实例 APP: {info["app_name"]} v{info["app_version"]}'
    try:
        # system_info 内含 lsblk 子进程与 psutil 采样，同步执行须放后台线程
        message = await asyncio.to_thread(st.system_info)
    except Exception:
        message = get_message("plugins", __plugin_name__, 'fetch_failed')
        # message = "当前运行设备暂不支持展示系统状态——"
    vars = read_from_path("data/bot_vars.json")
    save_to_path("data/bot_vars.json", vars)
    # user_datas = read_from_path("./data/users.json")
    user_count = len(user.User.get_users())

    # AI provider 余额段：只展示查到余额的 provider，未知家数附在总计后
    balance_msg = ""
    try:
        balances = await ai_balance.get_providers_balance()
        if balances:
            known = [b for b in balances if b.balance is not None]
            unknown = len(balances) - len(known)
            rows = "; ".join(f"{b.provider}: {ai_balance.format_balance(b)}" for b in known)
            totals = ai_balance.format_total_balance(ai_balance.total_by_currency(balances))
            suffix = f"（未知 {unknown} 家）" if unknown else ""
            body = f"{rows}\n" if rows else ""
            balance_msg = f"\n=== AI 余额 ===\n{body}总计: {totals}{suffix}"
    except Exception:
        pass

    # 获取指令统计数据（SQL 直接限定 STATS_DAYS 天窗口，统计表逐指令增长、不能全表加载）
    start_time = datetime.now() - timedelta(days=STATS_DAYS)
    datas = PluginCallData.get_datas(since=start_time.timestamp())
    if datas:
        filtered_datas = datas

        if filtered_datas:
            trend_data, top_names = weekly_chart_data(filtered_datas, start_time)
            hourly_data = hourly_chart_data(filtered_datas, top_names)
            # matplotlib 画图是同步 CPU 密集操作，放后台线程执行；
            # 左右拼成一张横向图：左=每 7 天周期趋势，右=每日各时段分布（同序同色）
            image_path, _ = await asyncio.to_thread(
                generate_command_stats_charts,
                trend_data,
                hourly_data,
                trend_title=f'最近 {STATS_DAYS} 天日均调用最多的 {TOP_K} 个指令',
                trend_xlabel='时间周期（每7天）',
                trend_ylabel='日均调用量',
                hourly_title=f'最近 {STATS_DAYS} 天每日各时段的日均调用量',
                hourly_xlabel='时段（小时）',
                hourly_ylabel='日均调用量'
            )
            message += ("=== 当前 bot 状态 ===\n" + info
                        + f"\n===============\nBOT 记录了 {user_count:,} 位用户。"
                        + balance_msg + "\n=== 指令统计 ===\n")
            # 发送图片
            await send_session_msg(
                session, message + (await image_msg(image_path)),
                tips=True
            )
        else:
            await send_session_msg(
                session, message + "最近3个月无指令调用数据",
                tips=True
            )
    else:
        await send_session_msg(
            session, message + "无指令调用数据",
            tips=True
        )