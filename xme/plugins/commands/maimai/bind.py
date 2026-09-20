"""mai bind 子命令：绑定或查看水鱼成绩导入 Token（限私聊）。

Token 既是读取成绩的凭证（GET /player/records），也是将来同步成绩的写入凭证，
因此只允许在私聊里发送，并做限频。
"""

import re

from character import get_message
from nonebot import CommandSession, SenderRoles
from nonebot.log import logger
from xme.plugins.commands.maimai import __plugin_name__
from xme.plugins.commands.xme_user.classes.user import (
    User,
    detect_limit,
    limit_count_tick,
)
from xme.xmetools.timetools import TimeUnit

from . import api, binding, constants

cmd_name = constants.CMD_BIND
alias = constants.BIND_ALIAS
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
    """处理 Token 绑定（限私聊）：先验证有效再保存，返回拼好的回复文案。"""
    sender = await SenderRoles.create(session.bot, session.event)
    if not sender.is_privatechat:
        return get_message("plugins", __plugin_name__, 'private_only')
    token = _clean_token(arg)
    if not token:
        current = binding.get_binding(user)
        if current[binding.TOKEN_KEY]:
            return get_message(
                "plugins", __plugin_name__, 'current_binding',
                token=binding.mask_token(current[binding.TOKEN_KEY]),
            )
        return get_message("plugins", __plugin_name__, 'bind_usage')
    if detect_limit(
        user=user,
        name=constants.SYNC_LIMIT_NAME,
        interval=constants.SYNC_LIMIT_INTERVAL,
        count_limit=constants.SYNC_LIMIT_COUNT,
        unit=TimeUnit.MINUTE,
    ):
        return get_message("plugins", __plugin_name__, 'sync_limited')
    # 发起验证即计数，避免拿无效 Token 反复刷水鱼接口
    limit_count_tick(user, constants.SYNC_LIMIT_NAME)
    try:
        payload = await api.fetch_records_payload(token)
    except api.MaimaiAPIError as ex:
        logger.warning(f"水鱼 Token 验证失败: {ex}")
        user.save()
        return get_message("plugins", __plugin_name__, 'update_invalid')
    binding.set_token(user, token)
    user.save()
    return get_message(
        "plugins", __plugin_name__, 'update_success',
        token=binding.mask_token(token), count=len(payload.get("records") or []),
    )
