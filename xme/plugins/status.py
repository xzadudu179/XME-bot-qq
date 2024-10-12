from nonebot import on_command, CommandSession
from ..xmetools import cur_system as st

@on_command('status', aliases=('系统状态', 'stats'), only_to_me=False)
async def _(session: CommandSession):
    message = ""
    try:
        message = st.system_info()
    except:
        message = "当前运行设备暂不支持展示系统状态——"
    await session.send(message)