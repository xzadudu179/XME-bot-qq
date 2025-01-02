from nonebot import on_command, CommandSession
from xme.xmetools.doc_tools import CommandDoc
from ...xmetools import cur_system as st
from character import get_message
from xme.xmetools.command_tools import send_cmd_msg

alias = ['系统状态', 'stats']
__plugin_name__ = 'status'
__plugin_usage__ = str(CommandDoc(
    name=__plugin_name__,
    desc=get_message(__plugin_name__, 'desc'),
    # desc='查看系统状态',
    introduction=get_message(__plugin_name__, 'introduction'),
    # introduction='查看运行该 XME-Bot 实例的设备的系统状态',
    usage=f'',
    permissions=[],
    alias=alias
))

@on_command(__plugin_name__, aliases=alias, only_to_me=False)
async def _(session: CommandSession):
    message = ""
    try:
        message = st.system_info()
    except:
        message = get_message(__plugin_name__, 'fetch_failed')
        # message = "当前运行设备暂不支持展示系统状态——"
    await send_cmd_msg(session, message)