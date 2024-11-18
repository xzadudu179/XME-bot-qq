from nonebot import on_command, CommandSession
import subprocess
import os
from character import get_message
import config
import xme.plugins.commands.instance_control as ic

# virtualenv_python = './.venv/bin/python'
restart_alias = ['inst_重启', 'inst_rebot', 'inst_reboot', 'instRestart', 'instRebot', 'instReboot']
cmd_name = 'inst_restart'
@on_command(cmd_name, aliases=restart_alias, only_to_me=True, permission=lambda x: x.is_superuser)
async def _(session: CommandSession):
    await session.send(get_message(ic.__plugin_name__, 'restarting'))
    # await session.send("正在重启 uwu")
    try:
        subprocess.Popen(['python', './bot.py'])
        if config.DEBUG:
            await session.send("[DEBUG] 已启动新的 xmebot 进程啦, 正在退出原进程...")
        try:
            # os.kill(oldpid, signal.SIGTERM)
            os._exit(0)
        except Exception as ex:
            await session.send(get_message(ic.__plugin_name__, 'restart_failed_kill').format(ex=ex))
            # await session.send(f"无法退出原 xmebot 进程 xwx\n错误原因: {ex}")
            return
    except Exception as ex:
        await session.send(get_message(ic.__plugin_name__, 'restart_failed').format(ex=ex, traceback=ex.with_traceback()))
        # await session.send(f"重启失败 xwx\n错误原因: {ex}\ntraceback:\n{ex.with_traceback()}")
