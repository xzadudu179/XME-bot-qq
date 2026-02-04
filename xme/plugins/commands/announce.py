from nonebot import CommandSession
from xme.xmetools.plugintools import on_command
from xme.xmetools.doctools import CommandDoc
from xme.xmetools.jsontools import read_from_path, save_to_path
from character import get_message
import config
from xme.xmetools.msgtools import send_session_msg, send_to_groups

alias = ['公告', 'anno']
__plugin_name__ = 'announce'
__plugin_usage__ = CommandDoc(
    name=__plugin_name__,
    desc=get_message("plugins", __plugin_name__, 'desc'),
    introduction=get_message("plugins", __plugin_name__, 'introduction'),
    usage='<(SUPERUSER)公告内容>',
    permissions=["无"],
    alias=alias
)


@on_command(__plugin_name__, aliases=alias, only_to_me=False, permission=lambda _: True)
async def _(session: CommandSession):
    anno = session.current_arg_text.strip()
    if not anno:
        return await send_session_msg(session, "[九九的公告] " + get_message("config", "anno_message", anno=x if (x:=read_from_path(config.BOT_SETTINGS_PATH).get("announcement", "无")) else "无公告"))

    if session.event.user_id not in config.SUPERUSERS:
        return await send_session_msg(session, get_message("config", 'no_permission'))
    if anno == "clear":
        anno = ""
    if anno.split(" ")[-1] == "temp":
        anno = " ".join(anno.split(" ")[:-1])
        # anno_sent_time = time.time()
        await send_session_msg(session, get_message("plugins", __plugin_name__, 'sending_all_group'))
        return await send_to_groups(session.bot, "[九九的群发公告] " + anno + "\n" + get_message("config", "anno_temp_suffix"))
    c = read_from_path(config.BOT_SETTINGS_PATH)
    c["announcement"] = anno
    save_to_path(config.BOT_SETTINGS_PATH, c)
    return await send_session_msg(session, get_message("plugins", __plugin_name__, 'success' if anno else 'clear', anno=anno))

