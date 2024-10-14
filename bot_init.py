import json
import os
from nonebot.log import logger
import nonebot
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

DRIFT_BOTTLES_INFO = {
    "bottles": [
    ]
}

BOT_SETTINGS = {
    "prevent_recall": {}
}

def init_json(path, data):
    if not os.path.exists(path):
        logger.warning(f"不存在 {path}, 正在重新创建")
        with open(path, 'w', encoding='utf-8') as file:
            file.write(json.dumps(data, indent=4, ensure_ascii=False))

def bot_init():
    # 老婆数据
    wife_path = "./data/wife.json"
    init_json(wife_path, WIFE_INFO)

    # botinfo
    botinfo_path = f'./data/botinfo.json'
    init_json(botinfo_path, BASIC_INFO)

    # botsettings
    botsettings_path = "./data/botsettings.json"
    init_json(botsettings_path, BOT_SETTINGS)

    bottles_path = "./data/drift_bottles.json"
    init_json(bottles_path, DRIFT_BOTTLES_INFO)


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


