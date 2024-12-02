import nonebot
from os import path
from xme.xmetools import color_manage as c
import os
from nonebot.log import logger
import bot_variables
import config
import bot_init

def load_plugins_list(*args: list[str, str]):
    for arg in args:
        nonebot.load_plugins(arg[0], arg[1])

if __name__ == '__main__':
    bot_init.saving_log(logger)
    nonebot.init(config)
    load_plugins_list(
        [path.join(path.dirname(__file__), 'xme', 'plugins', 'commands'), 'xme.plugins.commands'],
        [path.join(path.dirname(__file__), 'xme', 'plugins', 'event_parsers'), 'xme.plugins.event_parsers'],
        [path.join(path.dirname(__file__), 'xme', 'plugins', 'server_app'), 'xme.plugins.server_app'],
        [path.join(path.dirname(__file__), 'xme', 'plugins', 'schedulers'), 'xme.plugins.schedulers'],
        # [path.join(path.dirname(__file__), 'xme', 'plugins', 'manual'), 'xme.plugins.manual'],
    )

    bot_init.bot_init()
    bot_variables.currentpid = os.getpid()
    print(c.gradient_text("#dda3f8","#66afff" ,text=f"当前 bot 运行进程 PID：{bot_variables.currentpid}"))
    nonebot.run()