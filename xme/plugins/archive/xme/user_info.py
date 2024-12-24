
from .xme_config import *
from .classes.user import *
from .classes.database import *
import config
from nonebot import on_command, CommandSession
from .tools.pre_checks import *

user_info_alias = ["info", "用户信息"]
@on_command('userinfo', aliases=user_info_alias, only_to_me=True, permission=lambda x: x.from_group(config.GROUPS_WHITELIST))
@pre_check() # 执行前检查
async def _(session: CommandSession, user: User):
    """展示用户信息"""
    info = str(user)
    await send_msg(session, info)