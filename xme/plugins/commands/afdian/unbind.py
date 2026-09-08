
from aiocqhttp import ActionFailed
from character import get_message
from nonebot import CommandSession
from nonebot.log import logger

from xme.plugins.commands.afdian import __plugin_name__
from xme.plugins.commands.afdian.constants import CMD_UNBIND
from xme.plugins.commands.xme_user.classes.user import using_user, User
from xme.xmetools.afdiantools import AFDIAN_CLIENT
from xme.xmetools.afdiantools.constants import STATE_TTL

cmd_name = CMD_UNBIND
alias = ['解除绑定']
usage = {
    "name": cmd_name,
    "desc": get_message("plugins", __plugin_name__, cmd_name, 'desc'),
    "introduction": get_message("plugins", __plugin_name__, cmd_name, 'introduction'),
    "usage": '',
    "permissions": [],
    "alias": alias
}

@using_user(save_data=False)
async def handle(session: CommandSession, user: User, arg: str) -> str:
    if user.afdian_id is None or not user.afdian_id:
        return get_message("plugins", __plugin_name__, cmd_name, 'no_afdian_id')
    user.afdian_id = ""
    user.update("afdian_id")
    return get_message("plugins", __plugin_name__, cmd_name, 'success')
