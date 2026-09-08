"""afd me 子命令：查看自己的爱发电状态与本月发电情况。"""
from datetime import datetime

from character import get_message
from nonebot import CommandSession
from nonebot.log import logger

from xme.plugins.commands.afdian import __plugin_name__
from xme.plugins.commands.afdian.constants import CMD_ME, TIME_FORMAT
from xme.xmetools.afdiantools import (
    AFDIAN_CLIENT,
    AfdianApiError,
    SponsorProfile,
    get_sponsor_profile,
)
from xme.plugins.commands.xme_user.classes.user import try_load

cmd_name = CMD_ME
alias = ['我的发电']
usage = {
    "name": cmd_name,
    "desc": get_message("plugins", __plugin_name__, cmd_name, 'desc'),
    "introduction": get_message("plugins", __plugin_name__, cmd_name, 'introduction'),
    "usage": '',
    "permissions": [],
    "alias": alias
}


def format_ts(ts: int | None) -> str:
    """把时间戳格式化为展示文本，空值显示「暂无」。"""
    if not ts:
        return "暂无"
    return datetime.fromtimestamp(ts).strftime(TIME_FORMAT)


def format_plan(profile: SponsorProfile) -> str:
    """把当前订阅方案格式化为展示文本（含永久/到期信息）。"""
    name = profile.current_plan_name
    if not name or name == "无":
        return "无"
    if profile.plan_permanent:
        return f"{name}（永久）"
    if profile.plan_expire_time:
        return f"{name}（{datetime.fromtimestamp(profile.plan_expire_time).strftime(TIME_FORMAT)} 到期）"
    return name


async def handle(session: CommandSession, arg: str) -> str:
    """查询发送者绑定账号的发电画像，未绑定则引导使用 afd login。"""
    user = try_load(session.event.user_id)
    if not user.afdian_id:
        return get_message("plugins", __plugin_name__, cmd_name, 'not_bound')
    try:
        profile = await get_sponsor_profile(AFDIAN_CLIENT, user.afdian_id)
    except AfdianApiError as e:
        logger.warning(f"afd me 获取发电画像失败: {e}")
        return get_message("plugins", __plugin_name__, 'api_error')
    if profile is None:
        return get_message("plugins", __plugin_name__, cmd_name, 'no_record')
    return get_message(
        "plugins", __plugin_name__, cmd_name, 'success',
        name=profile.name or "爱发电用户",
        month_amount=f"{profile.month_amount:.2f}",
        month_count=profile.month_order_count,
        recent_days=profile.recent_days,
        recent_amount=f"{profile.recent_amount:.2f}",
        recent_count=profile.recent_order_count,
        total_amount=f"{profile.total_amount:.2f}",
        first_time=format_ts(profile.first_pay_time),
        last_time=format_ts(profile.last_pay_time),
        plan=format_plan(profile),
    )
