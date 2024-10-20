# 注册账号 或签到
from .xme_config import *
from .classes.user import *
from .classes.database import *
from nonebot import log
import random
import config
from nonebot import on_command, CommandSession

register_alias = ["reg", "r"]
@on_command('register', aliases=register_alias, only_to_me=True, permission=lambda x: x.from_group(config.GROUPS_WHITELIST))
async def _(session: CommandSession):
    """注册或签到"""
    user_id = session.event.user_id
    nickname = (await session.bot.get_group_member_info(group_id=session.event.group_id, user_id=user_id))['nickname']
    database = Xme_database("./data/xme/xme.db")
    users = User.load_user(database, "id", user_id)
    print(users)
    suffix = ""
    if len(users) < 1:
        user = User(database, user_id, nickname)
        suffix = "\n顺便帮你注册了账号哦 owo"
    else:
        user = users[0]
    curr_coins = user.coins
    if user.register():
        coins = user.coins - curr_coins
        coins_message = f"总共拥有 {user.coins} 枚虚拟星币哦 {'owo' if user.coins >= 10 else 'uwu'}" if user.coins > 0 else f"没有任何的虚拟星币 uwu"
        reg_message = f"你获得了 {coins} 枚虚拟星币！" if coins > 0 else f"你没获得任何虚拟星币..."
        message = f"[CQ:at,qq={user_id}] 签到成功~ {reg_message}\n你当前{coins_message}{suffix}"
    else:
        message = f"[CQ:at,qq={user_id}] 你今天已经签到过了哦 ovo"
    await session.send(message)