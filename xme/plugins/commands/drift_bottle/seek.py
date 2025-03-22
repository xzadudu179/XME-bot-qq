from xme.xmetools.timetools import *
from xme.plugins.commands.drift_bottle import __plugin_name__
from xme.xmetools.cmdtools import send_cmd, get_cmd_by_alias
from xme.xmetools import jsontools
from character import get_message
from xme.xmetools import randtools
import random
from nonebot import on_command, CommandSession
from xme.xmetools.msgtools import send_session_msg
import config

seek_alias = ["寻宝"]
command_name = "seek"

@on_command(command_name, aliases=seek_alias, only_to_me=False)
async def _(session: CommandSession):
    ...