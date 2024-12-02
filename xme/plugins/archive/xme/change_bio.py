
from .xme_config import *
from .classes.user import *
from .classes.database import *
import config
from nonebot import on_command, CommandSession
from .tools.pre_checks import *

change_bio_alias = ["个人介绍", "bio"]
@on_command('changebio', aliases=change_bio_alias, only_to_me=True, permission=lambda x: x.from_group(config.GROUPS_WHITELIST))
@pre_check() # 执行前检查
async def _(session: CommandSession, user: User):
    """更改用户介绍"""
    arg = session.current_arg_text.strip()
    if not arg:
        await send_msg(session, "请输入用户介绍哦")
    message = ""
    if user.change_bio(arg):
        message = f"修改个人介绍成功啦~"
    else:
        message = f"修改个人介绍失败，呜呜，请确定个人介绍的长度在 {user.MAX_BIO_LENGTH} 以内，且换行符少于 15 个哦 uwu"
    await send_msg(session, message)