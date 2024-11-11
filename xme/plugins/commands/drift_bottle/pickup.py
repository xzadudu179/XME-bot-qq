from xme.xmetools.date_tools import *
from xme.xmetools.command_tools import send_cmd, find_command_by_args
import keys
from xme.xmetools import json_tools
import json
from xme.xmetools import random_tools
import random
from nonebot import on_command, CommandSession
import config

pickup_alias = ["捡瓶子", "捡漂流瓶", "捡瓶", "pick"]


@on_command('pickup', aliases=pickup_alias, only_to_me=False)
async def _(session: CommandSession):
    user_id = session.event.user_id
    bottles_dict = json_tools.read_from_path('./data/drift_bottles.json')
    bottles = bottles_dict['bottles']
    # 没捡到瓶子
    if len(bottles) < 1:
        await session.send("海里一个瓶子里都没有...")
        return
    pickedup = random_tools.random_percent(90)
    if not pickedup:
        await session.send("你没有捡到瓶子ovo")
        return

    print("捡瓶子中")
    # print(bottles)
    # bottle = random.choice(bottles)
    index, bottle = random.choice(list(bottles.items()))
    # 增加浏览量以及构造卡片
    # ----------------------------
    view_message = f"被捡到了{bottle['views'] + 1}次" if (bottle['views'] + 1) > 1 else f"第一次被捡到"
    bottle['views'] += 1
    like_message = f"获得了{bottle['likes']}个赞owo" if bottle['likes'] > 0 else f"还没有任何赞ovo"
    bottle_card = f"[CQ:at,qq={user_id}] 你捡到了一个漂流瓶~\n[#{index}号漂流瓶，来自 \"{bottle['from_group']}\"]：\n-----------\n{bottle['content']}\n-----------\n由 \"{bottle['sender']}\" 在{bottle['send_time']} 投出\n这个瓶子{view_message}，{like_message}"
    if str(index) == keys.ERROR_BOTTLE_INDEX:
        bottle_card = f"[CQ:at,qq={user_id}] 你捡?到了一个漂流..??瓶..?\n[#{index}号?...瓶，来..自. \"{bottle['from_group']}\"]..：\n-----------\n{bottle['content']}\n-----------\n由 \"{bottle['sender']}\" 在{bottle['send_time']} [生成]\n这...个..{view_message}，{like_message} uwu"
    # ----------------------------
    # 手滑摔碎了瓶子
    broken = random_tools.random_percent(3)
    if not broken:
        if str(index) == keys.ERROR_BOTTLE_INDEX:
            bottle_card += keys.ERROR_BOTTLE_INFO_MSG
        else:
            bottle_card += f"\n你可以马上发送 \"-like\" 以点赞，或发送 \"-rep\" 以举报。"
    # 保存防止消息没发出来
    print("保存中")
    json_tools.save_to_path('./data/drift_bottles.json', bottles_dict)
    await session.send(bottle_card)
    print("捡到了瓶子")
    content = ""
    if broken:
        content = f"[CQ:at,qq={user_id}] 啊，你不小心把瓶子摔碎了..."
        if str(index) == keys.ERROR_BOTTLE_INDEX:
            content = keys.ERROR_BOTTLE_BROKE_MSG
        await session.send(content)
        if str(index) != keys.ERROR_BOTTLE_INDEX:
            bottles_dict = json_tools.read_from_path('./data/drift_bottles.json')
            del bottles_dict['bottles'][index]
            print("瓶子碎了")
            print("保存文件中")
            json_tools.save_to_path('./data/drift_bottles.json', bottles_dict)
        return
    elif str(index) == keys.ERROR_BOTTLE_INDEX:
        print("保存中")
        json_tools.save_to_path('./data/drift_bottles.json', bottles_dict)
        return
    else:
        for _ in range(3):
            # 处理之后可能的输入
            # 重新读取
            print("重新读取")
            bottles_dict = json_tools.read_from_path('./data/drift_bottles.json')
            # print("保存文件中")
            # # print(bottle)
            # json_tools.save_to_path('./data/drift_bottles.json', bottles_dict)
            reply = (await session.aget()).strip()
            print(find_command_by_args(reply))
            print(reply)
            if reply == '-like':
                # 重新读取
                content = f"[CQ:at,qq={user_id}] 点赞成功~"
                bottles_dict['bottles'][index]['likes'] += 1
                print("点赞了")
                print(bottles_dict['bottles'][index])
                print("保存文件中")
                # print(bottle)
                json_tools.save_to_path('./data/drift_bottles.json', bottles_dict)
                await session.send(content)
                return
            elif reply == '-rep':
                content = f"[CQ:at,qq={user_id}] 举报成功"
                for superuser in config.SUPERUSERS:
                    await session.bot.send_private_msg(user_id=superuser,message=f"{(await session.bot.get_group_member_info(group_id=session.event.group_id, user_id=user_id))['nickname']} ({user_id}) 举报了一个漂流瓶，瓶子信息如下：\n内容：\n-----------\n{bottle['content']}\n-----------\nIndex: {index}\n发送者: {bottle['sender']} ({bottle['sender_id']})\n来自群：{bottle['from_group']} ({bottle['group_id']})")
                await session.send(content)
                return
            elif find_command_by_args(reply) != False:
                print("执行指令")
                # if find_command_by_args(reply).name[0] == "wife":
                #     await session.send("注意：你在 pickup 指令的后面 3 句话内执行了 wife 指令，会默认显示我的老婆 uwu")
                await send_cmd(reply, session)
                return
            # 重新读取
            # bottles_dict = json_tools.read_from_path('./data/drift_bottles.json')
    # print("重新读取")
    # bottles_dict = json_tools.read_from_path('./data/drift_bottles.json')
    print("保存文件中")
    print(bottles_dict['bottles'][index])
    # print(bottle)
    json_tools.save_to_path('./data/drift_bottles.json', bottles_dict)
    # await session.send(content)