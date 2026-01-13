from nonebot import CommandSession
from xme.xmetools.plugintools import on_command
import traceback
import xme.plugins.commands.wife as w
from nonebot.log import logger
from xme.plugins.commands.wife import command_properties
from character import get_message
from .wife_tools import *
from xme.xmetools.texttools import get_at_id
from xme.xmetools.bottools import permission
from xme.xmetools.msgtools import send_session_msg

wife_alias = ['今日老婆', 'kklp', '看看老婆', 'w']
@on_command('wife', aliases=wife_alias, only_to_me=False, permission=lambda sender: True)
@permission(lambda sender:  sender.is_groupchat, permission_help=" & ".join(command_properties[0]['permission']))
async def _(session: CommandSession):
    # user_id = session.event.user_id
    group_id = str(session.event.group_id)
    wifeinfo = await group_init(group_id)
    logger.debug(session.current_key)
    arg = session.current_arg.strip()
    at_id = 0
    prefix = ""
    # support "/wife change" to change caller's wife
    # if arg.startswith("change"):
    #     at_id = session.event.user_id
    #     # attempt change
    #     new_partner = await change_wife(wifeinfo, group_id, at_id, session)
    #     if new_partner is None:
    #         message = get_message("plugins", w.__plugin_name__, "no_more_wife")
    #     else:
    #         who = "你"
    #         name = (x if (x:=new_partner.get('card', None)) else new_partner['nickname']) if new_partner['user_id'] != session.self_id else "我"
    #         message = get_message("plugins", w.__plugin_name__, "wife_message",
    #             who=who,
    #             avatar=f"[CQ:image,file=https://q1.qlogo.cn/g?b=qq&nk={new_partner['user_id']}&s=640]",
    #             name=name,
    #             user_id=str(new_partner['user_id']))
    #     await send_session_msg(session, message, tips=True, tips_percent=60)
    #     return
    if arg.startswith("[CQ:at,qq="):
        # at_id = int(arg.split("[CQ:at,qq=")[-1].split("]")[0].split(",")[0])
        at_id = get_at_id(arg)
        wife = await search_wife(wifeinfo, group_id, at_id, session)
    else:
        if arg.startswith("@"):
            prefix = get_message("plugins", w.__plugin_name__, "no_at_hint")
        # await send_msg(session, "请 at 你要看的人哦")
        at_name = "你"
        at_id = session.event.user_id
        # return
        logger.debug(at_id, session.self_id, group_id)
        wife = await search_wife(wifeinfo, group_id, at_id, session)
        # logger.debug(wife)
    if at_id == session.self_id:
        # at_id = session.self_id
        at_name = "我"

    try:
        if at_id != session.self_id and at_id != session.event.user_id:
            try:
                at = await session.bot.get_group_member_info(group_id=group_id, user_id=at_id,)
            except:
                at = session.bot.get_stranger_info(user_id=at_id, self_id=session.self_id)
            at_name = f"{x if (x:=at['card']) else at['nickname']} ({at_id}) "
        elif at_id == session.event.user_id:
            at_name = "你"
            at_id = session.event.user_id
        message = get_message("plugins", w.__plugin_name__, "no_wife", name=at_name)
        # message = f"{at_name}今天并没有老婆ovo"
        if wife:
            # logger.debug(pair_user)
            name = (x if (x:=wife.get('card', None)) else wife['nickname']) if wife['user_id'] != session.self_id else "我"
            who = f"{at_name}"
            message = prefix + get_message("plugins", w.__plugin_name__, "wife_message",
                who=who,
                avatar=f"[CQ:image,file=https://q1.qlogo.cn/g?b=qq&nk={wife['user_id']}&s=640]",
                # avatar=image_msg(get_qq_avatar(wife['user_id'])),
                name=name if arg != 'at' else '[CQ:at,qq=' + str(wife['user_id']) + ']',
                user_id=str(wife['user_id']))
            # message = f"{who}今日的老婆是:\n[CQ:image,file=https://q1.qlogo.cn/g?b=qq&nk={wife['user_id']}&s=640]\n{name if arg != 'at' else '[CQ:at,qq=' + str(wife['user_id']) + ']'} ({wife['user_id']})"
    except Exception as ex:
        message = get_message("plugins", w.__plugin_name__, "error", ex=ex)
        # message = f"呜呜，无法获取到群员信息：{ex}"
        logger.exception(traceback.format_exc())
    await send_session_msg(session, message, tips=True, tips_percent=60)

