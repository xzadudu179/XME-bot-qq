"""afd reward 子命令：结算并领取发电奖励（自动发放之外的手动补领入口）。"""
from character import get_message
from nonebot import CommandSession

from xme.plugins.commands.afdian import __plugin_name__
from xme.plugins.commands.afdian.constants import CMD_REWARD
from xme.plugins.commands.afdian.rewards import settle_rewards
from xme.plugins.commands.xme_user.classes.user import try_load

cmd_name = CMD_REWARD
alias = ['奖励', '领奖']
usage = {
    "name": cmd_name,
    "desc": get_message("plugins", __plugin_name__, cmd_name, 'desc'),
    "introduction": get_message("plugins", __plugin_name__, cmd_name, 'introduction'),
    "usage": '',
    "permissions": [],
    "alias": alias
}


async def handle(session: CommandSession, arg: str) -> str:
    """结算发送者的发电奖励：有则发放并展示，无则展示累计与下一档进度。"""
    user = try_load(session.event.user_id)
    if not user.afdian_id:
        return get_message("plugins", __plugin_name__, cmd_name, 'not_bound')
    result = await settle_rewards(user, force=True)
    if result.granted:
        return get_message(
            "plugins", __plugin_name__, cmd_name, 'success',
            rewards="\n".join(result.granted),
            total=f"{result.total_amount:.2f}",
            next_hints="\n".join(result.next_hints) or get_message(
                "plugins", __plugin_name__, cmd_name, 'no_more'),
        )
    return get_message(
        "plugins", __plugin_name__, cmd_name, 'nothing',
        total=f"{result.total_amount:.2f}",
        next_hints="\n".join(result.next_hints) or get_message(
            "plugins", __plugin_name__, cmd_name, 'no_more'),
    )
