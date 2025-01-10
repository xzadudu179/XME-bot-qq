from .tools.find_item import *
from .xme_config import *
from .classes.user import *
from .classes.database import *
import config
from nonebot import on_command, CommandSession
from .tools.pre_checks import *

show_inv_alias = ["inv", "物品栏"]
@on_command('showinv', aliases=show_inv_alias, only_to_me=True, permission=lambda x: x.from_group(config.GROUPS_WHITELIST))
@pre_check() # 执行前检查
async def _(session: CommandSession, user: User):
    """展示用户物品栏"""
    inv = [item.split(",") for item in str(user.inventory).split("|")]
    message = f"{user.name}，以下是你的物品栏 owo：\n"
    has_item = False
    for i, item in enumerate(inv):
        item_info = find_item_by_id(item[0])
        if not item_info:
            continue
        has_item = True
        item_info = item_info.name
        message += f"{i + 1}.\t{item_info} *{item[1]}\n"
    if not has_item:
        message += "唔，好像什么也没有...\n"
    # else:
        # message += "使用 xme.drop [物品栏编号] <数量> 来扔掉物品哦~"
    await send_session_msg(session, message)