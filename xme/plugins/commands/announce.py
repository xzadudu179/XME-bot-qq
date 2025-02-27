from nonebot import on_command, CommandSession
from xme.xmetools.doc_tools import CommandDoc
from xme.xmetools.json_tools import read_from_path, save_to_path
from character import get_message
from nonebot import NoneBot
from nonebot.plugin import PluginManager
from nonebot import message_preprocessor
from character import get_message
import aiocqhttp
from nonebot import message_preprocessor
import time
import config
from xme.xmetools.message_tools import send_session_msg, send_to_groups, send_to_superusers

alias = ['公告', 'anno']
__plugin_name__ = 'announce'
__plugin_usage__ = str(CommandDoc(
    name=__plugin_name__,
    desc=get_message("plugins", __plugin_name__, 'desc'),
    introduction=get_message("plugins", __plugin_name__, 'introduction'),
    usage=f'<(SUPERUSER)公告内容>',
    permissions=["无"],
    alias=alias
))

temp_anno_sent = False
anno_sent_time = 0

@on_command(__plugin_name__, aliases=alias, only_to_me=False, permission=lambda _: True)
async def _(session: CommandSession):
    global temp_anno_sent
    global anno_sent_time
    anno = session.current_arg_text.strip()
    if not anno:
        return await send_session_msg(session, "[九九的公告] " + get_message("config", "anno_message", anno=x if (x:=read_from_path(config.BOT_SETTINGS_PATH).get("announcement", "无")) else "无公告"))

    if session.event.user_id not in config.SUPERUSERS:
        return await send_session_msg(session, get_message("config", 'no_permission'))
    if anno == "clear":
        anno = ""
    if anno.split(" ")[-1] == "temp":
        anno = " ".join(anno.split(" ")[:-1])
        temp_anno_sent = True
        anno_sent_time = time.time()
        await send_session_msg(session, get_message("plugins", __plugin_name__, 'sending_all_group'))
        return await send_to_groups(session.bot, "[九九的群发公告] " + anno + "\n" + get_message("config", "anno_temp_suffix"))
    c = read_from_path(config.BOT_SETTINGS_PATH)
    c["announcement"] = anno
    save_to_path(config.BOT_SETTINGS_PATH, c)
    return await send_session_msg(session, get_message("plugins", __plugin_name__, 'success' if anno else 'clear', anno=anno))

@message_preprocessor
async def private_message_copy(bot: NoneBot, event: aiocqhttp.Event, plugin_manager: PluginManager):
    global temp_anno_sent
    global anno_sent_time
    raw_msg = event.raw_message
    if time.time() - anno_sent_time > 300 and anno_sent_time > 0:
        print("刷新")
        anno_sent_time = 0
    if "[CQ:at,qq=" in raw_msg and raw_msg.split("[CQ:at,qq=")[1].split(",")[0] == str(event.self_id):
        if not temp_anno_sent:
            return
        print("这是回应公告的消息")
        return await send_to_superusers(bot, event.raw_message)