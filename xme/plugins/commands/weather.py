from nonebot import on_command, CommandSession
from nonebot import on_natural_language, NLPSession, IntentCommand
from ...xmetools import random_tools as rt
from ...xmetools import request_tools as req
from ...xmetools import date_tools as dt
from xme.xmetools.doc_gen import CommandDoc
from datetime import datetime
import config

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
    desc='查询天气',
    introduction='查看指定地区的天气',
    usage=f'<地区名> <未来天气预测天数(1~3)>',
    permissions=[],
    alias=alias
))


# 天气预报查看
@on_command(__plugin_name__, aliases=alias, only_to_me=False)
async def _(session: CommandSession):
    params = session.current_arg_text.strip()
    message = rt.rand_str("请在下面发送你要查询的地区名~", "在下面发送地区名吧", "你想查询哪里的天气呢") + "，或发送 \"取消\" 取消哦"
    if not params:
        params = (await session.aget(prompt=message)).strip()
        if params == "取消":
            await session.send("取消天气查询啦")
            return
        while not params:
            params = (await session.aget(prompt="请重新输入地区名ovo")).strip()

    city_input = params.split(" ")[0]
    city = city_input
    # print(city)
    days_num = 1
    if len(params.split(" ")) > 1:
        try:
            days_num = int(params.split(" ")[1]) + 1
            if days_num > 4 or days_num < 2:
                message = f"{rt.rand_str('设置的天数', '未来天数', '天数')}还不可以大于 3 或小于 1 哦"
                await session.send(message)
                return
        except:
            message = f"请确认被解析的参数是否是你想的那样哦：\n城市名：{city}\n未来天数：{params.split(' ')[1]}"
            await session.send(message)
            return
    try:
        weathers = req.get_weather(city)["forecasts"][0]
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
        message = f"[CQ:at,qq={session.event.user_id}] "
        message += f'{rt.rand_str("我来看看天气~ owo", "让我看看天气~", "让我查询一下这里的天气~", "我看看这里的天气~ owo", "看看地球的天气怎么样啦~")}\n======※今日天气: {city_name}※======\n{datetime.strptime(date, "%Y-%m-%d").strftime("%m月%d日")} {dt.week_str(week)}\n{day_night_weather}\n温度: {temp_min}~{temp_max}℃\n日间: {day_wind[0]}风 {day_wind[1]} 级\t夜间: {night_wind[0]}风 {night_wind[1]} 级\n查询时间: {report_time}'
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
            rainning_days = len([item for item in weather_days if "雨" in item[0] or "雨" in item[1]])
            future_days = days_num - 1
            message += f'未来 {future_days} 天{("" if future_days <= 1 else "")}{("有" if rainning_days == future_days and future_days <= 1 else "")}{("有 " + str(rainning_days) + " 天有" if future_days > 1 and rainning_days < future_days else "都有" if rainning_days == future_days else "没有")}雨, 最高温度 {max_temp}℃, 最低温度 {min_temp}℃'
        message += f"\n{rt.rand_str('数据来自于高德开放平台~', '数据是高德开放平台的哦~', '通过高德开放平台查询的~')}"
    except:
        message = f"查询出错了, 呜呜, 请确认地区名称是否输入正确哦\n被解析的地区名：{city}"
    await session.send(message)


@on_natural_language(keywords={'天气'})
async def _(session: NLPSession):
    return IntentCommand(90, 'weather')