from nonebot import on_command, CommandSession
from xme.xmetools.msgtools import send_session_msg
# from ...xmetools import randtools as rt
from ...xmetools import reqtools as req
from ...xmetools import timetools as dt
from xme.xmetools.doctools import CommandDoc
from datetime import datetime
from character import get_message

alias = ['天气', 'wea', '查看天气']
__plugin_name__ = 'weather'
# __plugin_usage__ = rf"""
# 指令 {__plugin_name__}
# 简介：查询天气
# 作用：查看指定地区的天气
# 用法：
# - {config.COMMAND_START[0]}{__plugin_name__} <地区名> <未来天气预测天数(1~3)>
# 权限/可用范围：无
# 别名：{', '.join(alias)}
# """.strip()

__plugin_usage__ = str(CommandDoc(
    name=__plugin_name__,
    desc=get_message("plugins", __plugin_name__, 'desc'),
    # desc='查询天气',
    introduction=get_message("plugins", __plugin_name__, 'introduction'),
    # introduction='查看指定地区的天气',
    usage='<地区名> <未来天气预测天数(1~3)>',
    permissions=["无"],
    alias=alias
))


# 天气预报查看
@on_command(__plugin_name__, aliases=alias, only_to_me=False, permission=lambda _: True)
async def _(session: CommandSession):
    params = session.current_arg_text.strip()
    cancel_message = get_message("plugins", __plugin_name__, 'cancel_message')
    message = get_message("plugins", __plugin_name__, 'enter_city_prompt') + get_message("plugins", __plugin_name__, 'enter_city_prompt_cancel', cancel_message=cancel_message)
    # message = rt.rand_str("请在下面发送你要查询的地区名~", "在下面发送地区名吧", "你想查询哪里的天气呢") + f"，或发送 \"{cancel_message}\" 取消哦"
    if not params:
        params = (await session.aget(prompt=message)).strip()
        if params == cancel_message:
            await send_session_msg(session, get_message("plugins", __plugin_name__, 'search_cancelled'))
            # await send_msg(session, "取消天气查询啦")
            return
        while not params:
            params = (await session.aget(prompt=get_message("plugins", __plugin_name__, 're_enter_city_prompt'))).strip()
            # params = (await session.aget(prompt="请重新输入地区名ovo")).strip()

    city_input = params.split(" ")[0]
    city = city_input
    # print(city)
    days_num = 1
    if len(params.split(" ")) > 1:
        try:
            days_num = int(params.split(" ")[1]) + 1
            if days_num > 4 or days_num < 2:
                message = get_message("plugins", __plugin_name__, 'invalid_days', future_days=get_message("plugins", __plugin_name__, 'future_days'))
                # message = f"{rt.rand_str('设置的天数', '未来天数', '天数')}还不可以大于 3 或小于 1 哦"
                await send_session_msg(session, message)
                return
        except Exception:
            message = get_message("plugins", __plugin_name__, 'error_param', city=city, future_days=params.split(' ')[1])
            # message = f"出错啦...请确认被解析的参数是否是你想的那样哦：\n城市名：{city}\n未来天数：{params.split(' ')[1]}"
            await send_session_msg(session, message)
            return
    try:
        weathers = await req.get_weather(city)
        weathers = weathers["forecasts"][0]
        city_name = weathers["city"]
        report_time = weathers["reporttime"]
        weather_today = weathers["casts"][0]
        date = weather_today["date"]
        week = int(weather_today["week"])
        day = weather_today["dayweather"]
        night = weather_today["nightweather"]
        day_night_weather = day + "转" + night if day != night else day
        day_temp = weather_today["daytemp"]
        night_temp = weather_today["nighttemp"]
        temp_max = max(int(day_temp), int(night_temp))
        temp_min = min(int(day_temp), int(night_temp))
        day_wind = [weather_today["daywind"], weather_today["daypower"]]
        night_wind = [weather_today["nightwind"], weather_today["nightpower"]]
        message = ""
        message += get_message("plugins", __plugin_name__, 'result_prefix') + get_message("plugins", __plugin_name__, 'result_content',
            city_name=city_name,
            date=datetime.strptime(date, "%Y-%m-%d").strftime("%m月%d日"),
            weekday=dt.week_str(week),
            weather=day_night_weather,
            temp_min=temp_min,
            temp_max=temp_max,
            day_wind_min=day_wind[0],
            day_wind_max=day_wind[1],
            night_wind_min=night_wind[0],
            night_wind_max=night_wind[1],
            report_time=report_time
        )
        # message += f'{rt.rand_str("我来看看天气~ owo", "让我看看天气~", "让我查询一下这里的天气~", "我看看这里的天气~ owo", "让我看看天气怎么样啦~")}\n======※今日天气: {city_name}※======\n{datetime.strptime(date, "%Y-%m-%d").strftime("%m月%d日")} {dt.week_str(week)}\n天气：{day_night_weather}\n温度: {temp_min}~{temp_max}℃\n日间: {day_wind[0]}风 {day_wind[1]} 级\t夜间: {night_wind[0]}风 {night_wind[1]} 级\n查询时间: {report_time}'
        if len(params.split(" ")) > 1:
            message += "\n========================\n"
            max_temp = 0
            min_temp = 999
            weather_days = []
            for i in range(days_num - 1):
                weather_day = weathers["casts"][i + 1]
                max_temp = max(max(int(weather_day["daytemp"]), int(weather_day["nighttemp"])), max_temp)
                min_temp = min(min(int(weather_day["daytemp"]), int(weather_day["nighttemp"])), min_temp)
                day = weather_day["dayweather"]
                night = weather_day["nightweather"]
                weather_days.append([day, night])
            # print(["雨" in item[0] or "雨" in item[1] for item in weather_days])
            raining_days = len([item for item in weather_days if "雨" in item[0] or "雨" in item[1]])
            future_days = days_num - 1
            message += get_message("plugins", __plugin_name__, 'result_future',
                future_days=future_days,
                raining_days=f'{("都有" if raining_days == future_days and future_days <= 1 else "")}{("有 " + str(raining_days) + " 天有" if future_days > 1 and raining_days < future_days else "都有" if raining_days == future_days else "都没有")}',
                max_temp=max_temp,
                min_temp=min_temp
            )
            # message += f'未来 {future_days} 天{("" if future_days <= 1 else "")}{("有" if rainning_days == future_days and future_days <= 1 else "")}{("有 " + str(rainning_days) + " 天有" if future_days > 1 and rainning_days < future_days else "都有" if rainning_days == future_days else "没有")}雨, 最高温度 {max_temp}℃, 最低温度 {min_temp}℃'
        message += f"\n{get_message('plugins', __plugin_name__, 'data_from')}"
        # message += f"\n{rt.rand_str('数据来自于高德开放平台~', '数据是高德开放平台的哦~', '通过高德开放平台查询的~')}"
    except Exception as ex:
        message = get_message("plugins", __plugin_name__, 'error', city=city, ex=ex)
        # message = f"查询出错了, 呜呜, 请确认地区名称是否输入正确哦\n被解析的地区名：{city}\n{ex}"
    await send_session_msg(session, message)
