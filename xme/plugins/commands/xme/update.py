# 更新数据
from .xme_config import *
from .classes.user import *
from .classes.database import *
from nonebot import log
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