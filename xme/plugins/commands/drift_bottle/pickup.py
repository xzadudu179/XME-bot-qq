from xme.xmetools.date_tools import *
from xme.xmetools.command_sender import send_cmd
from xme.xmetools import json_tools
import json
import random
from nonebot import on_command, CommandSession
import config
from nonebot.command import call_command, CommandManager, Command


pickup_alias = ["捡瓶子", "捡漂流瓶", "捡瓶", "pick"]

@on_command('pickup', aliases=pickup_alias, only_to_me=False)
async def _(session: CommandSession):
    # with open('./data/drift_bottles.json', 'r', encoding='utf-8') as file:
    #     bottles_dict = json.load(file)
    bottles_dict = json_tools.read_from_path('./data/drift_bottles.json')
    bottles: list = bottles_dict['bottles']
    # 没捡到瓶子
    if len(bottles) < 1:
        await session.send("海里一个瓶子里都没有...")
        return
    pickedup = (random.randint(0, 100) > 10)
    if not pickedup:
        await session.send("你没有捡到瓶子ovo")
        return

    print("捡瓶子中")
    bottle = random.choice(bottles)
    # 增加浏览量以及构造卡片
    # ----------------------------
    view_message = f"被捡到了{bottle['views']}次" if bottle['views'] > 0 else f"第一次被捡到"
    bottle['views'] += 1
    like_message = f"获得了{bottle['likes']}个赞owo" if bottle['likes'] > 0 else f"还没有任何赞ovo"
    bottle_card = f"[CQ:at,qq={session.event.user_id}] 你捡到了一个漂流瓶~\n：[#{bottle['index']}号漂流瓶]：\n-----------\n{bottle['content']}\n-----------\n来自群 \"{bottle['from_group']}\" 的 \"{bottle['sender']}\"\n扔瓶子时间：{bottle['send_time']}\n这个瓶子{view_message}，{like_message}"
    bottle_card += f"\n发送 \"-like\" 以点赞，发送 \"-rep\" 以举报。"
    # ----------------------------
    await session.send(bottle_card)
    print("捡到了瓶子")

    # 手滑摔碎了瓶子 (1% 概率)
    broken = (random.randint(0, 100) > 99)
    if broken:
        await session.send("啊，你不小心把瓶子摔碎了...")
        del bottles[bottle['index'] - 1]
    else:
        # 处理之后可能的输入
        reply = (await session.aget()).strip()
        if reply == '-like':
            bottle['likes'] += 1
            await session.send("点赞成功~")
        elif reply == '-rep':
            await session.send("举报成功")
            for superuser in config.SUPERUSERS:
                await session.bot.send_private_msg(user_id=session[superuser],message=f"有人举报漂流瓶内容，漂流瓶信息如下：\n{bottle}")
        else:
            send_cmd(reply, session)
            # name = reply.split(" ")[0]
            # if name[0] in config.COMMAND_START:
            #     name = name[1:]
            # alias_cmd: Command = CommandManager._aliases.get(name, False)
            # if alias_cmd:
            #     name = alias_cmd.name
            # # print(CommandManager._find_command(self=CommandManager, name=name))
            # args = " ".join((reply.split(" ")[1:])) if len(reply.split(" ")) > 1 else ""
            # print(f"parse command: {name} | {args}")
            # await call_command(
            #     bot=session.bot,
            #     event=session.event,
            #     name=name,
            #     current_arg=args,
            #     check_perm=True)
    json_tools.save_to_path('./data/drift_bottles.json', bottles_dict)
    # with open('./data/drift_bottles.json', 'w', encoding='utf-8') as file:
    #     file.write(json.dumps(bottles_dict, ensure_ascii=False))