from nonebot import CommandSession
from xme.xmetools.plugintools import on_command
import xme.plugins.commands.wife as w
from xme.xmetools.debugtools import debug_msg
from xme.plugins.commands.wife import command_properties
from character import get_message
from .wife_tools import *
from xme.xmetools.texttools import get_at_id
from xme.xmetools.bottools import permission, get_group_member_name
from xme.xmetools.imgtools import get_qq_avatar
from xme.xmetools.msgtools import image_msg
from xme.xmetools.msgtools import send_session_msg
from xme.xmetools import timetools as t
from xme.plugins.commands.xme_user.classes.user import using_user, User, custom_limit

wife_alias = ['今日老婆', 'kklp', '看看老婆', 'w']
@on_command('wife', aliases=wife_alias, only_to_me=False, permission=lambda _: True)
@permission(lambda sender:  sender.is_groupchat, permission_help=" & ".join(command_properties[0]['permission']))
@using_user(True)
@custom_limit(lambda session, *_, **__: w.__plugin_name__ + str(session.event.group_id), 1, unit=t.TimeUnit.DAY, count_limit=2)
async def _(session: CommandSession, _: User, check_is_invalid, count_tick):
    group_id = str(session.event.group_id)
    arg = session.current_arg.strip()
    at_id = session.event.user_id
    prefix = ""
    members = [s["user_id"] for s in await session.bot.get_group_member_list(group_id=group_id)]
    # print(members)
    wife_id = "NO_WIFE"
    at_name = "你"

    # 查看别人的老婆
    if arg.startswith("[CQ:at,qq="):
        at_id = get_at_id(arg)
        at_name = await get_group_member_name(group_id, at_id, card=True)
        at_name += f" ({at_id}) "
        wife_id: int | str = get_wife_id(group_id, at_id, members, False)
    # 更换老婆
    elif arg.startswith(("change", "ch", "更换", "换")):
        if check_is_invalid():
            return await send_session_msg(session, get_message("plugins", w.__plugin_name__, "cannot_change_wife"))
        wife_id: int | str = get_wife_id(group_id, at_id, members, False)
        if wife_id == "CANT_GEN":
            return await send_session_msg(session, get_message("plugins", w.__plugin_name__, "no_wife_yet", name=at_name))
        wife_id = change_wife_id(group_id, at_id, members)
        # 无法更换
        if wife_id is None:
            return await send_session_msg(session, get_message("plugins", w.__plugin_name__, "no_more_wife", name=at_name))
        count_tick()
        prefix = get_message("plugins", w.__plugin_name__, "change_wife_success_prefix")
    # 自己的老婆
    else:
        if arg.startswith("@"):
            prefix = get_message("plugins", w.__plugin_name__, "no_at_hint")
        wife_id: int | str = get_wife_id(group_id, at_id, members)
        debug_msg(at_id, session.self_id, group_id)
    if at_id == session.self_id:
        at_name = "我"
    if wife_id == "CANT_GEN":
        return await send_session_msg(session, get_message("plugins", w.__plugin_name__, "no_wife_yet", name=at_name))
    elif wife_id == "NO_WIFE":
        return await send_session_msg(session, get_message("plugins", w.__plugin_name__, "no_wife", name=at_name))
    if wife_id == session.self_id:
        wife_name = "我"
    else:
        wife_name = await get_group_member_name(group_id, wife_id, card=True)
    return await send_session_msg(
        session,
        prefix +
        get_message(
            "plugins",
            w.__plugin_name__,
            "wife_message",
            who=at_name,
            avatar=await image_msg(await get_qq_avatar(wife_id)),
            name=wife_name,
            user_id=str(wife_id),
        )
    )