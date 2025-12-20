from nonebot import on_command, CommandSession
from xme.xmetools.doctools import CommandDoc
from xme.xmetools.jsontools import read_from_path
from xme.plugins.commands.xme_user.classes.user import User, using_user
from xme.xmetools.timetools import curr_days
from cn2an import an2cn
import random
random.seed()
from xme.xmetools.msgtools import send_session_msg, aget_session_msg
from character import get_message

alias = ['抽签', '求签', '签']
__plugin_name__ = 'lotluck'
__plugin_usage__ = CommandDoc(
    name=__plugin_name__,
    desc=get_message("plugins", __plugin_name__, "desc"),
    introduction=get_message("plugins", __plugin_name__, "introduction"),
    usage=f'',
    permissions=["无"],
    alias=alias
)

@on_command(__plugin_name__, aliases=alias, only_to_me=False, permission=lambda _: True)
@using_user(True)
async def _(session: CommandSession, u: User):
    reply: str = await aget_session_msg(session, prompt=get_message("plugins", __plugin_name__, "hint"))
    if reply.lower().strip() != "y":
        return await send_session_msg(session, get_message("plugins", __plugin_name__, "canceled"), tips=True)
    result = await u.try_spend(session, 5)
    if not result:
        return
    lots: list = read_from_path("./static/lot.json")
    lot = random.choice(lots)
    num_str = an2cn(lot["num"])
    result = f"第{num_str}签 {lot['type']}\n{lot['content']}"
    return await send_session_msg(session, result)
    # if coins < 15:
