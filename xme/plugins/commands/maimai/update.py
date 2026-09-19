"""mai update 子命令：绑定并验证水鱼成绩导入 Token。"""

import re

from character import get_message
from nonebot import CommandSession
from nonebot.log import logger
from xme.plugins.commands.maimai import __plugin_name__
from xme.plugins.commands.xme_user.classes.user import User

from . import api, binding, constants

cmd_name = constants.CMD_UPDATE
alias = constants.UPDATE_ALIAS
usage = {
    "name": cmd_name,
    "desc": get_message("plugins", __plugin_name__, cmd_name, 'desc'),
    "introduction": get_message("plugins", __plugin_name__, cmd_name, 'introduction'),
    "usage": '(成绩导入Token)',
    "permissions": [],
    "alias": alias,
}

_CQ_PATTERN = re.compile(r"\[CQ:[^\]]*\]")


def _clean_token(arg: str) -> str:
    """去掉消息段与首尾空白后得到纯 Token。"""
    return _CQ_PATTERN.sub("", arg).strip()


async def handle(session: CommandSession, user: User, arg: str) -> str:
    """处理导入 Token 绑定：先验证有效再保存，返回拼好的回复文案。"""
    token = _clean_token(arg)
    if not token:
        return get_message("plugins", __plugin_name__, 'update_usage')
    try:
        records = await api.fetch_records(token)
    except api.MaimaiAPIError as ex:
        logger.warning(f"导入 Token 验证失败: {ex}")
        return get_message("plugins", __plugin_name__, 'update_invalid')
    binding.set_token(user, token)
    user.save()
    return get_message(
        "plugins", __plugin_name__, 'update_success',
        token=binding.mask_token(token), count=len(records),
    )
