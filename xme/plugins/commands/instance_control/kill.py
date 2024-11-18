from nonebot import on_command, CommandSession
import os
import xme.plugins.commands.instance_control as ic
from character import get_message

kill_alias = ['inst_关机', 'inst_shutdown']
cmd_name = 'inst_kill'
@on_command(cmd_name, aliases=kill_alias, only_to_me=True, permission=lambda x: x.is_superuser)
async def _(session: CommandSession):
    reply = (await session.aget(prompt=f"[CQ:at,qq={session.event.user_id}] {get_message(ic.__plugin_name__, 'kill_prompt')}"))
    # reply = (await session.aget(prompt=f"[CQ:at,qq={session.event.user_id}] 请输入 Y 确定杀死 bot 进程..."))
    if reply.strip() != "Y":
        await session.send(get_message(ic.__plugin_name__, 'kill_cancelled'))
        # await session.send("取消杀死 bot 进程。")
        return
    await session.send(get_message(ic.__plugin_name__, 'on_kill'))
    # await session.send("(正在杀死 bot 进程) uwu")
    os._exit(0)