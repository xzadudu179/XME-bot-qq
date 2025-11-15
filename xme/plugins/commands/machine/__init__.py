from nonebot import on_command, CommandSession
from xme.xmetools.doctools import CommandDoc
from xme.xmetools.jsontools import read_from_path
from xme.plugins.commands.xme_user.classes.user import User, using_user
from xme.xmetools.timetools import curr_days
import random
random.seed()
from xme.xmetools.msgtools import send_session_msg, aget_session_msg
from character import get_message

alias = ['magic', 'mag', '神秘机器']
__plugin_name__ = 'machine'
__plugin_usage__ = str(CommandDoc(
    name=__plugin_name__,
    desc=get_message("plugins", __plugin_name__, "desc"),
    introduction=get_message("plugins", __plugin_name__, "introduction"),
    usage=f'',
    permissions=["无"],
    alias=alias
))

@on_command(__plugin_name__, aliases=alias, only_to_me=False, permission=lambda _: True)
@using_user(True)
async def _(session: CommandSession, u: User):
    ...