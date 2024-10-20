from nonebot import on_command, CommandSession
from .wife_tools import *

cancanneedalias = ['看看老婆', 'peekwife', 'kkndwife', 'kkndlp', 'kklp']
@on_command('cancanneedwife', aliases=cancanneedalias, only_to_me=False, permission=lambda sender: sender.is_groupchat)
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
        return
    wife = await search_wife(wifeinfo, group_id, at_id, session)
    print(at_id, session.self_id)
    # print(wife)

    try:
        if at_id != session.self_id:
            at = await session.bot.get_group_member_info(group_id=group_id, user_id=at_id)
            at_name = f"{at['nickname']} ({at_id}) "
        message = f"{at_name}今天并没有老婆ovo"
        if wife:
            # print(pair_user)
            name = wife['nickname']
            who = f"[CQ:at,qq={user_id}] {at_name}"
            message = f"{who}今日的老婆是:\n[CQ:image,file=https://q1.qlogo.cn/g?b=qq&nk={wife['user_id']}&s=640]\n{name} ({wife['user_id']})"
    except:
        message = "呜呜，无法获取到你 at 的群员信息"
    await session.send(message)


