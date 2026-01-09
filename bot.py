#   ____________________________________________________________________________________________________
#  /   ______     ______     ______   ______     ______     __            ______     ______     ______  \
# /   /\  __ \   /\  ___\   /\__  _\ /\  == \   /\  __ \   /\ \          /\  ___\   /\  __ \   /\__  _\  \
# \   \ \  __ \  \ \___  \  \/_/\ \/ \ \  __<   \ \  __ \  \ \ \____     \ \ \____  \ \  __ \  \/_/\ \/   \
#  \   \ \_\ \_\  \/\_____\    \ \_\  \ \_\ \_\  \ \_\ \_\  \ \_____\     \ \_____\  \ \_\ \_\    \ \_\    \
#   \   \/_/\/_/   \/_____/     \/_/   \/_/ /_/   \/_/\/_/   \/_____/      \/_____/   \/_/\/_/     \/_/    /
#    \____________________________________________________________________________________________________/

import nonebot
from os import path
from xme.xmetools import colortools as c
# from xme.xmetools import jsontools
# from xme.plugins.commands.xme_user.classes.user import User, try_load
import random
random.seed()
import os
from nonebot.log import logger
import bot_variables
import config
import bot_init
# from xme.xmetools.msgtools import send_to_superusers
import asyncio
# from config import BOT_SETTINGS_PATH

# def handle_exception(loop, context):
#     exception = context.get("exception")
#     if exception:
#         print("[异常]")
#         trace = traceback.format_exception(type(exception), exception, exception.__traceback__)
#         trace_str = "\n".join(trace)
#         except_msg = f'XME-BOT 运行出现异常：{context.get("message")}\n{trace_str}'
#         print(except_msg)
#         loop.create_task(send_to_superusers(nonebot.get_bot(), except_msg))
#     else:
#         # 如果 context 没有 exception，通常只有字符串 message
#         msg = context.get("message")
#         except_msg = f'XME-BOT 运行出现异常：{msg}'
#         print(except_msg)
#         loop.create_task(send_to_superusers(nonebot.get_bot(), except_msg))

def load_plugins_list(*args: list[str, str]):
    for arg in args:
        nonebot.load_plugins(arg[0], arg[1])

if __name__ == '__main__':
    random.seed()
    print("正在启动...")
    # TODO: 每日备份 data/ 文件
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
    # 初始化银河系地图
    # locations = jsontools.read_from_path(BOT_SETTINGS_PATH)["locations"]
    # GalaxyMap()
    bot_variables.currentpid = os.getpid()
    print(c.gradient_text("#dda3f8", "#66afff", text=f"当前 bot 运行进程 PID：{bot_variables.currentpid}"))
    loop = asyncio.get_event_loop()
    # loop.set_exception_handler(handle_exception)
    nonebot.run(loop=loop)