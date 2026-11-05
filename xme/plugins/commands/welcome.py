from nonebot import CommandSession
from xme.xmetools.plugintools import on_command
from xme.xmetools.doctools import CommandDoc
from xme.xmetools.bottools import permission, toggle_welcome
from xme.xmetools.msgtools import send_session_msg
from character import get_message

alias = ['入群欢迎', '群欢迎']
permissions = ["在群聊内", "是管理员或群主"]
__plugin_name__ = 'welcome'
__plugin_usage__ = CommandDoc(
    name=__plugin_name__,
    desc=get_message("plugins", __plugin_name__, "desc"),
    introduction=get_message("plugins", __plugin_name__, "introduction"),
    usage='',
    permissions=permissions,
    alias=alias
)

@on_command(__plugin_name__, aliases=alias, only_to_me=False, permission=lambda _: True)
@permission(lambda sender: (sender.is_groupchat and sender.is_admin or sender.is_owner), permission_help=" & ".join(permissions))
async def _(session: CommandSession):
    enabled = toggle_welcome(session.event.group_id)
    return await send_session_msg(session, get_message("plugins", __plugin_name__, "activated" if enabled else "disabled"))
