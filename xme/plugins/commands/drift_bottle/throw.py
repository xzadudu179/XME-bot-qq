from xme.xmetools.date_tools import *
import json
import config
from nonebot import on_command, CommandSession

throw_alias = ["扔瓶子", "扔漂流瓶", "扔瓶"]

@on_command('throw', aliases=throw_alias, only_to_me=False, permission=lambda x: x.is_groupchat)
async def _(session: CommandSession):
    if not session.current_arg_text.strip():
        await session.send(f"漂流瓶似乎没有内容呢ovo\n格式：\n{config.COMMAND_START[0]}throw (漂流瓶内容)")
        return
    if len(session.current_arg_text.strip()) > 200:
        await session.send(f"瓶子的内容太多啦！要 200 字以内哦")
        return
    bottles_dict = {}
    with open('./data/drift_bottles.json', 'r', encoding='utf-8') as file:
        bottles_dict = json.load(file)
    user = await session.bot.get_group_member_info(group_id=session.event.group_id, user_id=session.event.user_id)
    group = await session.bot.get_group_info(group_id=session.event.group_id)
    bottles_dict['bottles'].append({
        "content": session.current_arg_text.strip(),
        "sender": user['nickname'],
        "from_group": group["group_name"],
        "send_time": datetime.now().strftime(format="%Y年%m月%d日 %H:%M:%S"),
        "sender_id": user['user_id'],
        "group_id": user['group_id'],
    })
    with open('./data/drift_bottles.json', 'w', encoding='utf-8') as file:
        file.write(json.dumps(bottles_dict, ensure_ascii=False))
    await session.send("瓶子扔出去啦~")