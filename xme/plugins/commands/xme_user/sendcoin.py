from xme.plugins.commands.xme_user import __plugin_name__
from nonebot import CommandSession
from xme.xmetools.plugintools import on_command
from xme.xmetools.bottools import permission
from xme.xmetools.msgtools import send_session_msg
from .classes import user as u
from datetime import datetime
from xme.plugins.commands.xme_user.classes.user import User, coin_name, coin_pronoun
from character import get_message
from xme.xmetools.debugtools import debug_msg
from nonebot.log import logger
from xme.xmetools.texttools import get_at_id

alias = ['转账', f'给{coin_name}', 'ta', 'transfer', 'givecoin', 'v']
cmd_name = 'sendcoin'
usage = {
    "name": cmd_name,
    "desc": get_message("plugins", __plugin_name__, cmd_name, 'desc', ),
    "introduction": get_message("plugins", __plugin_name__, cmd_name, 'introduction', ),
    "usage": f'(at目标用户) ({coin_name}数量 以空格分隔)',
    "permissions": ["在群聊内"],
    "alias": alias
}

COUNT_LIMIT = 200

@on_command(cmd_name, aliases=alias, only_to_me=False, permission=lambda _: True)
@u.using_user(save_data=True)
@u.custom_limit(cmd_name, 1, count_limit=COUNT_LIMIT)
@permission(lambda sender:  sender.is_groupchat, permission_help=" & ".join(usage["permissions"]))
async def _(session: CommandSession, user: User, check_invalid, count_tick):
    message = ''
    arg_text = session.current_arg.strip() if session.current_arg else ""
    debug_msg(arg_text)
    args = arg_text.split(" ")
    coin_count = 0
    at_id = 0
    # 是否有参数并且 at 了用户
    if arg_text and args[0].startswith("[CQ:at,qq="):
        # at_id = int(args[0].split("[CQ:at,qq=")[-1].split(",")[0])
        at_id = get_at_id(args[0])

    else:
        message = get_message("plugins", __plugin_name__, cmd_name, 'no_arg')
        await send_session_msg(session, message, tips=True)
        return False
    # 是否 at 自己
    if at_id == session.event.user_id:
        message = get_message("plugins", __plugin_name__, cmd_name, 'send_to_self', )
        await send_session_msg(session, message, tips=True)
        return False
    # 是否设置了金币数量
    if len(args) >= 2:
        try:
            coin_count = sum([int(i) for i in args[1:] if i.strip().isdigit()])
        except:
            coin_count = 0
    else:
        message = get_message("plugins", __plugin_name__, cmd_name, 'no_coin_count')
        await send_session_msg(session, message, tips=True)
        return False
    if coin_count <= 0:
        message = get_message("plugins", __plugin_name__, cmd_name, 'invalid_coin_count', )
        await send_session_msg(session, message, tips=True)
        return False
    _, limit_c = u.get_limit_info(user, cmd_name)
    can_give_count = COUNT_LIMIT - limit_c
    if coin_count > can_give_count:
        message = get_message("plugins", __plugin_name__, cmd_name, 'coin_too_many', max=can_give_count)
        await send_session_msg(session, message, tips=True)
        return False

    # 验证用户是否存在
    is_real_user = False
    at_bot_self = at_id == session.self_id
    try:
        target_user = (await session.bot.api.get_stranger_info(user_id=at_id))['nickname']
        is_real_user = True
    except:
        pass
    if is_real_user:
        send_to_user: u.User = u.User.load(at_id, True)
    else:
        message = get_message("plugins", __plugin_name__, cmd_name, 'invalid_user')
        await send_session_msg(session, message, tips=True)
        return False
    curr_coins = user.coins
    user.coins -= coin_count
    # 是否有足够金币
    if user.coins < 0:
        message = get_message("plugins", __plugin_name__, cmd_name, 'not_enough_coin',  coin_total=curr_coins, )
        await send_session_msg(session, message, tips=True)
        return False
    send_to_user.add_coins(coin_count)
    send_to_user.save()
    message = get_message("plugins", __plugin_name__, cmd_name, 'success',
        target_user=f' {target_user} ({at_id})' if not at_bot_self else '我',
        coin_count=coin_count,
        coin_left=user.coins,
        received_coin_react=get_message("plugins", __plugin_name__, cmd_name, 'received_coin_react') if at_bot_self else '')
    await send_session_msg(session, message, tips=True)
    # print(datetime.today().weekday(), at_bot_self, coin_count)
    if at_bot_self and coin_count == 50 and datetime.today().weekday() == 3:
        await user.achieve_achievement(session, "V我50")
    count_tick(coin_count)
    return True