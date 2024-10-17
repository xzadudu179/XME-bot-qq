from xme.xmetools.date_tools import *
from xme.xmetools import json_tools
import json
import config
from nonebot import on_command, CommandSession

throw_alias = ["扔瓶子", "扔漂流瓶", "扔瓶"]

@on_command('throw', aliases=throw_alias, only_to_me=False, permission=lambda x: x.is_groupchat)
async def _(session: CommandSession):
    arg = session.current_arg_text.strip()
    if not arg:
        await session.send(f"漂流瓶似乎没有内容呢ovo\n格式：\n{config.COMMAND_START[0]}throw (漂流瓶内容)")
        return
    if len(arg) > 200:
        await session.send(f"瓶子的内容太多啦！要 200 字以内哦")
        return
    if arg.count('\n') > 15:
        await session.send(f"瓶子的行数太多啦！最多 15 行哦")
        return
    # bottles_dict = {}
    bottles_dict = json_tools.read_from_path('./data/drift_bottles.json')
    # with open('./data/drift_bottles.json', 'r', encoding='utf-8') as file:
    #     bottles_dict = json.load(file)
    user = await session.bot.get_group_member_info(group_id=session.event.group_id, user_id=session.event.user_id)
    group = await session.bot.get_group_info(group_id=session.event.group_id)
    try:
        id = bottles_dict["max_index"] + 1
    except:
        id = 0
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
    await session.send(f"瓶子扔出去啦~ 这是大海里的第 {id} 号瓶子哦 owo")