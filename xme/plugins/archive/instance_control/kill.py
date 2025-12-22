from nonebot import on_command, CommandSession
from xme.xmetools.msgtools import send_session_msg, aget_session_msg
import os
import xme.plugins.commands.instance_control as ic
from character import get_message
from xme.xmetools.bottools import permission

kill_alias = ['inst_关机', 'inst_shutdown']
cmd_name = 'inst_kill'
@on_command(cmd_name, aliases=kill_alias, only_to_me=True, permission=lambda x: True)
@permission(lambda sender: sender.is_superuser, permission_help="是 SUPERUSER")
async def _(session: CommandSession):
    reply = (await aget_session_msg(session, prompt=f"{get_message('plugins', ic.__plugin_name__, 'kill_prompt')}"))
    if reply.strip() != "Y":
        await send_session_msg(session, get_message("plugins", ic.__plugin_name__, 'kill_cancelled'))
        # await send_msg(session, "取消杀死 bot 进程。")
        return
    await send_session_msg(session, get_message("plugins",ic.__plugin_name__, 'on_kill'))
    # await send_msg(session, "(正在杀死 bot 进程) uwu")
    os._exit(0)