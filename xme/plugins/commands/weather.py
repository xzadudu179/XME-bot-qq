from nonebot import on_command, CommandSession
from xme.xmetools.doc_tools import CommandDoc, shell_like_usage
from nonebot.argparse import ArgumentParser
from character import get_message
from xme.xmetools.message_tools import send_session_msg
from xme.xmetools.time_tools import TimeUnit, iso_format_time
from xme.xmetools.request_tools import fetch_data
from xme.plugins.commands.user.classes import xme_user as u
import traceback
from xme.xmetools.json_tools import read_from_path, save_to_path
from xme.xmetools.location_tools import search_location, get_user_location
from keys import WEATHER_API_KEY
import textwrap

# TODO 将天气变为插件 合并 7timers 之类的指令

alias = ['当前天气', '天气', '查看天气', 'wea']
__plugin_name__ = 'weather'
arg_usage = shell_like_usage("OPTIONS", [
    {
        "name": "help",
        "abbr": "h",
        "desc": get_message("plugins", __plugin_name__, 'arg_help_desc'),
    },
    {
        "name": "warn",
        "abbr": "w",
        "desc": get_message("plugins", __plugin_name__, 'arg_warns_desc'),
    }
])
__plugin_usage__ = str(CommandDoc(
    name=__plugin_name__,
    desc=get_message("plugins", __plugin_name__, 'desc'),
    # desc='查看系统状态',
    introduction=get_message("plugins", __plugin_name__, 'introduction'),
    # introduction='查看运行该 XME-Bot 实例的设备的系统状态',
    usage=f'<地点名> [OPTIONS]\n{arg_usage}',
    permissions=["无"],
    alias=alias
))
headers = {
    "X-QW-Api-Key": WEATHER_API_KEY
}

@on_command(__plugin_name__, aliases=alias, only_to_me=False, permission=lambda _: True, shell_like=True)
@u.using_user(save_data=False)
@u.limit(__plugin_name__, 5, get_message("plugins", __plugin_name__, 'limited'), unit=TimeUnit.MINUTE, count_limit=5)
async def _(session: CommandSession, user: u.User):
    # print(session.current_arg_text)
    parser = ArgumentParser(session=session, usage=arg_usage)
    parser.add_argument('-w', '--warn', action='store_true', default=False)
    parser.add_argument('text', nargs='*')
    print(session.argv)
    args = parser.parse_args(session.argv)
    print(args)
    location_text = ' '.join(args.text).strip()
    print(location_text)
    locations, user_location_info = await get_user_location(session.event.user_id, location_text)
    print(len(locations), user_location_info)
    if not user_location_info and not location_text:
        await send_session_msg(session, get_message("plugins", __plugin_name__, 'no_location'))
        return False
    if len(locations) < 1 and location_text:
        await send_session_msg(session, get_message("plugins", __plugin_name__, 'no_result', loc=location_text))
        return False
    user_search = bool(location_text)
    try:
        location_info = locations[0]
        location_id = location_info["id"]
        warnings = output_warning(await get_warnings(location_id))
        if args.warn:
            return await get_warnings_now(session, location_info, warnings)
        return await get_weather_now(session, location_info, user_location_info, user_search, warnings)
    except Exception as ex:
        traceback.print_exc()
        await send_session_msg(session, get_message("plugins", __plugin_name__, 'output_error', ex=f"{type(ex)}: {ex}"))
        return False

async def get_warnings_now(session, location_info, warnings):
    # 输出预警信息
    location_name = f"{location_info['adm1']} {location_info['adm2']} {location_info['name']}"
    warns_output = f"======※预警信息：{location_name}※======\n"
    output = "\n" + warns_output + (warnings[1] if warnings[1] else "当前无预警")
    await send_session_msg(session, get_message("plugins", __plugin_name__, 'output', output=output))
    return True


async def get_weather_now(session, location_info, user_location_info, user_search, warnings):
    location_name = f"{location_info['adm1']} {location_info['adm2']} {location_info['name']}"
    location_id = location_info["id"]
    warns_output = "======※预警信息※======\n"
    weather = ouptut_weather_now(await get_weather(location_id))
    warns_output += warnings[0]
    output = f"\n======※现在天气：{location_name}※======" + f"{weather}" + (f"\n{warns_output}" if warnings[0] else "")
    tips_message = get_message("plugins", __plugin_name__, 'tips') if user_search and not user_location_info else ""
    if user_location_info:
        tips_message =  get_message("plugins", __plugin_name__, 'bound_tips') if user_location_info["id"] == location_id and user_search else tips_message
    await send_session_msg(session, get_message("plugins", __plugin_name__, 'output', output=output) + "\n" + tips_message)
    if user_location_info:
        # 启用了用户位置信息不会增加计时器
        return False
    return True


def ouptut_weather_now(weather):
    data = weather["now"]
    #  数据更新时间
    obs_time = iso_format_time(data["obsTime"], '%Y年%m月%d日 %H:%M')
    temp = data["temp"]
    feels_temp = data["feelsLike"]
    weather_stats = data["text"]
    wind_dir = data["windDir"]
    wind_scale = data["windScale"]
    humidity = data["humidity"]
    # 过去 1h 降水量 (mm)
    precip = data["precip"]
    # 气压 (hPa)
    pressure = data["pressure"]
    return textwrap.dedent(f"""
        - 天气：{weather_stats}，{wind_dir} {wind_scale} 级
        - 温度：{temp}℃，体感 {feels_temp}℃
        - 相对湿度 {humidity}%
        - 过去 1 小时降水量 {precip} mm
        - 气压 {pressure} hPa
        - 数据更新时间：{obs_time}""")

def output_warning(warning):
    datas = warning["warning"]
    lines = []
    details = []
    for data in datas:
        colors = {
            "Blue": "蓝色",
            "White": "白色",
            "Green": "绿色",
            "Yellow": "黄色",
            "Orange": "橙色",
            "Red": "红色",
            "Black": "黑色",
            "None": ""
        }
        color_emojis = {
            "Blue": "🟦",
            "White": "⬜",
            "Green": "🟩",
            "Yellow": "🟨",
            "Orange": "🟧",
            "Red": "🟥",
            "Black": "⬛",
            "None": "-"
        }
        # print(data)
        severity = x if (x:=data.get("severityColor", "")) else None
        color_emoji = color_emojis.get(severity, "-")
        # print(colors)
        line = f'{color_emoji} {data["typeName"]}{colors.get(severity, "")}预警'
        lines.append(line)
        detail = f'{color_emoji} {data["title"]}\n{data["text"]}'
        details.append(detail)
    return "\n".join(lines), "\n------------------\n".join(details)

async def get_weather(location: str):
    city_info = await search_location(location)
    city_id = city_info["location"][0]["id"]
    weather = await fetch_data(f'https://devapi.qweather.com/v7/weather/now?location={city_id}', headers=headers)
    return weather

async def get_warnings(location: str):
    city_info = await search_location(location)
    city_id = city_info["location"][0]["id"]
    warnings = await fetch_data(f'https://devapi.qweather.com/v7/warning/now?location={city_id}', headers=headers)
    return warnings