import nonebot
from os import path
from xme.xmetools import color_manage as c
import os
import bot_variables
import config
import bot_init

if __name__ == '__main__':
    nonebot.init(config)
    nonebot.load_plugins(
        path.join(path.dirname(__file__), 'xme', 'plugins'),
        'xme.plugins'
    )
    bot_init.bot_init()
    bot_variables.currentpid = os.getpid()
    print(c.gradient_text("#dda3f8","#66afff" ,text=f"当前 bot 运行进程 PID：{bot_variables.currentpid}"))
    nonebot.run()