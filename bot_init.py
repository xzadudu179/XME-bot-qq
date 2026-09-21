import json
import os
from pathlib import Path
# from xme.xmetools.debugtools import debug_msg
from nonebot.log import logger
import nonebot
from logging.handlers import TimedRotatingFileHandler
import logging
import traceback
from config import BOT_SETTINGS_PATH
from xme.xmetools import colortools as c
from xme.xmetools import logtools
# from xme.xmetools.cmdtools import get_cmd_by_alias
from xme.xmetools.doctools import DOC_MD_PATH, build_docs_md, doc_to_markdown
from cloudflared_sync import OK_STATUSES, sync_cloudflared_config
from datetime import datetime

from xme.xmetools.reqtools import fetch_data_post
from xme.xmetools.texttools import hash_text
# import config

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
    "schtime_groups": [],
    "ignore_member_count_groups": [],
}

hook_need_update = False
def gen_doc_md():
    """生成 docs.md：把各插件的 __plugin_usage__（Doc 对象）渲染成指令文档。

    文档同时是 /docs 页面（server_app.docs）与 AI 助手的系统提示词来源，排序与分栏规则
    都在 doctools.build_docs_md 里；某个插件字段写坏了只影响它自己，不阻塞其余文档。
    """
    global hook_need_update
    plugins = list(filter(lambda p: p.name, nonebot.get_loaded_plugins()))
    logger.info("正在生成文档文件")
    docs = []
    for pl in plugins:
        try:
            docs.append(doc_to_markdown(pl.usage))
        except Exception:
            logger.error("处理", pl.name, "插件出错:", traceback.format_exc())
            continue
    new_docs_text = build_docs_md(docs)
    new_docs = hash_text(new_docs_text)
    try:
        with open(DOC_MD_PATH, 'r', encoding='utf-8') as file:
            old_docs = hash_text(file.read())
    except OSError:
        old_docs = ""
    # 更新 hook
    hook_need_update = new_docs != old_docs
    if hook_need_update:
        logger.info("文档站需要重建")
    with open(DOC_MD_PATH, 'w', encoding='utf-8') as file:
        file.write(new_docs_text)

def is_hook_need_update():
    global hook_need_update
    return hook_need_update

def reset_hook():
    global hook_need_update
    hook_need_update = False

def init_json(path, data):
    if os.path.exists(path):
        return
    logger.warning(f"不存在 {path}, 正在重新创建")
    with open(path, 'w', encoding='utf-8') as file:
        file.write(json.dumps(data, indent=4, ensure_ascii=False))

def create_folder_if_not_exists(*paths):
    for path in paths:
        # if os.path.exists(path):
        #     continue
        logger.info(f"创建 {path} 文件夹")
        Path(path).mkdir(parents=True, exist_ok=True)
        # os.mkdir(path)

def bot_init():
    create_folder_if_not_exists("./logs", "./data", "./data/xme", "./data/temp", "./data/ai_historys")
    # Path("./data/ai_historys").mkdir(parents=True, exist_ok=True)
    # 老婆数据
    wife_path = "./data/wife.json"
    init_json(wife_path, WIFE_INFO)
    # botinfo
    # botinfo_path = f'./data/_botinfo.json'
    # init_json(botinfo_path, BASIC_INFO)

    # botsettings
    botsettings_path = BOT_SETTINGS_PATH
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

    sync_cloudflared_ingress()

    # 启动时显式检测并迁移所有数据库表结构（字段减少/增加自动重建表）
    init_all_databases()


def sync_cloudflared_ingress():
    """把仓库里的 cloudflared 配置同步到线上（deploy/cloudflared/config.yml 为唯一来源）。

    内容一致时不产生任何副作用；校验不通过或没授权只告警，不阻塞启动。
    """
    status, detail = sync_cloudflared_config()
    message = f"cloudflared 配置：{status.value}（{detail}）"
    if status in OK_STATUSES:
        logger.info(message)
    else:
        logger.warning(message)


def init_all_databases():
    """启动时检测所有数据库表的结构，与模型不一致则自动迁移（见 dbtools._ensure_table_schema）。

    用模型的最小实例推导字段；某张表检查失败不阻塞启动（首次保存时会再次自动检查）。
    """
    from xme.xmetools.dbtools import DATABASE
    from xme.plugins.commands.xme_user.classes.user import User
    from xme.xmetools.plugintools import PluginCallData
    from xme.plugins.commands.drift_bottle import DriftBottle

    # (模型类, 用于推导字段的最小实例构造参数)
    models = [
        (User, (0,)),
        (PluginCallData, (0, 0, 0, 0, 0, 0)),
        (DriftBottle, ()),
    ]
    checked = 0
    for cls, args in models:
        try:
            instance = cls(*args)
            DATABASE.create_class_table(instance)
            checked += 1
            logger.info(f"数据库表 {cls.get_table_name()} 结构检查完成")
        except Exception as ex:
            logger.warning(
                f"数据库模型 {cls.get_table_name()} 检查失败（不影响启动，首次保存时会自动重试）: {ex}"
            )
    logger.info(f"数据库启动检查完成：{checked}/{len(models)} 张表通过")


def colorize_console_log():
    """将 nonebot 默认控制台 handler 换成彩色 Formatter（文件日志不受影响）"""
    from nonebot.log import default_handler
    default_handler.setFormatter(logtools.ColoredFormatter(
        '[%(asctime)s %(name)s] %(levelname)s: %(message)s'))


def setup_lib_log():
    """接管 root logger 的库日志（aiocqhttp/Quart/APScheduler 等）

    心跳、定时任务例行执行等高频 INFO 行降级为 DEBUG 不再刷控制台，事件
    行紧凑上色显示；全部库日志落 ./logs/event/events.log（DEBUG 级，含降级行）；
    nonebot/send logger 关闭传播避免经 root 重复打印。需在 nonebot.init
    前调用，以抢占 Quart 懒加载的默认 stderr handler。
    """
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.addFilter(logtools.RoutineLogDemoteFilter(drop=True))
    console.setFormatter(logtools.EventLogFormatter(
        "[%(asctime)s] [%(levelname)s] %(message)s"))
    root.addHandler(console)

    events_path = './logs/event/events.log'
    os.makedirs(os.path.dirname(events_path), exist_ok=True)
    events_handler = TimedRotatingFileHandler(
        events_path, when="midnight", interval=1,
        backupCount=30, encoding="utf-8", delay=True)
    events_handler.suffix = "%Y-%m-%d"
    events_handler.setLevel(logging.INFO)
    events_handler.addFilter(logtools.RoutineLogDemoteFilter())
    events_handler.setFormatter(logging.Formatter(
        '[%(asctime)s] [%(levelname)s] %(message)s'))
    root.addHandler(events_handler)

    for name in ("nonebot", "send"):
        logging.getLogger(name).propagate = False
    print(c.gradient_text("#a8ffc5", "#66c7ff",
                          text=f"已接管库日志：事件将记录到 {events_path}"))


def saving_log(logger: logging.Logger, filepath='./logs/nonebot/nonebot.log'):
    # 设置日志的格式；backupCount 缺省 0 会永久保留每天的轮转文件（无界增长）
    # 本函数在 bot_init() 之前跑，日志目录得自己建（与 msgtools/watchdog 的做法一致）
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    log_handler = TimedRotatingFileHandler(filepath, when="midnight", interval=1,
                                           backupCount=120, encoding="utf-8")
    log_handler.suffix = "%Y-%m-%d"  # 按年-月-日格式保存日志文件
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    log_handler.setFormatter(formatter)
    # 添加文件处理器到 logger
    print(c.gradient_text("#a8ffc5","#66c7ff" ,text=f"当前日志将会被记录到文件 \"{filepath}\" 中。"))
    logger.addHandler(log_handler)


