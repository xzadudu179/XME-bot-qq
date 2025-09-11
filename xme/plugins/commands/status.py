from nonebot import on_command, CommandSession
from xme.xmetools.doctools import CommandDoc
from ...xmetools import systools as st
from character import get_message
import heapq
from xme.xmetools.jsontools import read_from_path, save_to_path
from xme.xmetools.msgtools import send_session_msg
from xme.xmetools.bottools import bot_call_action
from xme.plugins.commands.xme_user.classes import user

alias = ['系统状态', 'stats']
__plugin_name__ = 'status'
__plugin_usage__ = str(CommandDoc(
    name=__plugin_name__,
    desc=get_message("plugins", __plugin_name__, 'desc'),
    # desc='查看系统状态',
    introduction=get_message("plugins", __plugin_name__, 'introduction'),
    # introduction='查看运行该 XME-Bot 实例的设备的系统状态',
    usage=f'',
    permissions=["无"],
    alias=alias
))

@on_command(__plugin_name__, aliases=alias, only_to_me=False, permission=lambda _: True)
async def _(session: CommandSession):
    message = ""
    no_info = get_message("plugins", __plugin_name__, 'no_version_info')
    info = await bot_call_action(session.bot, "get_version_info", error_action=lambda _: no_info)
    print(info)
    if info != no_info and isinstance(info, dict):
        info = f'- bot 实例 APP: {info["app_name"]} v{info["app_version"]}'
    try:
        message = st.system_info()
    except:
        message = get_message("plugins", __plugin_name__, 'fetch_failed')
        # message = "当前运行设备暂不支持展示系统状态——"
    vars = read_from_path("data/bot_vars.json")
    usage: dict = read_from_path("data/usage_stats.json")["usages"]
    call_sum = 0
    for k, v in usage.items():
        # print(k, len(v["calls"]))
        call_sum += len(v["calls"])
    top_k_usage = heapq.nlargest(3, usage, key=lambda k: len(usage[k]["calls"]))
    top_k_str = '\n'.join([f'{i + 1}、' + u + f"\t 被调用了 {len(usage[u]['calls']):,} 次。" for i, u in enumerate(top_k_usage)])
    save_to_path("data/bot_vars.json", vars)
    # user_datas = read_from_path("./data/users.json")
    user_count = len(user.User.get_users())

    await send_session_msg(
        session, message + "=== 当前 bot 状态 ===\n" +
        info +
        f"\n===============\nBOT 自始以来被调用了 {call_sum:,} 次，记录了 {user_count:,} 位用户。以下是 3 个最常被调用的指令：\n{top_k_str}",
        tips=True
    )