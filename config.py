from nonebot.default_config import *
import character
from datetime import timedelta
import keys

# SUPERUSERS = character.get_item('config', 'super_users', default={1795886524})
SUPERUSERS = {1795886524}
COMMAND_START = ['/', '.', '。']
# ACCESS_TOKEN = keys.ACCESS_TOKEN
HOST = '0.0.0.0'
PORT = 18980
DEFAULT_VALIDATION_FAILURE_EXPRESSION = character.get_message('config', 'default_validation_failure_expression')
# DEFAULT_VALIDATION_FAILURE_EXPRESSION = '发送内容格式出错啦 xwx，可以检查一下输入或问问 179 哦'
SESSION_EXPIRE_TIMEOUT = timedelta(minutes=30)
SESSION_RUN_TIMEOUT = timedelta(minutes=60)
SESSION_RUNNING_EXPRESSION = character.get_message('config', 'busy')
# SESSION_RUNNING_EXPRESSION = None
# SESSION_RUNNING_EXPRESSION = ""
DEFAULT_COMMAND_PERMISSION = lambda s: True

# 用户自定义 config
SELF_ID = 3961418307
# 测试群
GROUPS_WHITELIST = [
    727949269,
    927322136
]
ANTI_MESSAGEBURST_GROUP = [
    905122019,
    727949269,
    927322136
]

# 视奸
PEEK_GROUP = [
    727949269,
    913581215
]

NICKNAME = character.get_character_item('bot_info', 'nickname', default=['XME', 'xme'])
VERSION = '0.8.1-beta'

USER_PATH = "./data/users.json"
BOT_SETTINGS_PATH = "./data/_botsettings.json"
DEBUG = False