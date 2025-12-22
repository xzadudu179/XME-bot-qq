import json
import os
from nonebot.log import logger
import nonebot
from logging.handlers import TimedRotatingFileHandler
import logging
import traceback
from xme.xmetools import colortools as c
from xme.xmetools.cmdtools import get_cmd_by_alias
from xme.xmetools.texttools import lazy_pinyin
from datetime import datetime
from xme.plugins.commands.xme_user import get_userhelp
import config

WIFE_INFO = {
}
TIME_LIMIT_INFO = {

}
USAGE_STATS = {
    "start_time": datetime.now().strftime("%Y年%m月%d日 %H:%M:%S"),
    "datas": [] # datas 字典列表, key 为群号
}
# DRIFT_BOTTLES_INFO = {
#     "max_index": 0,
#     "bottles": [
#     ]
# }

BOT_VARS = {
    "lottery_get_coins": 0,
    "lottery_lose_coins": 0
}

USERS = {
    "users": {}
}

BOT_SETTINGS = {
    "announcement": "",
    "latest_update": [],
    "locations": {
    },
    "seek_enable_groups": [],
    "deburst_groups": [
    ],
    "schtime_groups": []
}

def gen_doc_md():
    plugins = list(filter(lambda p: p.name, nonebot.get_loaded_plugins()))
    plugins.sort(key=lambda p: lazy_pinyin(p.name))
    # print([p.name for p in plugins])
    print("正在生成文档文件")
    usages = []
    for pl in plugins:
        try:
            usage = str(pl.usage).replace("/////OUTER/////", "")
            pl_type = usage.split("]")[0].split("[")[1]
            if pl_type == "指令":
                # print(pl.name, "是指令")
                md_usage = parse_command_doc(usage)
            elif pl.name.lower() in "xme 宇宙":
                md_usage = parse_user_doc(usage)
            elif pl_type == "插件":
                # print(pl.name, "是插件")
                # print(pl.usage)
                md_usage = parse_plugin_doc(usage)
            else:
                # print(pl.name, "是特殊插件，不处理")
                ...
            usages.append(md_usage)
        except Exception as ex:
            print("处理", pl.name, "插件出错:", ex)
            traceback.print_exc()
            continue
    with open("docs.md", 'w', encoding='utf-8') as file:
        file.write("\n\n".join(usages))

def parse_command_doc(doc_str, header_level=3):
    header = "#" * header_level + " " + doc_str.split("\n")[0]
    desc = "- **作用**\n\n  " + "\n  ".join((doc_str.split("作用：")[1].split("\n##用法##：")[0]).split("\n"))
    usage = "- **用法**\n\n``` Text\n" + (doc_str.split("##用法##：")[1].split("\n权限/可用范围：")[0]).strip() + "\n```"
    perms = "- **权限/可用范围**\n\n  " + doc_str.split("\n权限/可用范围：")[1].split("\n别名：")[0]
    alias = "- **别名**\n\n  " + "、 ".join([f"`{item}`" for item in doc_str.split("别名：")[1].split("\n########")[0].split(", ")])
    return "\n\n".join([header, desc, usage, perms, alias]) + "\n\n---"

def parse_user_doc(doc_str):
    header = "### " + doc_str.split("\n")[0]
    desc = "- **作用**\n\n  " + "\n  ".join((doc_str.split("作用：")[1].split("\n##内容##：")[0]).split("\n"))
    content = "- **指令列表：**\n\n"
    cmds = [item.strip().split(" ")[0].replace(":", "") for item in doc_str.split("##内容##：")[1].split("##所有指令用法##：")[0].split("\n") if item]
    md_cmds = []
    for cmd in cmds:
        cmd_info = parse_command_doc(get_userhelp(cmd), 4)
        md_cmds.append("\n  ".join(cmd_info.split("\n")))
    return f'{header}\n\n{desc}\n\n{content}  ' + "\n  ".join(md_cmds)


def parse_plugin_doc(doc_str):
    header = "### " + doc_str.split("\n")[0]
    desc = "- **作用**\n\n  " + "\n  ".join((doc_str.split("作用：")[1].split("\n##内容##：")[0]).split("\n"))
    content = "- **指令列表：**\n\n  "
    cmds = {item.strip().split(" ")[0].replace(":", ""): item.strip().split(": ")[1] for item in doc_str.split("##内容##：")[1].split("##所有指令用法##：")[0].split("\n") if item}
    usages = {item.strip()[1:].split(" ")[0].replace(":", ""): item.strip() for item in doc_str.split("##所有指令用法##：")[1].split("##权限/可用范围##：")[0].split("\n") if item}
    perms = {item.strip().split(" ")[0].replace(":", ""): item.split(": ")[1].split(" & ") for item in doc_str.split("##权限/可用范围##：")[1].split("##别名##：")[0].split("\n") if item}
    alias = {item.strip().split(" ")[0].replace(":", ""): item.split(": ")[1].split(", ") for item in doc_str.split("##别名##：")[1].split("\n########")[0].split("\n") if item}
    # print(alias)
    md_cmds = []
    for cmd, u in cmds.items():
        perm_lines = "\n    ".join(f"{i}. **{perm}**" for i, perm in enumerate(perms[cmd]))
        md_cmds.append(f'  #### {cmd}\n\n  - **作用**\n\n    {u}\n\n  - **用法**\n\n  ```Text\n  {usages[cmd]}\n  ```\n\n  - **权限/可用范围**\n\n    {perm_lines}\n\n  - **别名**\n\n    {"、 ".join([f"`{a}`" for a in alias[cmd]])}。\n\n  ---\n')
    return f'{header}\n\n{desc}\n\n{content}' + "\n".join(md_cmds)

def parse_special_doc(doc_str):
    ...

def init_json(path, data):
    if os.path.exists(path): return
    logger.warning(f"不存在 {path}, 正在重新创建")
    with open(path, 'w', encoding='utf-8') as file:
        file.write(json.dumps(data, indent=4, ensure_ascii=False))

def create_folder_if_not_exists(*paths):
    for path in paths:
        if os.path.exists(path): continue
        logger.info(f"创建 {path} 文件夹")
        os.mkdir(path)

def bot_init():
    create_folder_if_not_exists("./logs", "./data", "./data/xme", "./data/temp")
    # 老婆数据
    wife_path = "./data/wife.json"
    init_json(wife_path, WIFE_INFO)

    # botinfo
    # botinfo_path = f'./data/_botinfo.json'
    # init_json(botinfo_path, BASIC_INFO)

    # botsettings
    botsettings_path = "./data/_botsettings.json"
    init_json(botsettings_path, BOT_SETTINGS)

    # bottles_path = "./data/drift_bottles.json"
    # init_json(bottles_path, DRIFT_BOTTLES_INFO)

    usage_path = "./data/usage_stats.json"
    init_json(usage_path, USAGE_STATS)

    time_limit_path = "./data/time_limit_usage.json"
    init_json(time_limit_path, TIME_LIMIT_INFO)

    time_limit_path = "./data/bot_vars.json"
    init_json(time_limit_path, BOT_VARS)

    # init_json(config.USER_PATH, USERS)

    gen_doc_md()


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


