"""mai unbind 子命令：清除水鱼用户名与成绩导入 Token 绑定。"""

from character import get_message
from nonebot import CommandSession
from xme.plugins.commands.maimai import __plugin_name__
from xme.plugins.commands.xme_user.classes.user import User

from . import binding, constants

cmd_name = constants.CMD_UNBIND
alias = constants.UNBIND_ALIAS
usage = {
    "name": cmd_name,
    "desc": get_message("plugins", __plugin_name__, cmd_name, 'desc'),
    "introduction": get_message("plugins", __plugin_name__, cmd_name, 'introduction'),
    "usage": '',
    "permissions": [],
    "alias": alias,
}


async def handle(session: CommandSession, user: User, arg: str) -> str:
    """处理解绑请求，返回拼好的回复文案。"""
    if not binding.clear_binding(user):
        return get_message("plugins", __plugin_name__, 'unbind_nothing')
    user.save()
    return get_message("plugins", __plugin_name__, 'unbind_success')
