# 注册账号 或签到
from .xme_config import *
from .classes.user import *
from .classes.database import *
import config
from nonebot import on_command, CommandSession
from .tools.pre_checks import *

register_alias = ["reg", "r", "签到"]
@on_command('register', aliases=register_alias, only_to_me=True, permission=lambda x: x.from_group(config.GROUPS_WHITELIST))
@pre_check() # 执行前检查
async def _(session: CommandSession, user: User):
    """签到"""
    user_id = session.event.user_id
    suffix = ""
    curr_coins = user.coins
    if user.register():
        coins = user.coins - curr_coins
        coins_message = f"总共拥有 {user.coins} 枚虚拟星币哦 {'owo' if user.coins >= 10 else 'uwu'}" if user.coins > 0 else f"没有任何的虚拟星币 uwu"
        reg_message = f"你获得了 {coins} 枚虚拟星币！" if coins > 0 else f"你没获得任何虚拟星币..."
        message = f"[CQ:at,qq={user_id}] 签到成功~ {reg_message}\n你当前{coins_message}{suffix}"
    else:
        message = f"[CQ:at,qq={user_id}] 你今天已经签到过了哦 ovo"
    await session.send(message)