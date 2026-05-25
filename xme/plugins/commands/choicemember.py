from nonebot import CommandSession
from xme.xmetools.plugintools import on_command
from xme.xmetools.doctools import CommandDoc
from xme.xmetools.msgtools import send_session_msg
from xme.xmetools.bottools import permission
from character import get_message
from xme.xmetools.typetools import try_parse
import random


alias = ['cm']
__plugin_name__ = 'chomem'
__plugin_usage__ = CommandDoc(
    name=__plugin_name__,
    desc=get_message("plugins", __plugin_name__, 'desc'),
    introduction=get_message("plugins", __plugin_name__, 'introduction'),
    usage='<群员数量>',
    permissions=["无"],
    alias=alias
)

@permission(lambda x: x.is_groupchat, permission_help="在群聊内")
@on_command(__plugin_name__, aliases=alias, only_to_me=False, permission=lambda _: True)
async def _(session: CommandSession):
    MAX_MEMBER = 150
    arg = session.current_arg_text.strip()
    arg_int = try_parse(arg, int, 1)
    if arg_int <= 0:
        return await send_session_msg(session, get_message("plugins", __plugin_name__, "too_small_number"))
    members = await session.bot.get_group_member_list(group_id=session.event.group_id)
    if len(members) < arg_int:
        return await send_session_msg(session, get_message("plugins", __plugin_name__, "error"))
    if arg_int > MAX_MEMBER:
        return await send_session_msg(session, get_message("plugins", __plugin_name__, "max_num", max_num=MAX_MEMBER))
    random.shuffle(members)
    choice_members = [m["nickname"] for m in members[:arg_int]]
    await send_session_msg(
        session,
        get_message(
            "plugins",
            __plugin_name__,
            "output",
            members='\n'.join([f'{i + 1}. {m}' for i, m in enumerate(choice_members)])
        )
    )