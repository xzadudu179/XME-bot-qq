__plugin_name__ = 'shop'
from xme.plugins.commands.xme_user.classes.user import User, using_user
import random
from .classes.good import Good
# from .classes.coin_shop import CoinShop
from .static.shop import SHOP

from xme.xmetools.msgtools import send_session_msg, aget_arg
from xme.xmetools.msgtools import image_msg
from xme.xmetools.cmdtools import use_args
from nonebot import CommandSession
from xme.xmetools.plugintools import on_command
from xme.xmetools.imgtools import get_html_image
from xme.xmetools.doctools import CommandDoc
from character import get_message
random.seed()

alias = ["星币商店" , "商店"]

__plugin_usage__= CommandDoc(
    name=__plugin_name__,
    desc=get_message("plugins", __plugin_name__, 'desc'),
    introduction=get_message("plugins", __plugin_name__, 'introduction'),
    usage='<物品序号> <确认购买(y)>',
    permissions=[],
    alias=alias
)

@on_command(__plugin_name__, aliases=alias, only_to_me=False, permission=lambda _: True)
@using_user(save_data=True)
@use_args(arg_len=2)
async def _(session: CommandSession, arg_list, user: User):
    serial, is_buy = arg_list
    reply = "y" if is_buy in ['y', 'Y'] else None
    # serial = session.current_arg_text.strip()
    if not serial:
        # 默认展示商店
        img = get_html_image(SHOP.get_html_card(user))
        return await send_session_msg(session, get_message("plugins", __plugin_name__, "shop_card", image=await image_msg(img)), tips=True)

    # 有参数情况下
    good: Good | None = SHOP.get_good_from_serial(serial)
    if good is None:
        return await send_session_msg(session, get_message("plugins", __plugin_name__, "no_good", serial=serial), tips=True)

    # 有商品情况下
    good_image = get_html_image(good.get_html_information())
    good_img_msg = await image_msg(good_image)
    if good.is_user_bought(user):
        return await send_session_msg(session, get_message("plugins", __plugin_name__, "good_card_bought", image=good_img_msg), tips=True)

    # 未购买时
    if reply is None:
        await send_session_msg(session, get_message("plugins", __plugin_name__, "good_card", image=good_img_msg, price=good.price))
        reply = await aget_arg(
            session,
            prompt="",
            rules=lambda r: r in ['y', 'Y'],
            can_use_cmd=True
        )
    if reply == "CMD_END":
        return False
    if reply not in ['y', 'Y']:
        return False
    result = await good.buy(session, user)
    return result