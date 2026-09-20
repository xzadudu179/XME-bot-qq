"""mai update 子命令：暂时停用（Token 绑定能力已并入 mai bind）。

保留命令注册，让使用者输入时能看到明确提示，而不是「没有这个操作」。
"""

from character import get_message
from nonebot import CommandSession
from xme.plugins.commands.maimai import __plugin_name__
from xme.plugins.commands.xme_user.classes.user import User

from . import constants

cmd_name = constants.CMD_UPDATE
alias = constants.UPDATE_ALIAS
usage = {
    "name": cmd_name,
    "desc": get_message("plugins", __plugin_name__, cmd_name, 'desc'),
    "introduction": get_message("plugins", __plugin_name__, cmd_name, 'introduction'),
    "usage": '（暂时停用）',
    "permissions": [],
    "alias": alias,
}


async def handle(session: CommandSession, user: User, arg: str) -> str:
    """update 暂时停用，返回提示文案。"""
    return get_message("plugins", __plugin_name__, 'update_disabled')
