from nonebot import on_command, CommandSession
from xme.xmetools import pair as p
from .wife_tools import *

wife_alias = ['今日老婆', 'kklp', '看看老婆']
@on_command('wife', aliases=wife_alias, only_to_me=False, permission=lambda sender: sender.is_groupchat)
async def _(session: CommandSession):
    user_id = session.event.user_id
    group_id = str(session.event.group_id)
    wifeinfo = await group_init(group_id)
    arg = session.current_arg.strip()
    at_id = 0
    if arg.startswith("[CQ:at,qq="):
        at_id = int(arg.split("[CQ:at,qq=")[-1].split(",")[0])
    # 如果是对 xme 说
    elif session.ctx['to_me']:
        at_id = session.self_id
        at_name = "我"
    else:
        # await session.send("请 at 你要看的人哦")
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
        message = f"{at_name}今天并没有老婆ovo"
        if wife:
            # print(pair_user)
            name = x if (x:=wife['card']) else wife['nickname']
            who = f"[CQ:at,qq={user_id}] {at_name}"
            message = f"{who}今日的老婆是:\n[CQ:image,file=https://q1.qlogo.cn/g?b=qq&nk={wife['user_id']}&s=640]\n{name if arg != 'at' else '[CQ:at,qq=' + str(wife['user_id']) + ']'} ({wife['user_id']})"
    except Exception as ex:
        message = f"呜呜，无法获取到群员信息：{ex}"
        print(ex)
    await session.send(message)

