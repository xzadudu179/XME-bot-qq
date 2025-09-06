from xme.xmetools.timetools import *
from xme.plugins.commands.drift_bottle import __plugin_name__
from xme.xmetools.cmdtools import send_cmd, get_cmd_by_alias
from xme.xmetools.timetools import TimeUnit
from character import get_message
from asyncio import sleep
from xme.plugins.commands.xme_user.classes import user
import random
random.seed()
from nonebot import on_command, CommandSession
from xme.xmetools.msgtools import send_session_msg

# 寻宝每一步
class SeekStep:
    def __init__(self, fail_prob, message, event, **kwargs):
        self.fail_prob = fail_prob
        self.message = message
        self.event = event
        self.event_kwargs = kwargs

    def parse_step(event, **kwargs):
        result = event()



seek_alias = ["寻宝", 'sk']
command_name = "seek"

seek_state = {
    "is_seeking": False
}

TIMES_LIMIT = 1

@on_command(command_name, aliases=seek_alias, only_to_me=False)
@user.using_user(save_data=True)
@user.limit(command_name, 1, get_message("plugins", __plugin_name__, command_name, 'limited', ), TIMES_LIMIT, TimeUnit.HOUR)
async def _(session: CommandSession, u: user.User):
    ...
    await sleep(10)