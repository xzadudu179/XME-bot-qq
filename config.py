from nonebot.default_config import *
from datetime import timedelta

SUPERUSERS = {1795886524}
COMMAND_START = ['/', '!', '！', '.', '。']
HOST = '0.0.0.0'
PORT = 17980
NICKNAME = {'XME', 'xme'}
DEFAULT_VALIDATION_FAILURE_EXPRESSION = '发送内容格式出错啦 xwx，可以检查一下输入或问问 179 哦'
DEBUG = False
SESSION_EXPIRE_TIMEOUT = timedelta(minutes=2)
SESSION_RUN_TIMEOUT = timedelta(seconds=60)
SESSION_RUNNING_EXPRESSION = '我还有指令未处理 uwu'
DEFAULT_COMMAND_PERMISSION = lambda s: s.is_groupchat

# 用户自定义 config
GROUPS_WHITELIST = [
    727949269
]
# 报时
SCHEDULER_GROUP = [
    727949269,
    913581215,
    164072032,
]