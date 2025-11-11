from xme.xmetools.timetools import *
from .pickup import report
from character import get_message
from xme.plugins.commands.xme_user.classes import user as u
from xme.xmetools.msgtools import send_session_msg
from xme.xmetools.bottools import permission
from xme.plugins.commands.drift_bottle import __plugin_name__
from . import DriftBottle
import config
from nonebot import on_command, CommandSession

throw_alias = ["扔瓶子", "扔漂流瓶", "扔瓶"]
command_name = 'throw'
@on_command(command_name, aliases=throw_alias, only_to_me=False, permission=lambda _: True)
@u.using_user(save_data=False)
@u.limit(command_name, 1, get_message("plugins", __plugin_name__, 'throw_limited'), unit=TimeUnit.HOUR, count_limit=5)
@permission(lambda x: x.is_groupchat, permission_help="在群聊内")
async def _(session: CommandSession, user):
    MAX_LENGTH = 300
    MAX_LINES = 20

    arg = session.current_arg_text.strip()
    if not arg:
        await send_session_msg(session, get_message("plugins", __plugin_name__, "nothing_to_throw", command_name=f"{config.COMMAND_START[0]}{command_name}"))
        return False
    check = DriftBottle.check_duplicate_bottle(arg)
    if check['status'] == False:
        await send_session_msg(session, get_message("plugins", __plugin_name__, "content_already_thrown"))
        return False

    user = await session.bot.get_group_member_info(group_id=session.event.group_id, user_id=session.event.user_id)
    group = await session.bot.get_group_info(group_id=session.event.group_id)
    bottle_id = DriftBottle.get_max_bottle_id() + 1
    print(bottle_id)
    bottle_content = {
        "id": -1,
        "bottle_id": bottle_id,
        "content": arg,
        # "images": list(images),
        "sender": user['nickname'],
        "likes": 0,
        'views': 0,
        "from_group": group["group_name"],
        "send_time": datetime.now().strftime(format="%Y年%m月%d日 %H:%M:%S"),
        "sender_id": user['user_id'],
        "comments": "[]",
        "is_broken": False,
        # "pure_vote_users": {},
        "group_id": user['group_id'],
    }

    bottle: DriftBottle = DriftBottle.form_dict(bottle_content)
    formatted_arg = bottle.get_formatted_content("0%")
    # print(formatted_arg, len(formatted_arg))
    # print(arg, len(arg))
    if len(formatted_arg) > MAX_LENGTH:
        await send_session_msg(session, get_message("plugins", __plugin_name__, "content_too_many", max_length=MAX_LENGTH, text_len=len(formatted_arg)))
        return False
    if arg.count('\n') >= MAX_LINES or arg.count('\r') >= MAX_LINES:
        await send_session_msg(session, get_message("plugins", __plugin_name__, "lines_too_many", max_lines=MAX_LINES))
        return False


    bottle.save()
    print(bottle)

    await report(session, bottle, user['user_id'], "发送了一个漂流瓶", False)
    await send_session_msg(session, get_message("plugins", __plugin_name__, 'throwed', id=bottle_id), tips=True)
    # await send_msg(session, f"[CQ:at,qq={user['user_id']}] 瓶子扔出去啦~ 这是大海里的第 {id} 号瓶子哦 owo")
    return True