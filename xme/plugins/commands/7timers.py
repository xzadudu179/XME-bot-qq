from nonebot import CommandSession
from xme.xmetools.plugintools import on_command
from xme.xmetools.doctools import CommandDoc
from character import get_message
from xme.xmetools.msgtools import send_session_msg, aget_session_msg
from xme.xmetools import texttools
from xme.xmetools.typetools import try_parse
from xme.xmetools.loctools import get_user_location

alias = ['7t', '晴天钟']
__plugin_name__ = '7timers'
__plugin_usage__ = CommandDoc(
    name=__plugin_name__,
    desc=get_message("plugins", __plugin_name__, 'desc'),
    introduction=get_message("plugins", __plugin_name__, 'introduction'),
    usage=f'<纬度,经度>',
    permissions=["无"],
    alias=alias
)

@on_command(__plugin_name__, aliases=alias, only_to_me=False, permission=lambda _: True, shell_like=True)
async def _(session: CommandSession):
    try:
        args = session.current_arg_text.strip()
        location = args
        _, user_location_info = await get_user_location(session.event.user_id)
        # print(len(locations), user_location_info)
        if not args and not user_location_info:
            location = texttools.replace_chinese_punctuation(aget_session_msg(session, get_message("plugins", __plugin_name__, 'ask_location')))
            if "[CQ:location" in location:
                location_info = location.split("[CQ:location,")[1].split(",title")[0].replace(",", "&")
        elif user_location_info and not args:
            lat, lon = user_location_info["lat"], user_location_info["lon"]
            print(user_location_info)
            location_info = f'lat={lat}&lon={lon}'
        elif args or "[CQ:location" not in location:
            print(location)
            loc = [try_parse(l, float, None) for l in location.split(",")]
            if len(loc) < 2:
                loc.append(0)
            if loc[0] is None or (abs(loc[0]) > 180 and abs(loc[1]) > 180) or loc[1] is None:
                return await send_session_msg(session, get_message("plugins", __plugin_name__, 'invalid_location', lat=location.split(",")[0], lon=location.split(",")[1]))
            elif abs(loc[0]) > 90:
                loc[0], loc[1] = loc[1], loc[0]
            location_info = f'lat={loc[0]}&lon={loc[1]}'
        astro_image_url = f"https://www.7timer.info/bin/astro.php?{location_info}&ac=0&lang=zh-CN&unit=metric&tzshift=0"
        # meteo_image_url = f"https://www.7timer.info/bin/meteo.php?{location_info}&ac=0&lang=zh-CN&unit=metric&tzshift=0"
        print(location_info)
        await send_session_msg(session, get_message("plugins", __plugin_name__, 'outputing'))
        await send_session_msg(session, f"[CQ:image,file={astro_image_url}]" + get_message("plugins", __plugin_name__, 'output_suffix'), tips=True)
    except Exception as ex:
        await send_session_msg(session, get_message("plugins", __plugin_name__, 'error', ex=f"{type(ex)} {ex}"))

