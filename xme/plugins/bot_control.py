from nonebot import on_command, CommandSession
import subprocess
import os, signal
import bot_variables as v

__plugin_name__ = 'restart'
__plugin_usage__ = r"""
重启 bot
权限：需要 SUPERUSER 身份
restart
""".strip()

@on_command('restart', aliases=('重启'), only_to_me=True, permission=lambda x: x.is_superuser)
async def _(session: CommandSession):
    await session.send("正在重启 uwu")
    try:
        subprocess.Popen(['python', './bot.py'])
        await session.send("已启动新的 xmebot 进程啦, 正在杀死原进程...")
        try:
            # os.kill(oldpid, signal.SIGTERM)
            os._exit(0)
        except Exception as ex:
            await session.send(f"无法杀死原 xmebot 进程 xwx\n错误原因: {ex}")
            return
    except Exception as ex:
        await session.send(f"重启失败 xwx\n错误原因: {ex}\ntraceback:\n{ex.with_traceback()}")
