"""afd login 子命令：生成爱发电 OAuth 授权链接并绑定 afdian_id。"""
from aiocqhttp import ActionFailed
from character import get_message
from nonebot import CommandSession
from nonebot.log import logger

from xme.plugins.commands.afdian import __plugin_name__
from xme.plugins.commands.afdian.constants import CMD_LOGIN
from xme.xmetools.afdiantools import AFDIAN_CLIENT
from xme.xmetools.afdiantools.constants import STATE_TTL

cmd_name = CMD_LOGIN
alias = ['绑定']
usage = {
    "name": cmd_name,
    "desc": get_message("plugins", __plugin_name__, cmd_name, 'desc'),
    "introduction": get_message("plugins", __plugin_name__, cmd_name, 'introduction'),
    "usage": '',
    "permissions": [],
    "alias": alias
}


async def handle(session: CommandSession, arg: str) -> str:
    """签发带 state 的授权链接，优先私聊发送，失败时降级到当前会话。

    state 为含 qq 与过期时间的 JWT：只有发起绑定的人的 qq 会被写入
    回调绑定流程，但链接本身可能被他人点击完成「替别人授权」，
    因此优先私聊发送并提醒不要转发。
    """
    qq = session.event.user_id
    state = AFDIAN_CLIENT.make_login_state(qq)
    url = AFDIAN_CLIENT.build_authorize_url(state)
    expire_minutes = STATE_TTL // 60
    try:
        await session.bot.send_private_msg(
            user_id=qq,
            message=get_message(
                "plugins", __plugin_name__, cmd_name, 'private_msg',
                url=url, expire=expire_minutes,
            ),
        )
    except ActionFailed as e:
        logger.warning(f"afd {CMD_LOGIN} 私聊发送失败。{e}")
        # return get_message(
        #     "plugins", __plugin_name__, cmd_name, 'group_fallback',
        #     url=url, expire=expire_minutes,
        # )
        expire_minutes = expire_minutes * 3
        return get_message(
            "plugins", __plugin_name__, cmd_name, 'send_failed',
        )
    return get_message("plugins", __plugin_name__, cmd_name, 'sent_private')
