
from xme.plugins.commands.xme_user.classes.user import limit
from xme.xmetools.bottools import get_user_name
from xme.xmetools.msgtools import is_text_can_send, send_session_msg, send_to_superusers
from xme.xmetools.doctools import CommandDoc
from nonebot import CommandSession
from xme.xmetools.plugintools import on_command
from character import get_message
from xme.xmetools.texttools import to_forwardable_message
from xme.xmetools.timetools import TimeUnit
# from nonebot.log import logger

alias = ["反馈", "汇报", "rep"]
__plugin_name__ = 'report'

__plugin_usage__ = CommandDoc(
    name=__plugin_name__,
    desc=get_message("plugins", __plugin_name__, 'desc'),
    introduction=get_message("plugins", __plugin_name__, 'introduction'),
    usage='(汇报消息)',
    permissions=["无"],
    alias=alias
)

@limit(__plugin_name__, 1, get_message("plugins", __plugin_name__, "limited"), 3, TimeUnit.MINUTE)
@on_command(__plugin_name__, aliases=alias, only_to_me=False, permission=lambda _: True)
async def _(session: CommandSession):
    arg = session.current_arg.strip()
    msg = to_forwardable_message(arg)
    if msg is None or not msg:
        return await send_session_msg(session, get_message("plugins", __plugin_name__, "no_msg"))
    moderation = await is_text_can_send(session, msg, strictness=4)
    if not moderation["result"]:
        return await send_session_msg(session, get_message("plugins", __plugin_name__, "blocked"))
    await send_to_superusers(session.bot, get_message("plugins", __plugin_name__, "report", msg=msg, uname=await get_user_name(session.event.user_id), qq=str(session.event.user_id)))
    return await send_session_msg(session, get_message("plugins", __plugin_name__, "success"))