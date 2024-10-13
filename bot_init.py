import json
import os
from nonebot.log import logger
import logging
from xme.xmetools import color_manage as c
from logging.handlers import RotatingFileHandler
from datetime import datetime

WIFE_INFO = {
}
BASIC_INFO = {
    "name": "默认机器人",
    "author": "unknown",
    "author_qq": "0",
    "desc": "默认机器人介绍",
    "version": "v0.1.0"
}

BOT_SETTINGS = {
        "prevent_recall": {}
}
def bot_init():
    # 老婆数据
    wife_path = "./data/wife.json"
    if not os.path.exists(wife_path):
        logger.warning("不存在 wife.json, 正在重新创建")
        with open(wife_path, 'w', encoding='utf-8') as file:
            file.write(json.dumps(WIFE_INFO, indent=4, ensure_ascii=False))

    # botinfo
    botinfo_path = f'./data/botinfo.json'
    if not os.path.exists(botinfo_path):
        logger.warning("不存在 botinfo.json, 正在重新创建")
        with open(botinfo_path, 'w', encoding='utf-8') as file:
            file.write(json.dumps(BASIC_INFO, indent=4, ensure_ascii=False))

    # botsettings
    botsettings_path = "./data/botsettings.json"
    if not os.path.exists(botsettings_path):
        logger.warning("不存在 botsettings.json, 正在重新创建")
        with open(botsettings_path, 'w', encoding='utf-8') as file:
            file.write(json.dumps(BOT_SETTINGS, indent=4, ensure_ascii=False))

def saving_log(logger: logging.Logger, filepath=f'./logs/{datetime.now().strftime(format="%Y-%m-%d")}_nonebot.log'):
    file_handler = RotatingFileHandler(filepath, maxBytes=15 * 1024 * 1024, backupCount=10, encoding='utf-8')
    # 设置日志的格式
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(formatter)
    # 添加文件处理器到 logger
    logger.addHandler(file_handler)
    print(c.gradient_text("#dda3f8","#66afff" ,text=f"当前日志将会被记录到文件 \"{filepath}\" 中。"))
