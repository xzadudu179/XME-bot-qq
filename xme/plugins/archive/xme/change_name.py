
from .xme_config import *
from .classes.user import *
from .classes.database import *
import config
from nonebot import on_command, CommandSession
from .tools.pre_checks import *

change_name_alias = ["改名", "name"]
@on_command('changename', aliases=change_name_alias, only_to_me=True, permission=lambda x: x.from_group(config.GROUPS_WHITELIST))
@pre_check() # 执行前检查
async def _(session: CommandSession, user: User):
    """更改用户名"""
    arg = session.current_arg_text.strip()
    if not arg:
        await send_msg(session, "请输入用户名哦")
    message = ""
    if user.change_name(arg):
        suffix = '\n非法的字符被替换了哦 ovo' if arg != user.name else ''
        message = f"改名成功啦~ 你的用户名现在叫 \"{user.name}\" 哦~{suffix}"
    else:
        message = f"改名失败，呜呜，请确定用户名的长度在 {user.MAX_NAME_LENGTH} 以内哦 uwu"
    await send_msg(session, message)