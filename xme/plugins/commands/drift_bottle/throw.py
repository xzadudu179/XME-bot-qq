from xme.xmetools.timetools import *
from xme.xmetools import jsontools
from .pickup import report
from xme.xmetools import texttools
from character import get_message
from xme.plugins.commands.xme_user.classes import user as u
from xme.xmetools.msgtools import send_session_msg
from xme.xmetools.bottools import permission
from xme.plugins.commands.drift_bottle import __plugin_name__
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
    MAX_LINES = 10
    # raw_arg_msg = session.current_arg.strip()
    # arg, images = text_tools.get_image_str(raw_arg_msg)
    arg = session.current_arg_text.strip()
    if not arg:
        await send_session_msg(session, get_message("plugins", __plugin_name__, "nothing_to_throw", command_name=f"{config.COMMAND_START[0]}{command_name}"))
        # await send_msg(session, f"漂流瓶似乎没有内容呢ovo\n格式：\n{config.COMMAND_START[0]}throw (漂流瓶内容)")
        return False
    if len(arg) > MAX_LENGTH:
        await send_session_msg(session, get_message("plugins", __plugin_name__, "content_too_many", max_length=MAX_LENGTH, text_len=len(arg)))
        # await send_msg(session, f"瓶子的内容太多啦！要 200 字以内哦")
        return False
    if arg.count('\n') >= MAX_LINES or arg.count('\r') >= MAX_LINES:
        await send_session_msg(session, get_message("plugins", __plugin_name__, "lines_too_many", max_lines=MAX_LINES))
        # await send_msg(session, f"瓶子的行数太多啦！最多 MAX_LINES 行哦")
        return False
    # 保存图片并修改图片地址
    # for image in images:
    #     print(image)
    #     await session.bot.api.get_image(file=image)
    # bottles_dict = {}
    bottles_dict = jsontools.read_from_path('./data/drift_bottles.json')
    user = await session.bot.get_group_member_info(group_id=session.event.group_id, user_id=session.event.user_id)
    group = await session.bot.get_group_info(group_id=session.event.group_id)
    try:
        id = bottles_dict["max_index"] + 1
    except:
        id = 0
    for k, bottle in bottles_dict['bottles'].items():
        # print(bottle)
        if texttools.difflib_similar(arg, bottle['content'], False) > 0.75 and bottle["views"] < 114514 and (bottle["likes"] <= bottle["views"] // 2):
        # if arg == bottle['content']:
            await send_session_msg(session, get_message("plugins", __plugin_name__, "content_already_thrown", content=bottle['content'], id=k))
            # await send_msg(session, f"大海里已经有这个瓶子了哦ovo")
            return
    bottle_content = {
        "content": arg,
        # "images": list(images),
        "sender": user['nickname'],
        "likes": 0,
        'views': 0,
        "from_group": group["group_name"],
        "send_time": datetime.now().strftime(format="%Y年%m月%d日 %H:%M:%S"),
        "sender_id": user['user_id'],
        "comments": [],
        "pure_vote_users": {},
        "group_id": user['group_id'],
    }
    bottles_dict['bottles'][id] = bottle_content
    bottles_dict["max_index"] = id
    jsontools.save_to_path('./data/drift_bottles.json', bottles_dict)
    # with open('./data/drift_bottles.json', 'w', encoding='utf-8') as file:
    #     file.write(json.dumps(bottles_dict, ensure_ascii=False))
    await report(session, bottle_content, id, user['user_id'], "发送了一个漂流瓶", False)
    await send_session_msg(session, get_message("plugins", __plugin_name__, 'throwed', id=id))
    # await send_msg(session, f"[CQ:at,qq={user['user_id']}] 瓶子扔出去啦~ 这是大海里的第 {id} 号瓶子哦 owo")
    return True