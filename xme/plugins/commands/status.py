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
        # 过滤最近3个月的数据
        current_time = datetime.now()
        three_months_ago = current_time - timedelta(days=90)
        filtered_datas = [d for d in datas if datetime.fromtimestamp(d.call_time) >= three_months_ago]

        if filtered_datas:
            # 按周聚合调用量
            weeks = defaultdict(lambda: defaultdict(int))
            for d in filtered_datas:
                dt = datetime.fromtimestamp(d.call_time)
                year, week, _ = dt.isocalendar()
                weeks[(year, week)][d.name] += 1

            weeks_list = sorted(weeks.keys())
            names = set(d.name for d in filtered_datas)

            # 计算总日均调用量，选择前TOP_K
            total_daily_avg = {}
            for name in names:
                total_calls = sum(weeks[w].get(name, 0) for w in weeks_list)
                total_daily_avg[name] = total_calls / (len(weeks_list) * 7)
            top_k = sorted(total_daily_avg.items(), key=lambda x: x[1], reverse=True)[:TOP_K]

            # 绘制趋势图
            data_list = []
            for name, _ in top_k:
                x = list(range(len(weeks_list)))
                y = [weeks[w].get(name, 0) / 7 for w in weeks_list]
                data_list.append((x, y, name))
            image_path, _ = generate_command_trend_chart(data_list, title=f'最近 3 个月日均调用最多的 {TOP_K} 个指令', xlabel='周数', ylabel='日均调用量')
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