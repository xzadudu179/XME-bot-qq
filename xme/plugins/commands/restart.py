from nonebot import on_command, CommandSession
import subprocess
import os, signal
import bot_variables as v
from xme.xmetools.doc_gen import CommandDoc

alias = ['重启']
__plugin_name__ = 'restart'

__plugin_usage__ = str(CommandDoc(
    name=__plugin_name__,
    desc='重启 bot',
    introduction='使机器人实例重新启动',
    usage=f'',
    permissions=["需要 @ bot 或是呼叫 bot", "是 SUPERUSER"],
    alias=alias
))

@on_command('restart', aliases=alias, only_to_me=True, permission=lambda x: x.is_superuser)
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
