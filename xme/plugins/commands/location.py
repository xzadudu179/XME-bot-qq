from nonebot import on_command, CommandSession
from xme.xmetools.doctools import CommandDoc
from xme.xmetools.msgtools import send_session_msg
from character import get_message
import config
from xme.xmetools.loctools import search_location
from xme.xmetools.jsontools import read_from_path, save_to_path

alias = ['绑定位置', '设置位置', '定位', 'loc']
__plugin_name__ = 'location'
__plugin_usage__ = str(CommandDoc(
    name=__plugin_name__,
    desc=get_message("plugins", __plugin_name__, 'desc'),
    introduction=get_message("plugins", __plugin_name__, 'introduction'),
    usage=f'(地点)',
    permissions=["无"],
    alias=alias
))

@on_command(__plugin_name__, aliases=alias, only_to_me=False, permission=lambda _: True)
async def _(session: CommandSession):
    loc = session.current_arg_text
    data = read_from_path(config.BOT_SETTINGS_PATH)
    if not loc:
        user_loc = data["locations"].get(str(session.event.user_id), None)
        if user_loc:
            await send_session_msg(session, get_message("plugins", __plugin_name__, 'curr_loc', loc=f'{user_loc["adm1"]} {user_loc["adm2"]} {user_loc["name"]}'), tips=True, tips_percent=10)
            return
        await send_session_msg(session, get_message("plugins", __plugin_name__, 'no_curr_loc'), tips=True)
        return
    elif loc in ["clear", "unbind"]:
        del data["locations"][str(session.event.user_id)]
        save_to_path(config.BOT_SETTINGS_PATH, data)
        await send_session_msg(session, get_message("plugins", __plugin_name__, 'unbind_loc'), tips=True)
        return
    search = await search_location(loc, dict_output=False)
    if isinstance(search, str):
        await send_session_msg(session, search)
        return False
    locations = search.get("location", [])
    choose = {}
    if len(locations) > 1:
        target: str = await session.aget(prompt=get_message("plugins", __plugin_name__, 'choose_location', locs="\n".join([f'{i + 1}. {l["country"]} {l["adm1"]} {l["adm2"]} {l["name"]}' for i, l in enumerate(locations)])))
        if not target.isdigit() or (int(target) - 1) < 0 or int(target) > len(locations):
            await send_session_msg(session, get_message("plugins", __plugin_name__, 'invalid_choose', num=target), tips=True)
            return False
        choose = locations[int(target) - 1]
    elif len(locations) == 1:
        choose = locations[0]
    else:
        await send_session_msg(session, get_message("plugins", __plugin_name__, 'no_result', loc=loc), tips=True)
        return False

    data = read_from_path(config.BOT_SETTINGS_PATH)
    data["locations"][str(session.event.user_id)] = choose
    save_to_path(config.BOT_SETTINGS_PATH, data)
    await send_session_msg(session, get_message("plugins", __plugin_name__, 'success', loc=f'{choose["adm1"]} {choose["adm2"]} {choose["name"]}'), tips=True, tips_percent=10)
    return True