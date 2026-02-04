from nonebot import CommandSession
from xme.xmetools.plugintools import on_command
from xme.xmetools.doctools import CommandDoc
from xme.xmetools.msgtools import send_session_msg, aget_session_msg
from character import get_message
# import config
from xme.xmetools.loctools import search_location
# import re
# from xme.xmetools.jsontools import read_from_path, save_to_path
from xme.plugins.commands.xme_user.classes.user import using_user, User

alias = ['绑定位置', '设置位置', '定位', 'loc']
__plugin_name__ = 'location'
__plugin_usage__ = CommandDoc(
    name=__plugin_name__,
    desc=get_message("plugins", __plugin_name__, 'desc'),
    introduction=get_message("plugins", __plugin_name__, 'introduction'),
    usage='(地点)',
    permissions=["无"],
    alias=alias
)

@on_command(__plugin_name__, aliases=alias, only_to_me=False, permission=lambda _: True)
@using_user(save_data=True)
async def _(session: CommandSession, user: User):
    loc = session.current_arg_text
    # data = read_from_path(config.BOT_SETTINGS_PATH)
    if not loc:
        # user_loc = data["locations"].get(str(session.event.user_id), None)
        user_loc = user.plugin_datas.get("location", None)
        if user_loc:
            await send_session_msg(session, get_message("plugins", __plugin_name__, 'curr_loc', loc=f'{user_loc["adm1"]} {user_loc["adm2"]} {user_loc["name"]}'), tips=True, tips_percent=10)
            return
        await send_session_msg(session, get_message("plugins", __plugin_name__, 'no_curr_loc'), tips=True)
        return
    elif loc in ["clear", "unbind"]:
        # del data["locations"][str(session.event.user_id)]
        # save_to_path(config.BOT_SETTINGS_PATH, data)
        if user.plugin_datas.get("location", None):
            return await send_session_msg(session, get_message("plugins", __plugin_name__, 'no_curr_loc'), tips=True)
        del user.plugin_datas["location"]
        await send_session_msg(session, get_message("plugins", __plugin_name__, 'unbind_loc'), tips=True)
        return True
    search = await search_location(loc, dict_output=False)
    if isinstance(search, str):
        await send_session_msg(session, search)
        return False
    locations = search.get("location", [])
    choose = {}
    if len(locations) > 1:
        has_target = False
        await send_session_msg(session, get_message("plugins", __plugin_name__, 'choose_location', locs="\n".join([f'{i + 1}. {l["country"]} {l["adm1"]} {l["adm2"]} {l["name"]}' for i, l in enumerate(locations)])))  # noqa: E741
        times = 0
        while not has_target and times < 3:
            target: str = await aget_session_msg(session, can_use_command=True)
            if target == "CMD_END":
                return False
            target = target.replace(".", "").strip()
            if target.isdigit():
                has_target = True
            times += 1
        if times >= 3:
            await send_session_msg(session, get_message("plugins", __plugin_name__, 'no_choose', num=target), tips=True)
            return False
        elif (int(target) - 1) < 0 or int(target) > len(locations):
            await send_session_msg(session, get_message("plugins", __plugin_name__, 'invalid_choose', num=target), tips=True)
            return False
        choose = locations[int(target) - 1]
    elif len(locations) == 1:
        choose = locations[0]
    else:
        await send_session_msg(session, get_message("plugins", __plugin_name__, 'no_result', loc=loc), tips=True)
        return False

    # data = read_from_path(config.BOT_SETTINGS_PATH)
    # data["locations"][str(session.event.user_id)] = choose
    user.plugin_datas["location"] = choose
    # save_to_path(config.BOT_SETTINGS_PATH, data)
    await send_session_msg(session, get_message("plugins", __plugin_name__, 'success', loc=f'{choose["adm1"]} {choose["adm2"]} {choose["name"]}'), tips=True, tips_percent=10)
    return True