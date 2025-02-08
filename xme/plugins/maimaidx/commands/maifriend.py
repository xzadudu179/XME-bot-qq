from nonebot import on_command, CommandSession
from xme.xmetools.doc_tools import CommandDoc
from character import get_message
from xme.xmetools.image_tools import image_msg
from xme.xmetools.command_tools import send_session_msg
from ..libraries.maifriend import gen_maifriend
import traceback

alias = ['旅行伙伴', 'maif']
__plugin_name__ = 'maifriend'
__plugin_usage__ = str(CommandDoc(
    name=__plugin_name__,
    desc=get_message(__plugin_name__, 'desc'),
    introduction=get_message(__plugin_name__, 'introduction'),
    usage=f'<at 用户>',
    permissions=["无"],
    alias=alias
))

@on_command(__plugin_name__, aliases=alias, only_to_me=False, permission=lambda _: True)
async def _(session: CommandSession):
    arg = session.current_arg.strip()
    qq_id = session.event.user_id
    try:
        if arg.startswith("[CQ:at,qq="):
            qq_id = int(arg.split("[CQ:at,qq=")[-1].split(",")[0])
        image = gen_maifriend(qq_id)
    except:
        traceback.print_exc()
        return await send_session_msg(session, get_message(__plugin_name__, 'error'))
    return await send_session_msg(session, await image_msg(image))