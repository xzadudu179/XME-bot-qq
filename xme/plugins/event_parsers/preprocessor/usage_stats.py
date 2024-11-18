from xme.xmetools.command_tools import get_cmd_by_alias
from nonebot.session import BaseSession
from nonebot import NoneBot

def usage_stats(session: BaseSession, bot: NoneBot):
    if cmd:=get_cmd_by_alias(session['raw_message'].strip()) == False: return
