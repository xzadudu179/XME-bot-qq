from nonebot import CommandSession
from xme.xmetools.plugintools import on_command
from xme.xmetools.doctools import CommandDoc
from ...xmetools import systools as st
from character import get_message
# import heapq
from xme.xmetools.jsontools import read_from_path, save_to_path
from xme.xmetools.msgtools import send_session_msg, image_msg
from xme.xmetools.bottools import bot_call_action
from xme.plugins.commands.xme_user.classes import user
from xme.xmetools.plugintools import PluginCallData
from xme.xmetools.drawtools import generate_command_trend_chart

from collections import defaultdict

from datetime import datetime, timedelta

TOP_K = 5

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

@on_command(__plugin_name__, aliases=alias, only_to_me=False, permission=lambda _: True)
async def _(session: CommandSession):
    message = ""
    no_info = get_message("plugins", __plugin_name__, 'no_version_info')
    info = await bot_call_action(session.bot, "get_version_info", error_action=lambda _: no_info)
    if info != no_info and isinstance(info, dict):
        info = f'- bot 实例 APP: {info["app_name"]} v{info["app_version"]}'
    try:
        message = st.system_info()
    except Exception:
        message = get_message("plugins", __plugin_name__, 'fetch_failed')
        # message = "当前运行设备暂不支持展示系统状态——"
    vars = read_from_path("data/bot_vars.json")
    save_to_path("data/bot_vars.json", vars)
    # user_datas = read_from_path("./data/users.json")
    user_count = len(user.User.get_users())

    # 获取指令统计数据
    datas = PluginCallData.get_datas()
    if datas:
        # 过滤最近95天的数据
        current_time = datetime.now()
        start_time = current_time - timedelta(days=95)
        # 将 start_time 转换为时间戳，在循环过滤时直接对比浮点数，效率更高
        start_timestamp = start_time.timestamp()
        filtered_datas = [d for d in datas if d.call_time >= start_timestamp]

        if filtered_datas:
            # 按每 7 天聚合调用量
            periods = defaultdict(lambda: defaultdict(int))
            for d in filtered_datas:
                dt = datetime.fromtimestamp(d.call_time)
                # 计算该条数据距离 start_time 过去了多少天
                delta_days = (dt - start_time).days
                # 整除 7 得到所在的周期索引 (0, 1, 2...)
                period_index = delta_days // 7
                periods[period_index][d.name] += 1

            period_list = sorted(periods.keys())
            names = set(d.name for d in filtered_datas)

            # 计算总日均调用量，总跨度为 95 天，选择前TOP_K
            total_daily_avg = {}
            for name in names:
                total_calls = sum(periods[p].get(name, 0) for p in period_list)
                total_daily_avg[name] = total_calls / 95.0
            top_k = sorted(total_daily_avg.items(), key=lambda x: x[1], reverse=True)[:TOP_K]

            # 绘制趋势图
            data_list = []
            for name, _ in top_k:
                x = list(range(len(period_list)))
                y = []
                for p in period_list:
                    # 95 天无法被 7 完全整除 (95 = 13 * 7 + 4)
                    # 前 13 个周期是满 7 天的，最后一个周期只有 4 天
                    # 这里动态计算除数，确保最后一个周期的日均调用量统计客观准确
                    days_in_period = 7 if p < (95 // 7) else (95 % 7)
                    y.append(periods[p].get(name, 0) / days_in_period)

                data_list.append((x, y, name))

            image_path, _ = generate_command_trend_chart(
                data_list,
                title=f'最近 95 天日均调用最多的 {TOP_K} 个指令',
                xlabel='时间周期（每7天）',
                ylabel='日均调用量'
            )
            message += "=== 当前 bot 状态 ===\n" + info + f"\n===============\nBOT 记录了 {user_count:,} 位用户。" + "\n=== 指令统计 ===\n"
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