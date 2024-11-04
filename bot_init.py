import json
import os
from nonebot.log import logger
from logging.handlers import TimedRotatingFileHandler
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
    "max_index": 0,
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

def create_folder_if_not_exists(*paths):
    for path in paths:
        if not os.path.exists(path):
            logger.info(f"创建 {path} 文件夹")
            os.mkdir(path)

def bot_init():
    create_folder_if_not_exists("./logs", "./data", "./data/xme")
    # 老婆数据
    wife_path = "./data/wife.json"
    init_json(wife_path, WIFE_INFO)

    # botinfo
    botinfo_path = f'./data/_botinfo.json'
    init_json(botinfo_path, BASIC_INFO)

    # botsettings
    botsettings_path = "./data/_botsettings.json"
    init_json(botsettings_path, BOT_SETTINGS)

    bottles_path = "./data/drift_bottles.json"
    init_json(bottles_path, DRIFT_BOTTLES_INFO)


def saving_log(logger: logging.Logger, filepath=f'./logs/nonebot.log'):
    # 设置日志的格式
    log_handler = TimedRotatingFileHandler(filepath, when="midnight", interval=1, encoding="utf-8")
    log_handler.suffix = "%Y-%m-%d"  # 按年-月-日格式保存日志文件
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    log_handler.setFormatter(formatter)
    # 添加文件处理器到 logger
    print(c.gradient_text("#dda3f8","#66afff" ,text=f"当前日志将会被记录到文件 \"{filepath}\" 中。"))
    logger.addHandler(log_handler)


