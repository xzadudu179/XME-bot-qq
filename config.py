from nonebot.default_config import *  # noqa: F403
import character
from datetime import timedelta
import keys

# SUPERUSERS = character.get_item('config', 'super_users', default={1795886524})
SUPERUSERS = {1795886524}
COMMAND_START = ['/', '.', '。', '／']
ACCESS_TOKEN = keys.ACCESS_TOKEN
HOST = '0.0.0.0'
PORT = 18980
DEFAULT_VALIDATION_FAILURE_EXPRESSION = character.get_message('config', 'default_validation_failure_expression')
# DEFAULT_VALIDATION_FAILURE_EXPRESSION = '发送内容格式出错啦 xwx，可以检查一下输入或问问 179 哦'
SESSION_EXPIRE_TIMEOUT = timedelta(minutes=30)
SESSION_RUN_TIMEOUT = timedelta(minutes=500)
SESSION_RUNNING_EXPRESSION = character.get_message('config', 'busy')
# SESSION_RUNNING_EXPRESSION = None
# SESSION_RUNNING_EXPRESSION = ""
DEFAULT_COMMAND_PERMISSION = lambda _: True  # noqa: E731
# 用户自定义 config
SELF_ID = 3893933165
# 接收自身消息上报（post_type 为 message_sent 的扩展事件）。
# 需要在协议端同时开启对应开关（NapCat / SnowLuma / LLOneBot 的 reportSelfMessage），
# 关掉这里可让 bot 完全无视自身消息（用于回滚排查）
REPORT_SELF_MESSAGE = True
# 测试群
GROUPS_WHITELIST = [
    727949269,
    1094916675,
    927322136,
    739980056
]
# 反刷屏群，暂无作用
ANTI_MESSAGEBURST_GROUP = [
    905122019,
    1094916675,
    727949269,
    927322136
]

# 群最低成员要求（低于该值 bot 进群会自动退群）
MIN_GROUP_MEMBER_COUNT = 35

# 视奸
PEEK_GROUP = [
    727949269,
    913581215,
    1094916675
]

NICKNAME = character.get_character_item('bot_info', 'nickname', default=['XME', 'xme'])
VERSION = '1.15.3'

USER_PATH = "./data/users.json"
BOT_SETTINGS_PATH = "./data/_botsettings.json"
IMAGE_TEMP_PATH = "./data/images/temp/"
CONTAINER_BOT_PATH = "/xmebot"
# 舞萌机台协议工具（独立 Go 项目 mai-arcade）的二进制路径，供 /mai update 调用
MAI_ARCADE_PATH = "./bin/mai-arcade"
DEBUG = False

USE_PROXY = True
HTTP_PORT = 7890