from nonebot import on_command, CommandSession
import traceback
import xme.plugins.commands.wife as w
from character import get_message
from .wife_tools import *
from xme.xmetools.command_tools import send_session_msg

wife_alias = ['今日老婆', 'kklp', '看看老婆']
@on_command('wife', aliases=wife_alias, only_to_me=False, permission=lambda sender: sender.is_groupchat)
async def _(session: CommandSession):
    # user_id = session.event.user_id
    group_id = str(session.event.group_id)
    wifeinfo = await group_init(group_id)
    print(session.current_key)
    arg = session.current_arg.strip()
    at_id = 0
    if arg.startswith("[CQ:at,qq="):
        at_id = int(arg.split("[CQ:at,qq=")[-1].split(",")[0])
    # 如果是对 xme 说
    elif session.ctx['to_me']:
        at_id = session.self_id
        at_name = "我"
    else:
        # await send_msg(session, "请 at 你要看的人哦")
        at_name = "你"
        at_id = session.event.user_id
        # return
    try:
        print(at_id, session.self_id, group_id)
        wife = await search_wife(wifeinfo, group_id, at_id, session)
        # print(wife)

        if at_id != session.self_id and at_id != session.event.user_id:
            at = await session.bot.get_group_member_info(group_id=group_id, user_id=at_id)
            at_name = f"{x if (x:=at['card']) else at['nickname']} ({at_id}) "
        elif at_id == session.event.user_id:
            at_name = "你"
            at_id = session.event.user_id
        message = get_message(w.__plugin_name__, "no_wife", name=at_name)
        # message = f"{at_name}今天并没有老婆ovo"
        if wife:
            # print(pair_user)
            name = (x if (x:=wife['card']) else wife['nickname']) if wife['user_id'] != session.self_id else "我"
            who = f"{at_name}"
            message = get_message(w.__plugin_name__, "wife_message",
                who=who,
                avatar=f"[CQ:image,file=https://q1.qlogo.cn/g?b=qq&nk={wife['user_id']}&s=640]",
                name=name if arg != 'at' else '[CQ:at,qq=' + str(wife['user_id']) + ']',
                user_id=str(wife['user_id']))
            # message = f"{who}今日的老婆是:\n[CQ:image,file=https://q1.qlogo.cn/g?b=qq&nk={wife['user_id']}&s=640]\n{name if arg != 'at' else '[CQ:at,qq=' + str(wife['user_id']) + ']'} ({wife['user_id']})"
    except Exception as ex:
        message = get_message(w.__plugin_name__, "error", ex=ex)
        # message = f"呜呜，无法获取到群员信息：{ex}"
        print(traceback.format_exc())
    await send_session_msg(session, message)

