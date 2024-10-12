import json
import os
from nonebot.log import logger

WIFE_INFO = {
    "days": 0,
    "groups": {}
}
BASIC_INFO = {
    "name": "默认机器人",
    "author": "unknown",
    "author_qq": "0",
    "desc": "默认机器人介绍"
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
