from nonebot import on_command, CommandSession
from xme.xmetools.doc_tools import CommandDoc
from ...xmetools import cur_system as st
from character import get_message
from xme.xmetools.message_tools import send_session_msg
from xme.xmetools.bot_control import bot_call_action

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
        info = f'- bot 实例 APP: {info["app_name"]} v{info["app_version"]}\n- 协议: {info["nt_protocol"]} {info["protocol_version"]}'
    try:
        message = st.system_info()
    except:
        message = get_message("plugins", __plugin_name__, 'fetch_failed')
        # message = "当前运行设备暂不支持展示系统状态——"
    await send_session_msg(session, message + "=== 当前 bot 状态 ===\n" + info)