from xme.xmetools.date_tools import *
from xme.xmetools import json_tools
from xme.xmetools import text_tools
from character import get_message
from xme.plugins.commands.drift_bottle import __plugin_name__
import config
from nonebot import on_command, CommandSession

throw_alias = ["扔瓶子", "扔漂流瓶", "扔瓶"]
command_name = 'throw'
@on_command('throw', aliases=throw_alias, only_to_me=False, permission=lambda x: x.is_groupchat)
async def _(session: CommandSession):
    MAX_LENGTH = 200
    MAX_LINES = 15
    arg = session.current_arg_text.strip()
    if not arg:
        await session.send(get_message(__plugin_name__, "nothing_to_throw").format(command_name=f"{config.COMMAND_START[0]}{command_name}"))
        # await session.send(f"漂流瓶似乎没有内容呢ovo\n格式：\n{config.COMMAND_START[0]}throw (漂流瓶内容)")
        return
    if len(arg) > MAX_LENGTH:
        await session.send(get_message(__plugin_name__, "content_too_many").format(max_length=MAX_LENGTH))
        # await session.send(f"瓶子的内容太多啦！要 200 字以内哦")
        return
    if arg.count('\n') > MAX_LINES or arg.count('\r') > MAX_LINES:
        await session.send(get_message(__plugin_name__, "lines_too_many").format(max_lines=MAX_LINES))
        # await session.send(f"瓶子的行数太多啦！最多 MAX_LINES 行哦")
        return
    # bottles_dict = {}
    bottles_dict = json_tools.read_from_path('./data/drift_bottles.json')
    user = await session.bot.get_group_member_info(group_id=session.event.group_id, user_id=session.event.user_id)
    group = await session.bot.get_group_info(group_id=session.event.group_id)
    try:
        id = bottles_dict["max_index"] + 1
    except:
        id = 0
    for k, bottle in bottles_dict['bottles'].items():
        # print(bottle)
        if text_tools.jaccard_similarity(arg, bottle['content'], False) > 0.75:
        # if arg == bottle['content']:
            await session.send(get_message(__plugin_name__, "content_already_thrown").format(content=bottle['content'], id=k))
            # await session.send(f"大海里已经有这个瓶子了哦ovo")
            return
    bottles_dict['bottles'][id] = {
        "content": arg,
        "sender": user['nickname'],
        "likes": 0,
        'views': 0,
        "from_group": group["group_name"],
        "send_time": datetime.now().strftime(format="%Y年%m月%d日 %H:%M:%S"),
        "sender_id": user['user_id'],
        "group_id": user['group_id'],
    }
    bottles_dict["max_index"] = id
    json_tools.save_to_path('./data/drift_bottles.json', bottles_dict)
    # with open('./data/drift_bottles.json', 'w', encoding='utf-8') as file:
    #     file.write(json.dumps(bottles_dict, ensure_ascii=False))
    await session.send(f"[CQ:at,qq={user['user_id']}] " + get_message(__plugin_name__, 'throwed').format(id=id))
    # await session.send(f"[CQ:at,qq={user['user_id']}] 瓶子扔出去啦~ 这是大海里的第 {id} 号瓶子哦 owo")