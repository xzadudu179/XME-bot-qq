"""mai bind 子命令：绑定或查看水鱼查分器用户名。"""

import re

from character import get_message
from nonebot import CommandSession
from nonebot.log import logger
from xme.plugins.commands.maimai import __plugin_name__
from xme.plugins.commands.xme_user.classes.user import User

from . import api, binding, constants

cmd_name = constants.CMD_BIND
alias = constants.BIND_ALIAS
usage = {
    "name": cmd_name,
    "desc": get_message("plugins", __plugin_name__, cmd_name, 'desc'),
    "introduction": get_message("plugins", __plugin_name__, cmd_name, 'introduction'),
    "usage": '(水鱼用户名)',
    "permissions": [],
    "alias": alias,
}

_CQ_PATTERN = re.compile(r"\[CQ:[^\]]*\]")


def _clean_username(arg: str) -> str:
    """去掉消息段与首尾空白后得到纯用户名。"""
    return _CQ_PATTERN.sub("", arg).strip()


async def handle(session: CommandSession, user: User, arg: str) -> str:
    """处理绑定请求，返回拼好的回复文案。"""
    username = _clean_username(arg)
    current = binding.get_binding(user)
    if not username:
        if current[binding.USERNAME_KEY]:
            return get_message(
                "plugins", __plugin_name__, 'current_binding',
                username=current[binding.USERNAME_KEY],
                token=binding.mask_token(current[binding.TOKEN_KEY]),
            )
        return get_message("plugins", __plugin_name__, 'bind_usage')
    if current[binding.USERNAME_KEY] == username:
        return get_message("plugins", __plugin_name__, 'bind_duplicate', username=username)
    # 先向水鱼确认用户名真实存在（隐私用户也算存在），避免绑到不存在的名字
    try:
        if not await api.username_exists(username):
            return get_message(
                "plugins", __plugin_name__, 'bind_not_found', username=username)
    except api.MaimaiAPIError as ex:
        logger.warning(f"绑定校验请求失败: {ex}")
        return get_message("plugins", __plugin_name__, 'api_error', ex=ex.message)
    binding.set_username(user, username)
    user.save()
    return get_message("plugins", __plugin_name__, 'bind_success', username=username)
