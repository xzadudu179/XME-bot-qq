from xme.xmetools.timetools import *
from xme.plugins.commands.drift_bottle import __plugin_name__
from xme.xmetools.cmdtools import send_cmd, get_cmd_by_alias
from xme.xmetools import jsontools
from xme.plugins.commands.xme_user.classes import user as u
from xme.xmetools.bottools import get_stranger_name, get_group_name
from character import get_message
from xme.xmetools import randtools
import random
random.seed()
from nonebot import on_command, CommandSession
from xme.xmetools.msgtools import send_session_msg
import config

BOTTLE_PATH = './data/drift_bottles.json'
pickup_alias = ["捡瓶子", "捡漂流瓶", "捡瓶", "pick"]
command_name = "pickup"

async def like(session, bottles_dict, index):
    content = get_message("plugins", __plugin_name__, "liked")
    jsontools.change_json(BOTTLE_PATH, 'bottles', index, 'likes', set_method=lambda v: v + 1)
    print("点赞了")
    print(bottles_dict['bottles'][index])
    await send_session_msg(session, content)
    return

async def like(session, bottles_dict, index):
    content = get_message("plugins", __plugin_name__, "liked")
    jsontools.change_json(BOTTLE_PATH, 'bottles', index, 'likes', set_method=lambda v: v + 1)
    print("点赞了")
    print(bottles_dict['bottles'][index])
    await send_session_msg(session, content)
    return

async def report(session, bottle, index, user_id, message_prefix="举报了一个漂流瓶", send_success_message=True):
    content = get_message("plugins", __plugin_name__, "reported")
    for superuser in config.SUPERUSERS:
        await session.bot.send_private_msg(user_id=superuser,message=f"{(await session.bot.get_group_member_info(group_id=session.event.group_id, user_id=user_id))['nickname']} ({user_id}) {message_prefix}，瓶子信息如下：\n内容：\n-----------\n{bottle['content']}\n-----------\nid: {index}\n发送者: {bottle['sender']} ({bottle['sender_id']})\n来自群：{bottle['from_group']} ({bottle['group_id']})")
    if send_success_message:
        await send_session_msg(session, content)

@on_command(command_name, aliases=pickup_alias, only_to_me=False)
@u.using_user(save_data=False)
@u.limit(command_name, 1, get_message("plugins", __plugin_name__, 'limited'), unit=TimeUnit.HOUR, count_limit=20)
async def _(session: CommandSession, user: u.User):
    random.seed()
    user_id = session.event.user_id
    bottles_dict = jsontools.read_from_path(BOTTLE_PATH)
    bottles = bottles_dict['bottles']
    print("捡瓶子中")
    # 没捡到瓶子
    if len(bottles) < 1:
        await send_session_msg(session, get_message("plugins", __plugin_name__, "no_bottle"))
        # await send_msg(session, "海里一个瓶子里都没有...")
        return False
    pickedup = randtools.random_percent(90)
    if not pickedup:
        await send_session_msg(session, get_message("plugins", __plugin_name__, "no_bottle_picked"))
        # await send_msg(session, "你没有捡到瓶子ovo")
        return False
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
    view_message = get_message("plugins", __plugin_name__, "view_message", times=bottle['views'] + 1) if (bottle['views'] + 1) > 1 else get_message("plugins", __plugin_name__, "no_view_message", times=bottle['views'] + 1)
    jsontools.change_json(BOTTLE_PATH, 'bottles', index, 'views', set_method=lambda v: v + 1)
    like_message = get_message("plugins", __plugin_name__, "like_message", count=bottle['likes']) if bottle['likes'] > 0 else get_message("plugins", __plugin_name__, "no_like_message", count=bottle['likes'])
    messy_rate_string = ""
    if str(index) == '-179':
        messy_rate_string = "##未知##"
        messy_rate = random.randint(0, 100)
    elif not index_is_int:
        messy_rate_string = "##纯洁无暇##"
        messy_rate = 0
    else:
        messy_rate_string = f"{messy_rate}%"
    sender_now = await get_stranger_name(bottle['sender_id'])
    group_now = await get_group_name(bottle['group_id'])
    bottle_card = get_message("plugins", __plugin_name__, "bottle_card_content",
        index=index,
        messy_rate=messy_rate_string,
        from_group=bottle['from_group'],
        group_now=f" (现 '{group_now}')" if group_now != bottle['from_group'] and group_now else "" ,
        content=bottle['content'],
        sender=bottle['sender'],
        sender_now=f" (现 '{sender_now}')" if sender_now != bottle['sender'] and sender_now else "",
        send_time=bottle['send_time'],
        view_message=view_message,
        like_message=like_message,
        comment_message="" if bottle['comments'] else "\n" + "", # TODO
    )
    # 彩蛋瓶子
    if str(index) == "-179":
        bottle_card = randtools.messy_string(bottle_card, 35)
    # 手滑摔碎了瓶子
    # 越混乱的瓶子越容易摔碎
    broken_rate = min(100, 1 + messy_rate / 2.5) * 0.65 if messy_rate < 100 else 100
    print(f"混乱程度：{messy_rate}, 破碎概率：{broken_rate}%")
    broken = randtools.random_percent(broken_rate)
    if index_is_int and str(index) != "-179":
        # 普通瓶子会越来越混乱
        bottle_card = randtools.messy_string(bottle_card, messy_rate)
    if not broken:
        if str(index) == "-179":
            bottle_card += "\n" + get_message("plugins", __plugin_name__, "response_prompt_broken")
        else:
            bottle_card += "\n" + get_message("plugins", __plugin_name__, "response_prompt")
    await send_session_msg(session, bottle_card)
    content = ""
    if broken:
        content = get_message("plugins", __plugin_name__, "bottle_broken")
        if messy_rate == 100:
            content = get_message("plugins", __plugin_name__, "bottle_broken_messy")
        if str(index) != "-179":
            broken_bottles = jsontools.read_from_path("./data/broken_bottles.json")
            broken_bottles[index] = bottle
            jsontools.save_to_path("./data/broken_bottles.json", broken_bottles)
            jsontools.change_json(BOTTLE_PATH, 'bottles', index, delete=True)
            print("瓶子碎了")
        elif str(index) == "-179" or not index_is_int:
            print("瓶子碎了？")
            content = get_message("plugins", __plugin_name__, "bottle_broken?")
        await send_session_msg(session, content)
        return True
    else:
        operated = {
            "like": False,
            "rep": False,
            "say": False,
            "pure": False,
        }
        while_index = 0
        while True:
            if while_index > 3:
                return True
            reply = (await session.aget()).strip()
            print(get_cmd_by_alias(reply))
            print(reply)
            if get_cmd_by_alias(reply) != False:
                print("执行指令")
                # 手动计数
                u.limit_count_tick(user, command_name)
                user.save()
                print("增加计数")
                await send_cmd(reply, session)
                return False
            elif reply == '-like' and not operated["like"]:
                operated["like"] = True
                await like(session, bottles_dict, index)
                continue
            elif reply == '-rep' and not operated["rep"]:
                operated["rep"] = True
                await report(session, bottle, index, user_id)
                continue
            elif reply.split(" ")[0] == '-say':
                continue
            elif reply.split(" ")[0] == '-pure':
                continue
            while_index += 1