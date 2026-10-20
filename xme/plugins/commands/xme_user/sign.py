from xme.plugins.commands.xme_user import __plugin_name__
from nonebot import CommandSession
from nonebot.log import logger
from xme.xmetools.plugintools import on_command
# from xme.xmetools.msgtools import send_session_msg
from xme.xmetools import timetools
# from xme.xmetools.texttools import dec_to_chinese
import cn2an
from xme.xmetools import randtools

import math
import random
from functools import wraps

from xme.xmetools.texttools import remove_punctuation
# random.seed()
from .classes import user as u
from .classes.user import User
from xme.plugins.commands.xme_user.classes.user import User, coin_name, coin_pronoun
from character import get_message
from xme.xmetools.debugtools import debug_msg
from xme.xmetools.dicttools import get_value, set_value
from xme.xmetools.timetools import TELIA_CLOCK
from xme.xmetools.msgtools import aget_arg, send_session_msg

alias = ['签到', 'register', 's']
cmd_name = 'sign'
usage = {
    "name": cmd_name,
    "desc": get_message("plugins", __plugin_name__, cmd_name, 'desc'),
    "introduction": get_message("plugins", __plugin_name__, cmd_name, 'introduction', ),
    "usage": '',
    "permissions": [],
    "alias": alias
}

def heal_stale_sign_quota(func):
    """验证签到配额（limit 与 data）是否正确并修复
    """
    @wraps(func)
    async def wrapper(session: CommandSession, user: User, *args, **kwargs):
        try:
            if _has_stale_sign_quota(user):
                u.reset_limit(user, cmd_name)
                logger.warning(f"用户 {user.id} 的签到配额出现残留，已放行重签")
        except Exception:
            logger.exception("签到配额自愈失败")
        return await func(session, user, *args, **kwargs)
    return wrapper


def _has_stale_sign_quota(user: User) -> bool:
    """今天的配额占用是否有未完成的残留（执行中的占位已由 get_limit_info 扣除）。"""
    counter_time, count = u.get_limit_info(user, cmd_name)
    if count < 1 or not counter_time:
        return False
    today = math.floor(timetools.get_valuetime(timetools.timenow(), timetools.TimeUnit.DAY))
    occupied_day = math.floor(timetools.get_valuetime(counter_time, timetools.TimeUnit.DAY))
    if today - occupied_day >= 1:
        return False   # 占用不是今天的：限流器自己会重置，不算残留
    sign_date = get_value(__plugin_name__, cmd_name, "sign_date",
                          search_dict=user.plugin_datas, default=0)
    return sign_date != timetools.curr_days()


def count_signed_today(users: list[dict], curr_date: int) -> int:
    """统计今天已完成签到的用户数（纯函数，供排名与首签判定）。

    按完成记录（plugin_datas 里的 sign_date == 今天）统计，不用限流计数器的
    时间：配额在本命令执行前就占住（当前用户自己的那份也在里面），且进程崩溃
    会留下未完成的占位——用计数器会把它们都算成「今天已签到」，导致所有人的
    名次整体后移（第一个签到的人被判成第二个），首签奖励也发不出去。
    """
    count = 0
    for us in users:
        sign_data = get_value(__plugin_name__, cmd_name,
                              search_dict=us.get("plugin_datas") or {}, default=None)
        if isinstance(sign_data, dict) and sign_data.get("sign_date") == curr_date:
            count += 1
    return count


@on_command(cmd_name, aliases=alias, only_to_me=False, permission=lambda _: True)
@u.using_user(save_data=False)
@heal_stale_sign_quota
@u.limit(cmd_name, 1, get_message("plugins", __plugin_name__, cmd_name, 'limited'))
async def _(session: CommandSession, user: User):
    FIRST_AWARD = 20
    message = ""
    # message = get_message("plugins", __plugin_name__, cmd_name, 'failed')
    consecutive_days = get_value(__plugin_name__, cmd_name, "consecutive_days", search_dict=user.plugin_datas, default=0)
    last_sign_date = get_value(__plugin_name__, cmd_name, "sign_date", search_dict=user.plugin_datas, default=timetools.curr_days())
    curr_date = timetools.curr_days()
    is_consecutive = curr_date - last_sign_date <= 1
    # 临时改变
    # is_consecutive = True
    debug_msg("USER IS", user)
    append_coins = random.randint(0, 100)
    consecutive_award = int(min(consecutive_days * 0.02 * append_coins, append_coins * 2))
    user.add_coins(append_coins + consecutive_award)
    users: list[dict] = User.get_users()
    signed_users_count = count_signed_today(users, curr_date)
    macro_season, micro_season, _ = TELIA_CLOCK.get_current_state()
    status_message = get_message("character", "time_period_reactions", timetools.get_time_period(), f"{macro_season.value}{micro_season.value}", default=None)
    if status_message is None:
        status_message = get_message("character", "time_period_reactions",timetools.get_time_period(), f"normal")
    reaction = "\n" + status_message if randtools.random_percent(min(100, max(0, user.xme_favorability + 20))) else ""
    can_make_up = False
    if curr_date - last_sign_date == 2 and consecutive_days > 1:
        can_make_up = True
    if append_coins == 0:
        message = get_message("plugins", __plugin_name__, cmd_name, 'login_no_coins',
            time_period=timetools.get_time_period()
        )
    else:
        message = get_message(
            "plugins", __plugin_name__, cmd_name, 'success',
            login_success=get_message(
                "plugins", __plugin_name__, cmd_name, 'login_success', time_period=timetools.get_time_period()
            ),
            state=get_message("plugins", __plugin_name__, cmd_name, 'get_state'),
            coin_count=abs(append_coins),
            coin_pron_name=coin_pronoun + coin_name,
            coin_total=user.coins,
        )
    if signed_users_count == 0:
        user.add_coins(FIRST_AWARD)
        sign_message = get_message("plugins", __plugin_name__, cmd_name, 'first_sign', first_award=FIRST_AWARD,  )
    else:
        sign_message = get_message("plugins", __plugin_name__, cmd_name,'sign_rank', count=cn2an.an2cn(signed_users_count + 1) if (signed_users_count + 1 <= 10) else f' {signed_users_count + 1} ')
    consecutive_message = ""
    if can_make_up:
        make_up_cost = consecutive_days * 15
        await send_session_msg(session, get_message("plugins", __plugin_name__, cmd_name, 'consecutive_make_up', cost=make_up_cost))
        reply = await aget_arg(
            session,
            prompt="",
            rules=lambda r: remove_punctuation(r) in ['y', 'Y', 'n', 'N'],
        )
        if reply in ['y', 'Y']:
            spend_result = await user.try_spend(session, make_up_cost)
            if spend_result:
                is_consecutive = True
    if consecutive_days > 0 and is_consecutive:
        consecutive_message = "\n" + get_message(
            "plugins", __plugin_name__, cmd_name, 'consecutive_days', n = consecutive_days + 1, cons_award=
            " " + get_message(
                "plugins", __plugin_name__, cmd_name, "cons_award", count=consecutive_award
                ) if consecutive_award > 0 else ""
            )
    if not is_consecutive:
        consecutive_message = "\n" + get_message("plugins", __plugin_name__, cmd_name, 'consecutive_reset', days=consecutive_days)
    message += consecutive_message + "\n" + sign_message + reaction

    if consecutive_days + 1 >= 30 and is_consecutive:
        await user.achieve_achievement(session, "沙漠探索者")
    # 增加连签
    set_value(__plugin_name__, cmd_name, "consecutive_days", search_dict=user.plugin_datas, set_method=lambda v: (v + 1) if v is not None and is_consecutive else 1)
    set_value(__plugin_name__, cmd_name, "sign_date", search_dict=user.plugin_datas, set_method=lambda _: curr_date)
    # 防止发送消息时间过长导致出现多个第一名签到的情况
    user.save()
    debug_msg("保存用户数据")
    return message