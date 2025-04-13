from xme.xmetools.timetools import *
from xme.plugins.commands.drift_bottle import __plugin_name__
from xme.xmetools.cmdtools import send_cmd, get_cmd_by_alias
from xme.xmetools.timetools import TimeUnit
from character import get_message
from xme.xmetools import randtools
from xme.plugins.commands.xme_user.classes import user
import random
random.seed()
from nonebot import on_command, CommandSession
from xme.xmetools.msgtools import send_session_msg
import config

seek_alias = ["寻宝"]
command_name = "seek"
TIMES_LIMIT = 1

@on_command(command_name, aliases=seek_alias, only_to_me=False)
@user.using_user(save_data=True)
@user.limit(command_name, 5, get_message("plugins", __plugin_name__, command_name, 'limited', ), TIMES_LIMIT, TimeUnit.MINUTE)
async def _(session: CommandSession):
    ...