"""afd plan 子命令：查看自己当前有效的爱发电套餐及持续权益。"""
from datetime import datetime
from character import get_message
from nonebot import CommandSession
from nonebot.log import logger
from xme.plugins.commands.afdian import __plugin_name__
from xme.plugins.commands.afdian.constants import CMD_PLAN, TIME_FORMAT
from xme.plugins.commands.xme_user.classes.user import try_load
from xme.xmetools.afdiantools import AFDIAN_CLIENT, AfdianApiError, PLAN_BENEFITS, get_active_plan

cmd_name = CMD_PLAN
alias = ['套餐', '我的套餐']
usage = {
    "name": cmd_name,
    "desc": get_message("plugins", __plugin_name__, cmd_name, 'desc'),
    "introduction": get_message("plugins", __plugin_name__, cmd_name, 'introduction'),
    "usage": '',
    "permissions": [],
    "alias": alias
}


def _benefit_line(bonus: int, name: str | None = None) -> str:
    """把一条签到权益渲染为文案（name 为空时用于「当前套餐」的权益清单）。"""
    if name:
        return get_message("plugins", __plugin_name__, cmd_name, 'plan_line', name=name, bonus=bonus)
    return get_message("plugins", __plugin_name__, cmd_name, 'benefit_line', bonus=bonus)


def _available_benefits() -> str:
    """渲染所有已配置套餐的权益清单（未订阅时展示）。"""
    lines = [
        _benefit_line(benefit.daily_sign_bonus, benefit.label or (benefit.plan_names[0] if benefit.plan_names else "套餐"))
        for benefit in PLAN_BENEFITS if benefit.daily_sign_bonus > 0
    ]
    return "\n".join(lines) or get_message("plugins", __plugin_name__, cmd_name, 'no_benefits')


async def handle(session: CommandSession, arg: str) -> str:
    """展示发送者当前有效套餐、到期时间与权益；未订阅时列出可获得的权益。"""
    user = try_load(session.event.user_id)
    if not user.afdian_id:
        return get_message("plugins", __plugin_name__, cmd_name, 'not_bound')
    try:
        plan = await get_active_plan(AFDIAN_CLIENT, user.afdian_id)
    except AfdianApiError as e:
        logger.warning(f"afd plan 查询套餐失败: {e}")
        return get_message("plugins", __plugin_name__, 'api_error')
    if plan is None or plan.benefit is None:
        return get_message(
            "plugins", __plugin_name__, cmd_name, 'none',
            benefits=_available_benefits(),
        )
    if plan.permanent:
        expire = get_message("plugins", __plugin_name__, cmd_name, 'expire_permanent')
    elif plan.expire_time:
        expire = datetime.fromtimestamp(plan.expire_time).strftime(TIME_FORMAT)
    else:
        expire = get_message("plugins", __plugin_name__, cmd_name, 'expire_unknown')
    return get_message(
        "plugins", __plugin_name__, cmd_name, 'active',
        name=plan.name or plan.benefit.label or "爱发电套餐",
        expire=expire,
        benefits=_benefit_line(plan.benefit.daily_sign_bonus),
    )
