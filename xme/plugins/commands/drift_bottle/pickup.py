from xme.xmetools.timetools import *
from xme.plugins.commands.drift_bottle import __plugin_name__
from xme.xmetools.cmdtools import send_cmd, get_cmd_by_alias
from xme.xmetools import jsontools
from . import get_messy_rate, get_random_broken_bottle
from xme.plugins.commands.xme_user.classes import user as u
from xme.xmetools.bottools import get_stranger_name, get_group_name
from .tools.bottlecard import get_class_bottle_card_html, get_pickedup_bottle_card
from xme.xmetools.imgtools import get_html_image
from xme.xmetools.imgtools import image_msg
from xme.xmetools.randtools import messy_image
from character import get_message
from xme.xmetools import randtools
import os
from . import DriftBottle, get_random_bottle
import random
random.seed()
from nonebot import on_command, CommandSession
from xme.xmetools.msgtools import send_session_msg, send_to_superusers, aget_session_msg
import config
from . import BOTTLE_IMAGES_PATH
# BOTTLE_PATH = './data/drift_bottles.json'
pickup_alias = ["捡瓶子", "捡漂流瓶", "捡瓶", "pick", 'p']
command_name = "pickup"

async def like(session, bottle_id):
    content = get_message("plugins", __plugin_name__, "liked")
    # jsontools.change_json(BOTTLE_PATH, 'bottles', index, 'likes', set_method=lambda v: v + 1)
    bottle = DriftBottle.get(bottle_id)
    bottle.likes += 1
    # bottle.update(lambda bottle: {
        # "likes": bottle.likes
    # })
    bottle.save()
    print("点赞了")
    # print(bottles_dict['bottles'][index])
    await send_session_msg(session, content)
    return

async def reset(session: CommandSession, user: u.User):
    _, count = u.get_limit_info(user, command_name)
    if count <= 0:
        await send_session_msg(session, get_message("plugins", __plugin_name__, "no_limit", count=count))
        return True

    price = count * 10
    result = await user.try_spend(session, price)
    if not result:
        return False
    u.reset_limit(user, command_name)
    await send_session_msg(session, get_message("plugins", __plugin_name__, "reset_limit", count=count))
    return True

async def likesay(session: CommandSession, bottle_id, comment_index: str, said):
    bottle = DriftBottle.get(bottle_id)
    index = bottle_id
    if not comment_index.isdigit():
        await send_session_msg(session, get_message("plugins", __plugin_name__, "like_comment_failed", id=comment_index, bottle=index))
        return False
    comment_index = int(comment_index)
    # 排除刚说完话就点赞自己的留言的情况
    if said and bottle.comments[comment_index -1] == bottle.comments[-1]:
        await send_session_msg(session, get_message("plugins", __plugin_name__, "like_comment_self"))
        return False
    if comment_index < 1 or comment_index > len(bottle.comments):
        await send_session_msg(session, get_message("plugins", __plugin_name__, "like_comment_failed", id=comment_index, bottle=index))
        return False
    # jsontools.change_json(BOTTLE_PATH, 'bottles', index, 'comments', set_method=lambda v: v[comment_index - 1]['likes'] + 1)
    bottle.comments[comment_index - 1]["likes"] += 1
    bottle.save()
    # bottle.update(lambda bottle: {
    #     "comments": bottle.comments
    # })
    # bottle.save()
    print("点赞了评论")
    print(bottle)
    await send_session_msg(session, get_message("plugins", __plugin_name__, "liked_comment", id=comment_index))
    return True

async def comment(session, bottle_id, user_id, comment_content):
    bottle = DriftBottle.get(bottle_id)
    index = bottle_id
    # index = bottle.bottle_id
    content = get_message("plugins", __plugin_name__, "commented", id=index)
    comment_content = comment_content.strip()
    if not comment_content:
        await send_session_msg(session, get_message("plugins", __plugin_name__, "no_content"))
        return False
    # try:
        # sender = (await session.bot.get_group_member_info(group_id=session.event.group_id, user_id=user_id))['nickname']
    # except ActionFailed:
    sender = (await session.bot.get_stranger_info(user_id=user_id))['nickname']

    MAX_COMMENT_LEN = 35
    if len(comment_content) > MAX_COMMENT_LEN:
        await send_session_msg(session, get_message("plugins", __plugin_name__, "comment_too_long", count=MAX_COMMENT_LEN, input_len=len(comment_content)))
        return False
    MAX_COMMENT_COUNT = 15
    if len(bottle.comments) > MAX_COMMENT_COUNT:
        await send_session_msg(session, get_message("plugins", __plugin_name__, "comment_too_many", count=MAX_COMMENT_COUNT))
        return False

    bottle.comments.append({
        "sender": sender,
        "sender_id": user_id,
        "content": comment_content,
        "likes": 0
    })
    bottle.save()
    print("评论了")
    for superuser in config.SUPERUSERS:
        await session.bot.send_private_msg(user_id=superuser,message=f"{sender} ({user_id}) 评论了 {index} 号漂流瓶：{comment_content}")
    print(bottle)
    await send_session_msg(session, content)
    return True

async def report(session, bottle: DriftBottle, user_id, message_prefix="举报了一个漂流瓶", send_success_message=True, report_content=""):
    content = get_message("plugins", __plugin_name__, "reported")
    messy_rate = max(0, min(100, bottle.views * 2 - bottle.likes * 3))
    card = await image_msg(get_html_image(get_class_bottle_card_html(bottle, 0, f"{messy_rate}%")))
    for superuser in config.SUPERUSERS:
        await session.bot.send_private_msg(user_id=superuser,message=f"{(await session.bot.get_group_member_info(group_id=session.event.group_id, user_id=user_id))['nickname']} ({user_id}) {message_prefix}，瓶子信息如下：{card}id: {bottle.bottle_id}\n发送者: {bottle.sender} ({bottle.sender_id})\n来自群：{bottle.from_group} ({bottle.group_id})\n（如果是举报）举报原因：{report_content}")
    if send_success_message:
        await send_session_msg(session, content)

@on_command(command_name, aliases=pickup_alias, only_to_me=False, permission=lambda _: True)
@u.using_user(save_data=False)
@u.custom_limit(command_name, 1, unit=TimeUnit.HOUR, count_limit=30)
# @permission(lambda x: x.is_groupchat, permission_help="在群聊内")
async def _(session: CommandSession, user: u.User, validate, count_tick):
    if session.current_arg_text == "reset":
        await reset(session, user)
        user.save()
        return True

    if validate():
        _, count = u.get_limit_info(user, command_name)
        await send_session_msg(session, get_message("plugins", __plugin_name__, 'limited', price=count * 10))
        return False
    random.seed()
    skin_name = user.get_custom_setting(__plugin_name__, "custom_cards")
    user_id = session.event.user_id
    # 普通瓶子
    # bottles_dict = jsontools.read_from_path(BOTTLE_PATH)
    # bottles = bottles_dict['bottles']
    table_name = DriftBottle.get_table_name()
    print("捡瓶子中")
    # 没捡到瓶子
    if not DriftBottle.exec_query(query=f"SELECT 1 FROM {table_name} WHERE is_broken != TRUE LIMIT 1", dict_data=True):
        await send_session_msg(session, get_message("plugins", __plugin_name__, "no_bottle"), linebreak=False)
        # await send_msg(session, "海里一个瓶子里都没有...")
        return False
    pickedup = randtools.random_percent(100)
    if not pickedup:
        await send_session_msg(session, get_message("plugins", __plugin_name__, "no_bottle_picked"))
        # await send_msg(session, "你没有捡到瓶子ovo")
        return False
    is_special_bottle = randtools.random_percent(1.32)
    # 幽灵瓶子 只在 23 点 ~ 3点出现
    is_broken_bottle = randtools.random_percent(1.2) if (datetime.now().hour < 4 or datetime.now().hour >= 22) else False
    is_cthulhu_bottle = randtools.random_percent(0.7)
    print("时间段", (datetime.now().hour < 4 or datetime.now().hour >= 22))
    print("isbroken", is_broken_bottle)
    if is_broken_bottle:
        broken = get_random_broken_bottle()
    else:
        broken = None
    special = DriftBottle.exec_query(query=
    f"""SELECT * FROM {table_name}
    WHERE (CAST(bottle_id AS TEXT) != CAST(bottle_id AS INTEGER) OR bottle_id == "-179") AND is_broken != TRUE
    AND bottle_id NOT LIKE '%PURE%'""", dict_data=True)
    # print(random.choice(special))
    have_special_bottle = False
    # bottle: DriftBottle = DriftBottle.form_dict(DriftBottle.exec_query(query=f"SELECT * FROM {table_name} ORDER BY RANDOM() LIMIT 1", dict_data=True)[0])
    bottle: DriftBottle = get_random_bottle()
    if is_cthulhu_bottle:
        from . import ERROR_BOTTLE
        bottle = ERROR_BOTTLE
    if not bottle.bottle_id.isdigit() or bottle.bottle_id == '-179':
        is_special_bottle = True
        have_special_bottle
    if is_broken_bottle:
        bottle = broken
        print("捡到了碎瓶子")
        bottle.skin = "幽灵"
        await user.achieve_achievement(session, "幽灵瓶")
        await send_to_superusers(session.bot, f"用户 \"{await get_stranger_name(session.event.user_id)}\" 在群 \"{await get_group_name(session.event.group_id)}\" 中捡到了一个幽灵瓶子~")
    elif is_special_bottle and special or have_special_bottle and not is_broken_bottle:
        if not have_special_bottle:
            # print(random.choice(special))
            bottle: DriftBottle = DriftBottle.form_dict(random.choice(special))
        print("捡到了彩蛋瓶子")
        await user.achieve_achievement(session, "彩蛋瓶")
        if bottle.bottle_id in ["550W", "MOSS"]:
            await user.achieve_achievement(session, "MOSS")
        elif bottle.bottle_id in ["CTHULHU", "CTHULHU-2"]:
            await user.achieve_achievement(session, "蠕动的血肉")
        await send_to_superusers(session.bot, f"用户 \"{await get_stranger_name(session.event.user_id)}\" 在群 \"{await get_group_name(session.event.group_id)}\" 中捡到了一个彩蛋瓶子~")
    else:
        # bottle: DriftBottle = DriftBottle.form_dict(DriftBottle.exec_query(query=f"SELECT * FROM {table_name} ORDER BY RANDOM() LIMIT 1", dict_data=True)[0])
        print(bottle)
        if bottle.sender_id == session.event.user_id and bottle.views == 0:
            await user.achieve_achievement(session, "回旋瓶")
        print("捡到了瓶子")
    # 瓶子自己的皮肤
    if bottle.skin:
        skin_name = bottle.skin
    index = bottle.bottle_id
    index_is_int = index.isdigit()


    # 增加浏览量以及构造卡片
    # ----------------------------
    if not is_broken_bottle:
        bottle.views += 1
        bottle.save()

    # suffix = ""
    messy_rate, _ = get_messy_rate(bottle, view_minus=1)

    # 手滑摔碎了瓶子
    # 越混乱的瓶子越容易摔碎
    broken_rate = min(100, 0.5 + messy_rate / 3) if messy_rate < 100 else 100
    if is_special_bottle:
        broken_rate = random.randint(5, 20)
    print(f"混乱程度：{messy_rate}, 破碎概率：{broken_rate}%")
    broken = randtools.random_percent(broken_rate)
    #     # 普通瓶子会越来越混乱
    bottle_card = get_pickedup_bottle_card(bottle, skin_name=skin_name, view_minus=1)
    # await send_session_msg(session, bottle_card)
    prefix_message = get_message("plugins", __plugin_name__, "bottle_picked_prefix")
    if is_broken_bottle:
        prefix_message = get_message("plugins", __plugin_name__, "bottle_picked_prefix_broken")
    await send_session_msg(session, prefix_message + (await image_msg(bottle_card)), linebreak=False, tips=True)
    if is_broken_bottle:
        print("破碎的瓶子直接返回")
        count_tick()
        return False
    content = ""
    if broken:
        await user.achieve_achievement(session, "混乱不堪")
        content = get_message("plugins", __plugin_name__, "bottle_broken")
        if messy_rate >= 100:
            content = get_message("plugins", __plugin_name__, "bottle_broken_messy")
            await user.achieve_achievement(session, "章鱼的诅咒...")
        # 被举报混乱的瓶子浏览量大于 114514，点赞小于 2000 是防止极端情况
        if bottle.views >= 114514 and bottle.likes < 2000 and messy_rate >= 100:
            # 删除被举报的瓶子
            if len(bottle.images) > 0:
                # 删除所有图片
                for i in bottle.images:
                    print("删除图片", BOTTLE_IMAGES_PATH + i)
                    try:
                        os.remove(BOTTLE_IMAGES_PATH + i)
                    except FileNotFoundError:
                        continue
            try:
                DriftBottle.exec_query(query=f"DELETE FROM {table_name} WHERE id=={bottle.id} AND views>=114514 AND likes<2000")
            except:
                pass
            await send_session_msg(session, content)
            return True
        if str(index) == "-179" or not index_is_int:
            print("瓶子碎了？")
            await user.achieve_achievement(session, "纯洁无暇！")
            content = get_message("plugins", __plugin_name__, "bottle_broken?")
        elif index != "-179":
            broken_bottles = jsontools.read_from_path("./data/broken_bottles.json")
            broken_bottles[index] = bottle.to_dict()
            # jsontools.save_to_path("./data/broken_bottles.json", broken_bottles)
            # jsontools.change_json(BOTTLE_PATH, 'bottles', index, delete=True)
            bottle.remove_self()
            print("瓶子碎了")

        await send_session_msg(session, content)
        count_tick()
        return True
    else:
        operated = {
            "like": False,
            "rep": False,
            "say": False,
            "pure": False,
            "likesay": False,
        }
        while_index = 0
        while True:
            if while_index > 4:
                return True
            async def cmd_func(reply):
                print("执行指令")
                # 手动计数，防止递归调用不计数问题
                u.limit_count_tick(user, command_name)
                user.save()
                print("增加计数")
                await send_cmd(reply, session)
                return "CMD_OVER"
            reply = await aget_session_msg(session=session, can_use_command=True, command_func=cmd_func)
            if reply == "CMD_OVER":
                return False
            if reply == '-like' and not operated["like"]:
                operated["like"] = True
                await like(session, bottle.bottle_id)
                continue
            elif reply.split(" ")[0] == '-rep' and not operated["rep"]:
                operated["rep"] = True
                await report(session, bottle, user_id, report_content=reply.split(" ")[1] if len(reply.split(" ")) > 1 else "")
                continue
            elif reply.split(" ")[0] == '-say' and not operated["say"]:
                result = await comment(session, bottle.bottle_id, user_id, " ".join(reply.split(" ")[1:]))
                if result:
                    operated["say"] = True
                continue
            elif reply.split(" ")[0] == '-pure'  and not operated["pure"]:
                operated["pure"] = True
                await report(session, bottle, user_id, "申请了一个纯洁无暇的漂流瓶", False)
                await send_session_msg(session, get_message("plugins", __plugin_name__, "pured"))
                continue
            elif reply.split(" ")[0] == '-likesay' and not operated["likesay"]:
                result = await likesay(session, bottle.bottle_id, " ".join(reply.split(" ")[1:]).strip(), operated["say"])
                if result:
                    operated["likesay"] = True
                continue
            while_index += 1
    count_tick