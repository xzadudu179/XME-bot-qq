from xme.xmetools.time_tools import *
from xme.plugins.commands.drift_bottle import __plugin_name__
from xme.xmetools.command_tools import send_cmd, get_cmd_by_alias
from xme.xmetools import json_tools
from character import get_message
from xme.xmetools import random_tools
import random
from nonebot import on_command, CommandSession
from xme.xmetools.command_tools import send_session_msg
import config

pickup_alias = ["捡瓶子", "捡漂流瓶", "捡瓶", "pick"]
command_name = "pickup"

@on_command(command_name, aliases=pickup_alias, only_to_me=False)
async def _(session: CommandSession):
    user_id = session.event.user_id
    # at = f"[CQ:at,qq={user_id}]"
    bottles_dict = json_tools.read_from_path('./data/drift_bottles.json')
    bottles = bottles_dict['bottles']
    print("捡瓶子中")
    # 没捡到瓶子
    if len(bottles) < 1:
        await send_session_msg(session, get_message(__plugin_name__, "no_bottle"))
        # await send_msg(session, "海里一个瓶子里都没有...")
        return
    pickedup = random_tools.random_percent(90)
    if not pickedup:
        await send_session_msg(session, get_message(__plugin_name__, "no_bottle_picked"))
        # await send_msg(session, "你没有捡到瓶子ovo")
        return

    # print(bottles)
    # bottle = random.choice(bottles)
    index, bottle = random.choice(list(bottles.items()))
    print("捡到了瓶子")
    index_is_int = True
    try:
        int(index)
    except Exception as ex:
        print(f"因为 {ex} 所以瓶子 id 不是整数")
        index_is_int = False
    # 混乱值根据浏览量计算
    messy_rate: float = min(100, max(0, bottle['views'] * 2 - bottle['likes'] * 3)) if index_is_int or str(index) != '-179' else 0
    # 增加浏览量以及构造卡片
    # ----------------------------
    view_message = get_message(__plugin_name__, "view_message", times=bottle['views'] + 1) if (bottle['views'] + 1) > 1 else get_message(__plugin_name__, "no_view_message", times=bottle['views'] + 1)
    # view_message = f"被捡到了{bottle['views'] + 1}次" if (bottle['views'] + 1) > 1 else f"第一次被捡到"
    bottle['views'] += 1
    like_message = get_message(__plugin_name__, "like_message", count=bottle['likes']) if bottle['likes'] > 0 else get_message(__plugin_name__, "no_like_message", count=bottle['likes'])
    # like_message = f"获得了{bottle['likes']}个赞owo" if bottle['likes'] > 0 else f"还没有任何赞ovo"
    messy_rate_string = ""
    if str(index) == '-179':
        messy_rate_string = "##未知##"
    elif not index_is_int:
        messy_rate_string = "##纯洁无暇##"
    else:
        messy_rate_string = f"{messy_rate}%"
    bottle_card = get_message(__plugin_name__, "bottle_card_content",
        index=index,
        messy_rate=messy_rate_string,
        from_group=bottle['from_group'],
        content=bottle['content'],
        sender=bottle['sender'],
        send_time=bottle['send_time'],
        view_message=view_message,
        like_message=like_message
    )
    # bottle_card = f"{at} 你捡到了一个漂流瓶~\n[#{index}号漂流瓶，来自 \"{bottle['from_group']}\"]：\n-----------\n{bottle['content']}\n-----------\n由 \"{bottle['sender']}\" 在{bottle['send_time']} 投出\n这个瓶子{view_message}，{like_message}"
    # 彩蛋瓶子
    if str(index) == "-179":
        bottle_card = random_tools.messy_string(bottle_card, 35)
    # elif index_is_int:
    #     # 普通瓶子会越来越混乱
    #     bottle_card = random_tools.messy_string(bottle_card, messy_rate)
    # ----------------------------
    # 拼接回复
    #     bottle_card = f"{at} 你捡?到了一个漂流..??瓶..?\n[#{index}号?...瓶，来..自. \"{bottle['from_group']}\"]..：\n-----------\n{bottle['content']}\n-----------\n由 \"{bottle['sender']}\" 在{bottle['send_time']} [生成]\n这...个..{view_message}，{like_message} uwu"
    # ----------------------------
    # 手滑摔碎了瓶子
    # 越混乱的瓶子越容易摔碎
    print(f"混乱程度：{messy_rate}%")
    broken = random_tools.random_percent(min(100, 1 + messy_rate / 2) if messy_rate < 100 else 100)
    if index_is_int and str(index) != "-179":
        # 普通瓶子会越来越混乱
        bottle_card = random_tools.messy_string(bottle_card, messy_rate)
    if not broken:
        if str(index) == "-179":
            bottle_card += "\n" + get_message(__plugin_name__, "response_prompt_broken")
            # bottle_card += f"\n你[不]可以..发送 \"-li??\" 以点赞?，或.?发送 \"-??p\" 以...?。"
        else:
            bottle_card += "\n" + get_message(__plugin_name__, "response_prompt")
            # bottle_card += f"\n你可以马上发送 \"-like\" 以点赞，或发送 \"-rep\" 以举报。"
    # 保存防止消息没发出来
    print("保存中")
    json_tools.save_to_path('./data/drift_bottles.json', bottles_dict)
    await send_session_msg(session, bottle_card)
    content = ""
    if broken:
        content = get_message(__plugin_name__, "bottle_broken")
        if messy_rate == 100:
            content = get_message(__plugin_name__, "bottle_broken_messy")
        # content = f"{at} 啊，你不小心把瓶子摔碎了..."
        if str(index) != "-179":
            bottles_dict = json_tools.read_from_path('./data/drift_bottles.json')
            del bottles_dict['bottles'][index]
            print("瓶子碎了")
            print("保存文件中")
            json_tools.save_to_path('./data/drift_bottles.json', bottles_dict)
        elif str(index) == "-179" or not index_is_int:
            # print("保存中")
            print("瓶子碎了？")
            content = get_message(__plugin_name__, "bottle_broken?")
            # content = "啊，你不小心把瓶子摔...咦？这个瓶子自己修复了，然后它飞回了海里..."
            # json_tools.save_to_path('./data/drift_bottles.json', bottles_dict)
        await send_session_msg(session, content)
        return
    elif str(index) != "-179":
        for _ in range(3):
            # 处理之后可能的输入
            # 重新读取
            print("重新读取")
            bottles_dict = json_tools.read_from_path('./data/drift_bottles.json')
            # print("保存文件中")
            # # print(bottle)
            # json_tools.save_to_path('./data/drift_bottles.json', bottles_dict)
            reply = (await session.aget()).strip()
            print(get_cmd_by_alias(reply))
            print(reply)
            if reply == '-like':
                # 重新读取
                content = get_message(__plugin_name__, "liked")
                # content = f"{at} 点赞成功~"
                bottles_dict['bottles'][index]['likes'] += 1
                print("点赞了")
                print(bottles_dict['bottles'][index])
                print("保存文件中")
                # print(bottle)
                json_tools.save_to_path('./data/drift_bottles.json', bottles_dict)
                await send_session_msg(session, content)
                return
            elif reply == '-rep':
                content = get_message(__plugin_name__, "reported")
                # content = f"{at} 举报成功"
                for superuser in config.SUPERUSERS:
                    await session.bot.send_private_msg(user_id=superuser,message=f"{(await session.bot.get_group_member_info(group_id=session.event.group_id, user_id=user_id))['nickname']} ({user_id}) 举报了一个漂流瓶，瓶子信息如下：\n内容：\n-----------\n{bottle['content']}\n-----------\nid: {index}\n发送者: {bottle['sender']} ({bottle['sender_id']})\n来自群：{bottle['from_group']} ({bottle['group_id']})")
                await send_session_msg(session, content)
                return
            elif get_cmd_by_alias(reply) != False:
                print("执行指令")
                # if find_command_by_args(reply).name[0] == "wife":
                #     await send_msg(session, "注意：你在 pickup 指令的后面 3 句话内执行了 wife 指令，会默认显示我的老婆 uwu")
                await send_cmd(reply, session)
                return
    else:
        # 彩蛋瓶子直接返回
        return
            # 重新读取
            # bottles_dict = json_tools.read_from_path('./data/drift_bottles.json')
    # print("重新读取")
    # bottles_dict = json_tools.read_from_path('./data/drift_bottles.json')
    print("保存文件中")
    print(bottles_dict['bottles'][index])
    # print(bottle)
    json_tools.save_to_path('./data/drift_bottles.json', bottles_dict)
    # await send_msg(session, content)