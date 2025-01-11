from nonebot import on_command, CommandSession
from xme.xmetools.doc_tools import CommandDoc
from xme.xmetools.json_tools import read_from_path, save_to_path
from character import get_message
import config
from xme.xmetools.command_tools import send_session_msg

alias = ['公告', 'anno']
__plugin_name__ = 'announce'
__plugin_usage__ = str(CommandDoc(
    name=__plugin_name__,
    desc=get_message(__plugin_name__, 'desc'),
    introduction=get_message(__plugin_name__, 'introduction'),
    usage=f'<(SUPERUSER)公告内容>',
    permissions=[],
    alias=alias
))

@on_command(__plugin_name__, aliases=alias, only_to_me=False)
async def _(session: CommandSession):
    anno = session.current_arg_text.strip()
    if not anno:
        return await send_session_msg(session, get_message("config", "anno_message", anno=read_from_path(config.BOT_SETTINGS_PATH).get("announcement", "无")))
    if session.event.user_id not in config.SUPERUSERS:
        return await send_session_msg(session, get_message("config", 'no_permission'))
    c = read_from_path(config.BOT_SETTINGS_PATH)
    c["announcement"] = anno
    save_to_path(config.BOT_SETTINGS_PATH, c)
    return await send_session_msg(session, get_message(__plugin_name__, 'success', anno=anno))