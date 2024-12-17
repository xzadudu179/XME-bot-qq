import os
import sys

import nonebot

import config

nonebot.init(config)
bot = nonebot.get_bot()
app = bot.asgi

if __name__ == '__main__':
    bot.run()