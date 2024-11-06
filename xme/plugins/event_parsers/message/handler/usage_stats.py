from xme.xmetools.command_tools import find_command_by_args
from nonebot.session import BaseSession
from nonebot import NoneBot

def usage_stats(session: BaseSession, bot: NoneBot):
    if cmd:=find_command_by_args(session['raw_message'].strip()) == False: return
