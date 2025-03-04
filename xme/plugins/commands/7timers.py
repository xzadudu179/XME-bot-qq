from nonebot import on_command, CommandSession
from xme.xmetools.doctools import CommandDoc
from character import get_message
from xme.xmetools.msgtools import send_session_msg
from xme.xmetools import texttools
from xme.xmetools.typetools import try_parse

alias = ['7t', '晴天钟']
__plugin_name__ = '7timers'
__plugin_usage__ = str(CommandDoc(
    name=__plugin_name__,
    desc=get_message("plugins", __plugin_name__, 'desc'),
    introduction=get_message("plugins", __plugin_name__, 'introduction'),
    usage=f'<纬度,经度>',
    permissions=["无"],
    alias=alias
))

@on_command(__plugin_name__, aliases=alias, only_to_me=False, permission=lambda _: True, shell_like=True)
async def _(session: CommandSession):
    try:
        args = session.current_arg_text.strip()
        location = args
        if not args:
            location = texttools.replace_chinese_punctuation(await session.aget(prompt=get_message("plugins", __plugin_name__, 'ask_location')))
            if "[CQ:location" in location:
                location_info = location.split("[CQ:location,")[1].split(",title")[0].replace(",", "&")
        if args or "[CQ:location" not in location:
            loc = [try_parse(l, float, None) for l in location.split(",")]
            if len(loc) < 2:
                loc.append(0)
            if loc[0] is None or abs(loc[0]) > 90 or loc[1] is None or abs(loc[1]) > 180:
                return await send_session_msg(session, get_message("plugins", __plugin_name__, 'invalid_location', lat=loc[0], lon=loc[1]))
            location_info = f'lat={loc[0]}&lon={loc[1]}'
        astro_image_url = f"https://www.7timer.info/bin/astro.php?{location_info}&ac=0&lang=zh-CN&unit=metric&tzshift=0"
        # meteo_image_url = f"https://www.7timer.info/bin/meteo.php?{location_info}&ac=0&lang=zh-CN&unit=metric&tzshift=0"
        print(location_info)
        await send_session_msg(session, get_message("plugins", __plugin_name__, 'outputing'))
        await send_session_msg(session, f"[CQ:image,file={astro_image_url}]" + get_message("plugins", __plugin_name__, 'output_suffix'))
    except Exception as ex:
        await send_session_msg(session, get_message("plugins", __plugin_name__, 'error', ex=f"{type(ex)} {ex}"))

