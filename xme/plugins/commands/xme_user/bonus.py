"""奖金账户：发放池机制 + 超管充值命令。

奖金账户（User.bonus）每天凌晨由 schedulers/bonus_payday.py 触发 pay_daily_bonuses，
把每个用户的 min(bonus, DAILY_BONUS_LIMIT) 转入星币余额——账户余额低于上限时当天
全发完，效果上等同直接加星币；跨过零点不在线时由启动补发任务调用同一幂等函数。
"""
from nonebot import CommandSession
from nonebot.log import logger

from character import get_message
from xme.xmetools.debugtools import debug_msg
from xme.xmetools.doctools import SUPERUSER_PERMISSION
from xme.xmetools.bottools import permission
from xme.xmetools.jsontools import read_from_path, save_to_path
from xme.xmetools.msgtools import get_user_id_from_arg, send_session_msg
from xme.xmetools.plugintools import on_command
from xme.xmetools.texttools import no_except_cn2an
from xme.xmetools import timetools
from . import __plugin_name__
from .classes import user as u
from .classes.user import User, coin_name

# 每天从奖金账户自动发放到星币余额的上限
DAILY_BONUS_LIMIT = 2000
# 发放进度记录（last_bonus_day = curr_days 天数）：零点 cron 与启动补发共用，
# 当天已发放则直接跳过，天然防双发
BONUS_VARS_PATH = "data/bot_vars.json"


def _load_last_bonus_day() -> int:
    return int(read_from_path(BONUS_VARS_PATH).get("last_bonus_day") or 0)


def _save_last_bonus_day(day: int) -> None:
    vars = read_from_path(BONUS_VARS_PATH)
    vars["last_bonus_day"] = day
    save_to_path(BONUS_VARS_PATH, vars)


def pay_daily_bonuses() -> tuple[int, int]:
    """把所有用户的奖金按每天上限发放到星币余额，返回 (发放人数, 发放总金额)。

    幂等：当天已发放（bot_vars 的 last_bonus_day 为今天）直接返回 (0, 0)，
    供零点 cron 与启动补发安全共用。发放用单条 UPDATE 原子完成
    （coins 加多少 bonus 就减多少，SQLite 单事务无并发问题）。
    """
    today = timetools.curr_days()
    if _load_last_bonus_day() == today:
        return 0, 0
    stats = User.exec_query(
        f"SELECT COUNT(*) AS n, COALESCE(SUM(MIN(bonus, ?)), 0) AS total "
        f"FROM {User.get_table_name()} WHERE bonus > 0",
        (DAILY_BONUS_LIMIT,))
    count = int(stats[0]["n"]) if stats else 0
    total = int(stats[0]["total"]) if stats else 0
    if count:
        User.exec_query(
            f"UPDATE {User.get_table_name()} "
            f"SET coins = coins + MIN(bonus, ?), bonus = bonus - MIN(bonus, ?) "
            f"WHERE bonus > 0",
            (DAILY_BONUS_LIMIT, DAILY_BONUS_LIMIT))
        logger.info(f"奖金账户每日发放：{count} 名用户共发放 {total} {coin_name}")
    _save_last_bonus_day(today)
    return count, total


alias = ['添加奖金', '加奖金']
cmd_name = 'addbonus'
usage = {
    "name": cmd_name,
    "desc": get_message("plugins", __plugin_name__, cmd_name, 'desc', ),
    "introduction": get_message("plugins", __plugin_name__, cmd_name, 'introduction', ),
    "usage": f'(at目标用户) (奖金数量 以空格分隔)',
    "permissions": ["在群聊内"] + SUPERUSER_PERMISSION,
    "alias": alias
}


@on_command(cmd_name, aliases=alias, only_to_me=False, permission=lambda _: True)
@u.using_user(save_data=True)
@permission(lambda sender: sender.is_groupchat and (sender.is_superuser), permission_help=" & ".join(usage["permissions"]))
async def _(session: CommandSession, user: User):
    arg_text = session.current_arg.strip() if session.current_arg else ""
    debug_msg(arg_text)
    args = arg_text.split(" ")
    at_id = get_user_id_from_arg(args[0]) if arg_text else None
    if at_id is None:
        await send_session_msg(session, get_message("plugins", __plugin_name__, cmd_name, 'no_arg'), tips=True)
        return False
    if len(args) < 2:
        await send_session_msg(session, get_message("plugins", __plugin_name__, cmd_name, 'no_coin_count'), tips=True)
        return False
    # 金额支持阿拉伯数字与中文数字（与 sendcoin 同款解析）
    try:
        bonus_count = sum([int(no_except_cn2an(i.strip()))
                           for i in args[1:]
                           if i.strip() and str(no_except_cn2an(i.strip())).isdecimal()])
    except Exception:
        bonus_count = 0
    if bonus_count <= 0:
        await send_session_msg(session, get_message("plugins", __plugin_name__, cmd_name, 'invalid_coin_count', ), tips=True)
        return False
    # 验证用户是否存在
    try:
        target_name = (await session.bot.api.get_stranger_info(user_id=at_id))['nickname']
    except Exception:
        await send_session_msg(session, get_message("plugins", __plugin_name__, cmd_name, 'invalid_user'), tips=True)
        return False
    send_to_user: u.User = u.User.load(at_id, True)
    send_to_user.add_bonus(bonus_count)
    send_to_user.save()
    await send_session_msg(session, get_message("plugins", __plugin_name__, cmd_name, 'success',
        target_user=f' {target_name} ({at_id})',
        coin_count=bonus_count,
        bonus_left=send_to_user.bonus,
    ), tips=True)
    return True
