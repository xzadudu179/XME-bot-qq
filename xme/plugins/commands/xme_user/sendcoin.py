from xme.plugins.commands.xme_user import __plugin_name__
from nonebot import on_command, CommandSession
from xme.xmetools.message_tools import send_session_msg
from .classes import user as u
from xme.plugins.commands.xme_user.classes.user import User, coin_name, coin_pronoun
from character import get_message


alias = ['转账', f'给{coin_name}', 'ta', 'transfer', 'givecoin']
cmd_name = 'sendcoin'
usage = {
    "name": cmd_name,
    "desc": get_message("plugins", __plugin_name__, cmd_name, 'desc', coin_name=coin_name),
    "introduction": get_message("plugins", __plugin_name__, cmd_name, 'introduction', coin_name=coin_name),
    "usage": f'(at目标用户) ({coin_name}数量 以空格分隔)',
    "permissions": [],
    "alias": alias
}
@on_command(cmd_name, aliases=alias, only_to_me=False)
@u.using_user(save_data=True)
async def _(session: CommandSession, user: User):
    message = ''
    arg_text = session.current_arg.strip() if session.current_arg else ""
    args = arg_text.split(" ")
    coin_count = 0
    at_id = 0
    # 是否有参数并且 at 了用户
    if arg_text and args[0].startswith("[CQ:at,qq="):
        at_id = int(args[0].split("[CQ:at,qq=")[-1].split(",")[0])
    else:
        message = get_message("plugins", __plugin_name__, cmd_name, 'no_arg')
        await send_session_msg(session, message)
        return False
    # 是否 at 自己
    if at_id == session.event.user_id:
        message = get_message("plugins", __plugin_name__, cmd_name, 'send_to_self', coin_name=coin_name)
        await send_session_msg(session, message)
        return False
    # 是否设置了金币数量
    if len(args) >= 2:
        try:
            coin_count = sum([int(i) for i in args[1:] if i.strip().isdigit()])
        except:
            coin_count = 0
    else:
        message = get_message("plugins", __plugin_name__, cmd_name, 'no_coin_count')
        await send_session_msg(session, message)
        return False
    if coin_count <= 0:
        message = get_message("plugins", __plugin_name__, cmd_name, 'invalid_coin_count', coin_name=coin_name)
        await send_session_msg(session, message)
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
        await send_session_msg(session, message)
        return False
    curr_coins = user.coins
    user.coins -= coin_count
    # 是否有足够金币
    if user.coins < 0:
        message = get_message("plugins", __plugin_name__, cmd_name, 'not_enough_coin', coin_name=coin_name, coin_total=curr_coins, coin_pronoun=coin_pronoun)
        await send_session_msg(session, message)
        return False
    send_to_user.add_coins(coin_count)
    send_to_user.save()
    message = get_message("plugins", __plugin_name__, cmd_name, 'success',
        target_user=f' {target_user} ({at_id})' if not at_bot_self else '我',
        coin_name=coin_name,
        coin_count=coin_count,
        coin_pronoun=coin_pronoun,
        coin_left=user.coins,
        received_coin_react=get_message("plugins", __plugin_name__, cmd_name, 'received_coin_react') if at_bot_self else '')
    await send_session_msg(session, message)
    return True