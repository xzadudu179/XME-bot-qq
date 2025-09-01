from xme.xmetools.timetools import *
from xme.plugins.commands.drift_bottle import __plugin_name__
from xme.xmetools import jsontools
from xme.xmetools.bottools import permission
from .tools.bottlecard import get_bottle_card_html, get_card_image
from xme.xmetools.imgtools import image_msg
from character import get_message
from xme.xmetools import randtools
import random
from nonebot import on_command, CommandSession
from xme.xmetools.msgtools import send_session_msg
from . import DriftBottle

check_alias = ["检查"]
command_name = "check"
TIMES_LIMIT = 1
BOTTLE_PATH = './data/drift_bottles.json'

@on_command(command_name, aliases=check_alias, only_to_me=False, permission=lambda _: True)
@permission(lambda sender: sender.is_superuser, permission_help="是 SUPERUSER")
async def _(session: CommandSession):
    random.seed()
    # user_id = session.event.user_id
    bottle_id = session.current_arg_text.strip()
    # bottles_dict = jsontools.read_from_path(BOTTLE_PATH)
    # bottles = bottles_dict['bottles']
    # is_special_bottle = randtools.random_percent(0.5)
    bottle: DriftBottle = DriftBottle.get(bottle_id)
    # for i, b in bottles.items():
        # if i == bottle_id:
            # index, bottle = i, b
    # index, bottle = [i, b for i, b in bottles.items() if b['']]
    if not bottle:
        return await send_session_msg(session, "这个编号没有瓶子哦")
    index = bottle.bottle_id
    print("捡到了瓶子")
    index_is_int = index.isdigit()
    # 混乱值根据浏览量计算
    messy_rate: float = min(100, max(0, bottle.views * 2 - bottle.likes * 3)) if index_is_int or index != '-179' else 0
    # 增加浏览量以及构造卡片
    # ----------------------------
    # view_message = get_message("plugins", __plugin_name__, "view_message", times=bottle['views'] + 1) if (bottle['views'] + 1) > 1 else get_message("plugins", __plugin_name__, "no_view_message", times=bottle['views'] + 1)
    # jsontools.change_json(BOTTLE_PATH, 'bottles', index, 'views', set_method=lambda v: v + 1)
    # like_message = get_message("plugins", __plugin_name__, "like_message", count=bottle['likes']) if bottle['likes'] > 0 else get_message("plugins", __plugin_name__, "no_like_message", count=bottle['likes'])
    messy_rate_string = ""
    if index == '-179':
        messy_rate_string = "##未知##"
        messy_rate = random.randint(0, 100)
    elif not index_is_int:
        messy_rate_string = "##纯洁无暇##"
        messy_rate = 0
    else:
        messy_rate_string = f"{messy_rate}%"
    # sender_now = await get_stranger_name(bottle['sender_id'])
    # group_now = await get_group_name(bottle['group_id'])
    suffix = ""

    # 手滑摔碎了瓶子
    # 越混乱的瓶子越容易摔碎
    broken_rate = min(100, 1 + messy_rate / 2.5) * 0.65 if messy_rate < 100 else 100
    print(f"混乱程度：{messy_rate}, 破碎概率：{broken_rate}%")
    # broken = randtools.random_percent(broken_rate)
    # if index_is_int and str(index) != "-179":
    #     # 普通瓶子会越来越混乱
    #     bottle_card = randtools.messy_string(bottle_card, messy_rate)
    if str(index) == "-179":
        # bottle_card += "\n" + get_message("plugins", __plugin_name__, "response_prompt_broken")
        suffix = f'<p style="color: #D40"> -{get_message("plugins", __plugin_name__, "response_prompt_broken")}- </p>'
    bottle_card = get_card_image(get_bottle_card_html(
        id=index,
        messy_rate_str=messy_rate_string,
        messy_rate=messy_rate,
        date=bottle.send_time,
        content=bottle.content,
        sender=bottle.sender,
        group=bottle.from_group,
        views=bottle.views + 1,
        likes=bottle.likes,
        comments_list=bottle.comments,
        custom_suffix=suffix,
    ))
    # await send_session_msg(session, bottle_card)
    await send_session_msg(session, (await image_msg(bottle_card)), tips=True)