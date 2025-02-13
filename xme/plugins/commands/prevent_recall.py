# -- coding: utf-8 --**
import json
from xme.xmetools.command_tools import send_session_msg
from xme.xmetools.doc_tools import CommandDoc
from nonebot import on_command, CommandSession
from character import get_message

alias = ['防撤回', "precall", "防撤", '防撤回功能']
__plugin_name__ = 'prevrecall'
__plugin_usage__ = str(CommandDoc(
    name=__plugin_name__,
    desc=get_message("plugins", __plugin_name__, "desc"),
    # desc='防撤回',
    introduction=get_message("plugins", __plugin_name__, "introduction"),
    # introduction='防撤回功能相关',
    usage=f'<开|关|T|F>',
    permissions=["在群聊内", "是 SUPERUSER"],
    alias=alias
))

@on_command(__plugin_name__, aliases=alias, only_to_me=False, permission=lambda sender: (sender.is_groupchat and sender.is_superuser))
async def _(session: CommandSession):
    group_id = str(session.event.group_id)
    settings = {}
    try:
        with open("./data/_botsettings.json", 'r', encoding='utf-8') as jsonfile:
            settings = json.load(jsonfile)
    except:
        settings = {
            "prevent_recall": {}
        }
    prev = settings['prevent_recall'].get(group_id, False)
    message = get_message("plugins", __plugin_name__, "stats", group_id=group_id, stats=get_message("plugins", __plugin_name__, "opened_message") if prev else get_message("plugins", __plugin_name__, "closed_message"))
    # message = f"本群 ({group_id}) 的防撤回功能：{'已开启' if prev else '已关闭'}"
    arg = session.current_arg_text.strip()
    if arg.capitalize() == "开" or arg.capitalize() == "T":
        settings['prevent_recall'][group_id] = True
        await send_session_msg(session, get_message("plugins", __plugin_name__, "open"))
        # await send_msg(session, "防撤回功能已开owo")
    elif arg.capitalize() == "关" or arg.capitalize() == "F":
        settings['prevent_recall'][group_id] = False
        await send_session_msg(session, get_message("plugins", __plugin_name__, "close"))
        # await send_msg(session, "防撤回功能已关ovo")
    else:
        await send_session_msg(session, message)
    with open ("./data/_botsettings.json", 'w', encoding='utf-8') as jsonfile:
        jsonfile.write(json.dumps(settings, indent=4))