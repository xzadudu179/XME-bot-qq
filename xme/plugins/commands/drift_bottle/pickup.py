from xme.xmetools.date_tools import *
import json
import random
from nonebot import on_command, CommandSession

pickup_alias = ["捡瓶子", "捡漂流瓶", "捡瓶"]

@on_command('pickup', aliases=pickup_alias, only_to_me=False, permission=lambda x: x.is_groupchat)
async def _(session: CommandSession):
    bottles_dict = {}
    with open('./data/drift_bottles.json', 'r', encoding='utf-8') as file:
        bottles_dict = json.load(file)

    if len(bottles_dict['bottles']) < 1:
        await session.send("海里一个瓶子里都没有...")
        return
    pickedup = (random.randint(0, 100) > 50)
    if not pickedup:
        await session.send("你没有捡到瓶子ovo")
        return

    bottle = random.choice(bottles_dict['bottles'])
    bottle_card = f"你捡到了一个漂流瓶~\n内容：\n-----------\n{bottle['content']}\n-----------\n发送者：{bottle['sender']}\n来自群：{bottle['from_group']}\n扔瓶子时间：{bottle['send_time']}"
    await session.send(bottle_card)