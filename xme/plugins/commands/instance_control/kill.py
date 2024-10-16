from nonebot import on_command, CommandSession
import os

kill_alias = ['关机', 'shutdown']
@on_command('kill', aliases=kill_alias, only_to_me=True, permission=lambda x: x.is_superuser)
async def _(session: CommandSession):
    reply = (await session.aget(prompt=f"[CQ:at,qq={session.event.user_id}] 请输入 Y 确定杀死 bot 进程..."))
    if reply.strip() != "Y":
        await session.send("取消杀死 bot 进程。")
        return
    await session.send("(正在杀死 bot 进程) uwu")
    os._exit(0)