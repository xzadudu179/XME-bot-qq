# -- coding: utf-8 --**
from xme.xmetools.jsontools import change_json, get_json_value
from xme.xmetools.msgtools import send_session_msg
from xme.xmetools.doctools import CommandDoc
from nonebot import on_command, CommandSession
from character import get_message
import config

alias = ['报时', 'stime']
__plugin_name__ = 'schtime'
__plugin_usage__ = str(CommandDoc(
    name=__plugin_name__,
    desc=get_message("plugins", __plugin_name__, "desc"),
    introduction=get_message("plugins", __plugin_name__, "introduction"),
    usage=f'',
    permissions=["在群聊内", "是管理员或群主"],
    alias=alias
))

@on_command(__plugin_name__, aliases=alias, only_to_me=False, permission=lambda sender: (sender.is_groupchat and sender.is_admin or sender.is_owner))
async def _(session: CommandSession):
    group_id = str(session.event.group_id)
    if group_id in get_json_value(config.BOT_SETTINGS_PATH, "schtime_groups"):
        change_json(config.BOT_SETTINGS_PATH, "schtime_groups", set_method=lambda v: [x for x in v if x != group_id])
        return await send_session_msg(session, get_message("plugins", __plugin_name__, "disabled"))
    else:
        change_json(config.BOT_SETTINGS_PATH, "schtime_groups", set_method=lambda v: v + [group_id])
        return await send_session_msg(session, get_message("plugins", __plugin_name__, "activated"))