from nonebot import on_command, CommandSession
from xme.xmetools.doc_gen import CommandDoc
from ...xmetools import cur_system as st
import config

alias = ['系统状态', 'stats']
__plugin_name__ = 'status'
__plugin_usage__ = str(CommandDoc(
    name=__plugin_name__,
    desc='查看系统状态',
    introduction='查看运行该 XME-Bot 实例的设备的系统状态',
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
        message = "当前运行设备暂不支持展示系统状态——"
    await session.send(message)